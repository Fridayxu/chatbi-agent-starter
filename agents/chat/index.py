"""
ChatBI Agent — POST /chat
Gateway Direct + Function Calling: leverages EdgeOne Makers sandbox
(code_interpreter, files, commands) via OpenAI-compatible tool calling.

Capabilities surfaced to the frontend:
  - Tool calls: real-time SSE events for code execution, file ops
  - Model info: model name emitted at conversation start
  - Memory: conversation persisted via ctx.store
  - Observability: every tool call + API round-trip logged
"""
from __future__ import annotations

import json, time, httpx, base64, subprocess, os, asyncio
from typing import Any
from pathlib import Path

from .._model import resolve_model_name
from .._logger import create_logger

logger = create_logger("chatbi")

# ═══════════════════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are ChatBI Agent, a supply chain data analyst on EdgeOne Makers.

## Tools
| Tool | How to use |
|------|-----------|
| `list_files` | See what files the user uploaded. Always call first. |
| `read_file` | Returns: columns, types, stats (min/max/mean/sum) per numeric column, unique values for categorical, first rows, correlations. **For large files, it returns a statistical sample — stats are still accurate.** |
| `code_interpreter` | Run Python. File is at `/tmp/<filename>`. **Use csv.DictReader — the file is already there. Built-in modules only: csv, json, statistics, math, collections, datetime. 120s timeout.** |

## Rules for Data Analysis
1. First `list_files`, then `read_file` — the stats it returns are usually enough for a summary.
2. For deeper analysis, use `code_interpreter` with csv.DictReader on `/tmp/<filename>`.
3. **NEVER use `!pip install`** — it ALWAYS times out. Built-in csv module works great.
4. For large files: read_file gives sampled stats. Use code_interpreter for full pass (csv is fast, 73K rows takes <2 seconds).
5. Use Chinese. Show numbers first, explain briefly.

## Conciseness
- Greetings: ≤5 words. No capability lists."""

# ═══════════════════════════════════════════════════════════════
# Tool Definitions (OpenAI function-calling format)
# ═══════════════════════════════════════════════════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "code_interpreter",
            "description": "Execute Python code in a sandbox. Use for data analysis, statistics, forecasting, visualization. Stdout and stderr are returned. Install packages with !pip install ... in the code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. For charts, save to /tmp/chart.png."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read an uploaded file (CSV, Excel, JSON, TXT). Returns a pandas DataFrame preview: first 20 rows, shape, and column dtypes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the uploaded file to read."
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files the user has uploaded and are available for analysis. Call this first when a user uploads data.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# ═══════════════════════════════════════════════════════════════
# Tool Executors
# ═══════════════════════════════════════════════════════════════

# In-memory registry of uploaded files: {filename: {content_bytes, mimeType}}
_uploaded_files: dict[str, dict] = {}


def _store_uploaded_files(files: list[dict]) -> None:
    """Decode base64 files and store in memory for tool access."""
    for f in files:
        try:
            raw = base64.b64decode(f.get("content", ""))
            _uploaded_files[f["name"]] = {
                "bytes": raw,
                "mimeType": f.get("mimeType", "text/csv"),
            }
            logger.log(f"stored file: {f['name']} ({len(raw)} bytes)")
        except Exception as e:
            logger.error(f"failed to decode {f.get('name', '?')}: {e}")


def _exec_python(code: str) -> str:
    """Execute Python code in a subprocess with a timeout."""
    lines = code.split("\n")
    pre_install = []
    actual_code = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("!pip install"):
            pkg_str = stripped[len("!pip install"):].strip()
            pre_install.append(pkg_str)
        elif stripped.startswith("!pip3 install"):
            pkg_str = stripped[len("!pip3 install"):].strip()
            pre_install.append(pkg_str)
        else:
            actual_code.append(line)

    script_parts = ["import sys, os, warnings, subprocess as _sp"]
    script_parts.append("warnings.filterwarnings('ignore')")
    script_parts.append("os.environ['MPLBACKEND'] = 'Agg'")

    # Pre-install each set of packages
    for pkg_str in pre_install:
        # Split by space, filter out flags (start with -) to keep them as flags
        parts = pkg_str.split()
        pkgs = [p for p in parts if not p.startswith('-')]
        flags = [p for p in parts if p.startswith('-')]
        for pkg in pkgs:
            script_parts.append(f"_sp.run([sys.executable, '-m', 'pip', 'install', '-q'] + {flags} + ['{pkg}'], check=False)")

    # Actual code
    script_parts.append("\n".join(actual_code))

    full_script = "\n".join(script_parts)

    try:
        result = subprocess.run(
            ["python", "-c", full_script],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/tmp",
            env={**os.environ, "PYTHONUNBUFFERED": "1", "MPLBACKEND": "Agg"},
        )
        out = result.stdout
        if result.stderr:
            out += "\n## stderr\n" + result.stderr
        if result.returncode != 0:
            out += f"\n## exit code: {result.returncode}"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "⏱️ Timeout: code ran longer than 60 seconds. Try optimizing or splitting into smaller steps."
    except FileNotFoundError:
        return "❌ Python not available in this environment."
    except Exception as e:
        return f"❌ Execution error: {e}"


def _read_file_preview(filename: str) -> str:
    """Read a file — efficient sampling for large files, full stats for small ones."""
    if filename not in _uploaded_files:
        available = ", ".join(_uploaded_files.keys()) or "(none)"
        return f"File '{filename}' not found. Available files: {available}"

    f = _uploaded_files[filename]
    raw = f["bytes"]
    size_mb = len(raw) / (1024 * 1024)
    tmp_path = Path("/tmp") / filename
    tmp_path.write_bytes(raw)

    # For large files, use sampling to avoid timeout
    max_rows = 5000 if size_mb > 0.5 else 50000

    try:
        code = f'''
import csv, statistics as st, sys, random, os
path = "{tmp_path.as_posix()}"
file_size = {size_mb}
max_rows = {max_rows}

with open(path, 'r', newline='', encoding='utf-8-sig') as cf:
    reader = csv.DictReader(cf)
    all_data = [row for row in reader]

total_rows = len(all_data)
print(f"File: {filename} ({file_size:.1f}MB)")
print(f"Shape: {{total_rows}} rows x {{len(all_data[0].keys())}} columns")
print(f"Columns: {{list(all_data[0].keys())}}")

# For large files, sample
if total_rows > max_rows:
    sample = random.sample(all_data, max_rows)
    print(f"(Sampled {{max_rows}}/{{total_rows}} rows for stats)")
else:
    sample = all_data

cols = list(sample[0].keys())

# Detect numeric columns & compute stats
num_cols = []
for c in cols:
    try:
        [float(r[c]) for r in sample]
        num_cols.append(c)
    except: pass

if num_cols:
    print(f"Numeric columns: {{num_cols}}")
    for c in num_cols:
        vals = [float(r[c]) for r in sample]
        print(f"  {{c}}: min={{min(vals):.2f}} max={{max(vals):.2f}} mean={{st.mean(vals):.2f}} sum~{{sum(vals)*total_rows/len(sample):.0f}}")

# Categorical: unique values (top 20)
for c in cols:
    if c not in num_cols:
        uniq = list(dict.fromkeys(r[c] for r in sample))
        print(f"  {{c}}: {{len(set(uniq))}} unique values, examples: {{uniq[:10]}}")

# First 10 rows
print(f"First 10 rows:")
for i, r in enumerate(sample[:10]):
    print(f"  [{{i}}] {{r}}")

# Correlations for numeric columns
if len(num_cols) >= 2:
    print("Top correlations:")
    cors = []
    for c1 in num_cols:
        for c2 in num_cols:
            if c1 < c2:
                v1 = [float(r[c1]) for r in sample]
                v2 = [float(r[c2]) for r in sample]
                m1, m2 = st.mean(v1), st.mean(v2)
                n = sum((a-m1)*(b-m2) for a,b in zip(v1,v2))
                d = (sum((a-m1)**2 for a in v1)*sum((b-m2)**2 for b in v2))**0.5
                r_val = n/d if d else 0
                if abs(r_val) > 0.3:
                    cors.append((abs(r_val), c1, c2, r_val))
    cors.sort(reverse=True)
    for _, c1, c2, r_val in cors[:5]:
        print(f"  {{c1}} vs {{c2}}: r={{r_val:.3f}}")

print("NOTE: pandas NOT available. Use built-in csv module for analysis.")
'''
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True, text=True, timeout=45,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        out = result.stdout.strip()
        # Truncate if too long (keep model context manageable)
        if len(out) > 3000:
            out = out[:3000] + f"\n...(truncated, {len(out)} chars total)"
        return out or f"(empty file or read error: {result.stderr})"
    except subprocess.TimeoutExpired:
        return f"File too large ({size_mb:.1f}MB) for preview. Try asking specific questions about the data."
    except Exception as e:
        return f"Read error: {e}"


def _list_files_str() -> str:
    """Return a listing of all uploaded files."""
    if not _uploaded_files:
        return "No files uploaded yet. Ask the user to upload a CSV or Excel file."
    lines = ["Uploaded files:"]
    for name, f in _uploaded_files.items():
        size_kb = len(f["bytes"]) / 1024
        lines.append(f"  - {name} ({size_kb:.1f} KB, {f['mimeType']})")
    return "\n".join(lines)


async def execute_tool(name: str, args: dict) -> str:
    """Dispatch tool execution and return result string."""
    t0 = time.time()
    logger.log(f"tool call: {name} args={json.dumps(args, ensure_ascii=False)[:120]}")

    if name == "code_interpreter":
        code = args.get("code", "")
        result = _exec_python(code)
    elif name == "read_file":
        filename = args.get("filename", "")
        result = _read_file_preview(filename)
    elif name == "list_files":
        result = _list_files_str()
    else:
        result = f"Unknown tool: {name}"

    elapsed = (time.time() - t0) * 1000
    logger.log(f"tool result: {name} ({elapsed:.0f}ms) → {result[:200]}")
    return result

# ═══════════════════════════════════════════════════════════════
# Handler
# ═══════════════════════════════════════════════════════════════

async def handler(ctx: Any) -> Any:
    cid = ctx.conversation_id or ""
    t_start = time.time()
    logger.log(f"handler entered, cid={cid}")

    try:
        body = ctx.request.body
        user_message = body.get("message", "") if isinstance(body, dict) else ""
        uploaded = body.get("files", []) if isinstance(body, dict) else []

        if not user_message.strip() and not uploaded:
            return {"error": "'message' or 'files' is required"}, 400

        # ── Store uploaded files for tool access ──
        if uploaded:
            _store_uploaded_files(uploaded)

        # ── Build user display text ──
        display_msg = user_message
        if uploaded:
            names = ", ".join(f["name"] for f in uploaded)
            display_msg = f"[Uploaded: {names}]" + (f"\n{user_message}" if user_message.strip() else "")

        # ── Persist user message ──
        if cid:
            try:
                await ctx.store.append_message(cid, "user", display_msg)
            except Exception as e:
                logger.error(f"store user: {e}")

        # ── Gateway config ──
        env = ctx.env
        api_key = env.get("AI_GATEWAY_API_KEY", "")
        base_url = env.get("AI_GATEWAY_BASE_URL", "https://ai-gateway.edgeone.link/v1")
        model = resolve_model_name(env)

        if not api_key:
            async def no_key_gen():
                yield ctx.utils.sse({"type": "error_message", "content": "Missing AI_GATEWAY_API_KEY"})
                yield b"data: [DONE]\n\n"
            return ctx.utils.stream_sse(no_key_gen())

        # ── Build messages for LLM ──
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": display_msg},
        ]

        # Only include tools when files are uploaded (avoids model overhead for simple chat)
        has_files = len(uploaded) > 0

        async def gen():
            nonlocal messages, has_files
            assistant_text = ""
            max_turns = 10
            turn = 0

            yield ctx.utils.sse({"type": "model_info", "model": model, "provider": "EdgeOne AI Gateway"})

            async with httpx.AsyncClient(timeout=300.0) as client:
                while turn < max_turns:
                    turn += 1
                    if ctx.request.signal.is_set():
                        yield ctx.utils.sse({"type": "status", "status": "aborted"})
                        break

                    # ── Signal to frontend ──
                    yield ctx.utils.sse({"type": "status", "status": "thinking"})

                    t_api = time.time()

                    # ── Stream from API — real-time text + tool call accumulation ──
                    streamed_content = ""
                    tool_call_accum: dict[int, dict] = {}

                    # Build request body — conditionally include tools
                    req_body = {
                        "model": model,
                        "messages": messages,
                        "stream": True,
                    }
                    if has_files:
                        req_body["tools"] = TOOLS
                        req_body["tool_choice"] = "auto"

                    try:
                        async with client.stream(
                            "POST",
                            f"{base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json=req_body,
                        ) as stream_response:
                            if stream_response.status_code != 200:
                                err_body = (await stream_response.aread()).decode()[:300]
                                logger.error(f"API {stream_response.status_code}: {err_body}")
                                yield ctx.utils.sse({"type": "error_message", "content": f"Gateway {stream_response.status_code}"})
                                break

                            async for line in stream_response.aiter_lines():
                                if ctx.request.signal.is_set():
                                    break
                                if not line.startswith("data: "):
                                    continue
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                except json.JSONDecodeError:
                                    continue

                                delta = chunk.get("choices", [{}])[0].get("delta", {})

                                # ── Text content: stream immediately ──
                                content = delta.get("content", "") or ""
                                if content:
                                    streamed_content += content
                                    yield ctx.utils.sse({"type": "ai_response", "content": content})

                                # ── Tool calls: accumulate by index ──
                                for tc in delta.get("tool_calls", []):
                                    idx = tc.get("index", 0)
                                    if idx not in tool_call_accum:
                                        tool_call_accum[idx] = {"id": "", "name": "", "arguments": ""}
                                    entry = tool_call_accum[idx]
                                    if tc.get("id"):
                                        entry["id"] = tc["id"]
                                    fn = tc.get("function", {})
                                    if fn.get("name"):
                                        entry["name"] = fn["name"]
                                    if fn.get("arguments"):
                                        entry["arguments"] += fn["arguments"]

                    except httpx.ReadError as e:
                        if not ctx.request.signal.is_set():
                            logger.error(f"stream read error: {e}")
                            yield ctx.utils.sse({"type": "error_message", "content": f"Stream error: {e}"})
                        break
                    except Exception as e:
                        logger.error(f"API call failed: {e}")
                        yield ctx.utils.sse({"type": "error_message", "content": f"API error: {e}"})
                        break

                    if ctx.request.signal.is_set():
                        yield ctx.utils.sse({"type": "status", "status": "aborted"})
                        break

                    api_ms = (time.time() - t_api) * 1000
                    logger.log(f"stream round-trip: {api_ms:.0f}ms (turn {turn})")

                    # ── Process accumulated tool calls ──
                    tool_calls_list = sorted(
                        [v for v in tool_call_accum.values() if v["name"]],
                        key=lambda x: list(tool_call_accum.keys())[list(tool_call_accum.values()).index(x)]
                    )
                    # Deduplicate & preserve order
                    seen = set()
                    ordered_tool_calls = []
                    for tc in tool_calls_list:
                        key = (tc["id"], tc["name"])
                        if key not in seen:
                            seen.add(key)
                            ordered_tool_calls.append(tc)

                    if ordered_tool_calls:
                        yield ctx.utils.sse({"type": "status", "status": "executing"})

                        tool_results = {}
                        for tc in ordered_tool_calls:
                            if ctx.request.signal.is_set():
                                break
                            tool_name = tc["name"]
                            tc_id = tc["id"]
                            try:
                                tool_args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                            except json.JSONDecodeError:
                                tool_args = {"raw": tc["arguments"]}

                            yield ctx.utils.sse({
                                "type": "tool_call",
                                "id": tc_id,
                                "name": tool_name,
                                "args": tool_args,
                            })

                            result = await execute_tool(tool_name, tool_args)
                            tool_results[tc_id] = result

                            yield ctx.utils.sse({
                                "type": "tool_result",
                                "id": tc_id,
                                "name": tool_name,
                                "preview": result[:500] + ("..." if len(result) > 500 else ""),
                                "length": len(result),
                            })

                        if ctx.request.signal.is_set():
                            yield ctx.utils.sse({"type": "status", "status": "aborted"})
                            break

                        # Append to message history for next turn
                        openai_tool_calls = [
                            {"id": tc["id"], "type": "function",
                             "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                            for tc in ordered_tool_calls
                        ]
                        messages.append({"role": "assistant", "content": None, "tool_calls": openai_tool_calls})
                        for tc in ordered_tool_calls:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": tool_results.get(tc["id"], "(no result)"),
                            })
                        continue  # next turn

                    # ── Text response complete ──
                    if streamed_content:
                        assistant_text = streamed_content
                    break

            # ── Send [DONE] FIRST so frontend completes immediately ──
            yield b"data: [DONE]\n\n"

            # ── Persist assistant message (after [DONE], doesn't block UI) ──
            if cid and assistant_text.strip():
                try:
                    await ctx.store.append_message(cid, "assistant", assistant_text.strip())
                except Exception as e:
                    logger.error(f"store assistant: {e}")

            total_ms = (time.time() - t_start) * 1000
            logger.log(f"handler done: {len(assistant_text)} chars, {total_ms:.0f}ms total")

        return ctx.utils.stream_sse(gen())

    except Exception as e:
        logger.error(f"handler error: {e}")
        async def err_gen():
            yield ctx.utils.sse({"type": "error_message", "content": str(e)})
            yield b"data: [DONE]\n\n"
        return ctx.utils.stream_sse(err_gen())


