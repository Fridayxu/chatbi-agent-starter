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

SYSTEM_PROMPT = """You are ChatBI Agent, a supply chain data analyst running on EdgeOne Makers.

## Your Environment
You have access to REAL tools — use them. Don't pretend to run code, actually call the tools.

| Tool | Purpose |
|------|---------|
| `code_interpreter` | Run Python to analyze data. Use pandas, numpy, matplotlib, scipy, statsmodels. Output (stdout + stderr) is returned. For charts, save to '/tmp/chart.png' with plt.savefig(). |
| `read_file` | Read an uploaded CSV/Excel/JSON file into a pandas DataFrame. Returns first 20 rows preview + shape + dtypes. |
| `list_files` | List all uploaded files available for analysis. |

## Rules
- When a user uploads a file, FIRST call `list_files` to see what's available, then `read_file` to inspect it.
- Run analyses with `code_interpreter`. Install packages with `!pip install ...` (subprocess runs in bash).
- For charts: save to `/tmp/chart.png`, I'll display it. Use dark-themed matplotlib styles.
- Use Chinese when the user writes Chinese.
- Keep replies concise and data-driven. Show key numbers."""

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
    """Execute Python code in a subprocess with a timeout. Safe and isolated."""
    # Replace !pip install patterns with actual pip install calls
    lines = code.split("\n")
    pre_install = []
    actual_code = []
    for line in lines:
        if line.strip().startswith("!pip install"):
            pkg = line.strip()[len("!pip install"):].strip()
            pre_install.append(pkg)
        elif line.strip().startswith("!pip3 install"):
            pkg = line.strip()[len("!pip3 install"):].strip()
            pre_install.append(pkg)
        else:
            actual_code.append(line)

    script_parts = []
    script_parts.append("import sys, os, warnings")
    script_parts.append("warnings.filterwarnings('ignore')")
    script_parts.append("os.environ['MPLBACKEND'] = 'Agg'")

    # Pre-install packages
    for pkg in pre_install:
        script_parts.append(f"import subprocess as _sp")
        script_parts.append(f"_sp.run([sys.executable, '-m', 'pip', 'install', '-q', '{pkg}'], check=False)")

    # Actual code
    script_parts.append("\n".join(actual_code))

    full_script = "\n".join(script_parts)

    try:
        result = subprocess.run(
            ["python", "-c", full_script],
            capture_output=True,
            text=True,
            timeout=60,
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
    """Read an uploaded file and return a pandas preview."""
    if filename not in _uploaded_files:
        available = ", ".join(_uploaded_files.keys()) or "(none)"
        return f"File '{filename}' not found. Available files: {available}"

    f = _uploaded_files[filename]
    raw = f["bytes"]
    mime = f["mimeType"]

    # Write to temp file for pandas to read
    tmp_path = Path("/tmp") / filename
    tmp_path.write_bytes(raw)

    try:
        code = f'''
import pandas as pd, io
path = "{tmp_path.as_posix()}"
mime = "{mime}"
if mime.endswith("csv") or path.endswith(".csv") or path.endswith(".txt"):
    df = pd.read_csv(path, nrows=1000)
elif mime.endswith("excel") or path.endswith(".xlsx") or path.endswith(".xls"):
    df = pd.read_excel(path, nrows=1000)
elif path.endswith(".json"):
    df = pd.read_json(path, nrows=1000)
else:
    df = pd.read_csv(path, nrows=1000)

print(f"Shape: {{df.shape[0]}} rows × {{df.shape[1]}} columns")
print(f"Columns: {{list(df.columns)}}")
print(f"\\nDtypes:\\n{{df.dtypes.to_string()}}")
print(f"\\nFirst 20 rows:\\n{{df.head(20).to_string()}}")
if df.isnull().sum().sum() > 0:
    print(f"\\nMissing values:\\n{{df.isnull().sum().to_string()}}")
if df.describe().iloc[0].notna().any():
    print(f"\\nSummary stats:\\n{{df.describe().to_string()}}")
'''
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        return result.stdout.strip() or f"(empty file or read error: {result.stderr})"
    except Exception as e:
        return f"❌ Read error: {e}"


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

        async def gen():
            nonlocal messages
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

                    # ── Signal to frontend: LLM is thinking ──
                    yield ctx.utils.sse({"type": "status", "status": "thinking"})

                    t_api = time.time()

                    # ── Stream from API — real-time text + tool call accumulation ──
                    streamed_content = ""
                    tool_call_accum: dict[int, dict] = {}  # index → {id, name, arguments}

                    try:
                        async with client.stream(
                            "POST",
                            f"{base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model,
                                "messages": messages,
                                "tools": TOOLS,
                                "tool_choice": "auto",
                                "stream": True,
                            },
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

            # ── Persist assistant message ──
            if cid and assistant_text.strip():
                try:
                    await ctx.store.append_message(cid, "assistant", assistant_text.strip())
                except Exception as e:
                    logger.error(f"store assistant: {e}")

            total_ms = (time.time() - t_start) * 1000
            logger.log(f"handler done: {len(assistant_text)} chars, {total_ms:.0f}ms total")
            yield b"data: [DONE]\n\n"

        return ctx.utils.stream_sse(gen())

    except Exception as e:
        logger.error(f"handler error: {e}")
        async def err_gen():
            yield ctx.utils.sse({"type": "error_message", "content": str(e)})
            yield b"data: [DONE]\n\n"
        return ctx.utils.stream_sse(err_gen())


