"""
ChatBI Agent — POST /chat
Supply chain data analysis powered by Claude Agent SDK + EdgeOne Makers.

Follows EdgeOne Makers Python Claude Agent SDK convention:
- ctx.env (never os.environ)
- CLAUDE_CONFIG_DIR + CLAUDE_CODE_TMPDIR for writable config
- SSE via ctx.utils.stream_sse(gen())
- Abort via ctx.request.signal.is_set()
"""

from __future__ import annotations

import time
from typing import AsyncGenerator

from claude_agent_sdk import query, create_sdk_mcp_server

from .._model import resolve_model_name, collect_gateway_env
from .._logger import create_logger

logger = create_logger("chatbi")

CHATBI_SYSTEM_PROMPT = """You are **ChatBI Agent** — a supply chain data analyst powered by Claude Agent SDK on EdgeOne Makers.

## Capabilities
- **EDA**: summary stats, missing values, distributions, correlation, trend detection
- **Forecasting**: time series, WMAPE/MAPE evaluation, baseline comparison
- **ABC/XYZ**: product classification by revenue contribution and demand variability
- **Inventory**: safety stock, ROP, EOQ, service level analysis
- **Promotional Impact**: lift analysis, statistical significance
- **Pricing**: elasticity, competitor analysis
- **Visualization**: matplotlib charts (line, bar, heatmap, scatter, donut)

## Tools
- code_interpreter: run Python (pandas, numpy, matplotlib, scipy)
- files: read/write/list sandbox files
- commands: shell commands (pip install if needed)
- browser: fetch external data

## File Upload
When user uploads a file (CSV/Excel), it's saved to /tmp/uploads/.
Read it with files tool first, then analyze with code_interpreter.

## Output Standards
- Charts: title, axis labels, legend, data source
- Numbers: formatted with commas
- Chinese when user writes Chinese
- Structure: Key Finding → Evidence → Recommendation

Reply concisely. Use tools one at a time, wait for results."""


async def handler(ctx) -> AsyncGenerator[str, None]:
    """EdgeOne Makers agent entry point for POST /chat."""
    cid = ctx.conversation_id or ""
    logger.log(f"chat entered, cid={cid}")

    body = ctx.request.body
    user_message = body.get("message", "") if isinstance(body, dict) else ""
    files_data = body.get("files", []) if isinstance(body, dict) else []

    # ---- Process file uploads ----
    file_context = ""
    if files_data:
        import base64, os as _os
        _os.makedirs("/tmp/uploads", exist_ok=True)
        for f in files_data:
            fname = f.get("name", "upload")
            fcontent = f.get("content", "")
            try:
                raw = base64.b64decode(fcontent)
                path = f"/tmp/uploads/{fname}"
                with open(path, "wb") as fh:
                    fh.write(raw)
                file_context += f"\n[Uploaded: {fname} ({len(raw)} bytes), path: {path}]"
            except Exception as e:
                logger.error(f"file upload failed: {fname}: {e}")

    if not user_message.strip() and not files_data:
        yield ctx.utils.sse({"type": "error_message", "content": "'message' is required"})
        yield b"data: [DONE]\n\n"
        return

    if file_context:
        user_message = file_context + "\n" + (user_message.strip() or "Please analyze the uploaded file data")

    # Save user message to store
    if cid:
        try:
            await ctx.store.append_message(cid, "user", user_message)
        except Exception as e:
            logger.error(f"store save failed: {e}")

    # ---- Build Claude Agent SDK options ----
    env = ctx.env  # ⚠️ ctx.env, never os.environ
    gateway_env = collect_gateway_env(env)
    gateway_env["CLAUDE_CONFIG_DIR"] = "/tmp/claude-agent-sdk"
    gateway_env["CLAUDE_CODE_TMPDIR"] = "/tmp"

    model = resolve_model_name(env)
    logger.log(f"model={model}")

    edgeone_bundle = ctx.tools.to_claude_mcp_server("edgeone", always_load=True)
    edgeone_mcp = create_sdk_mcp_server(name=edgeone_bundle.name, tools=edgeone_bundle.tools)

    options = {
        "model": model,
        "system_prompt": CHATBI_SYSTEM_PROMPT,
        "env": gateway_env,
        "max_turns": 30,
        "mcp_servers": {"edgeone": edgeone_mcp},
        "allowed_tools": edgeone_bundle.allowed_tools,
        "permission_mode": "dontAsk",
        "include_partial_messages": True,
    }

    # ---- SSE streaming generator ----
    async def gen():
        assistant_text = ""

        try:
            stream = query(prompt=user_message, options=options)

            async for msg in stream:
                if ctx.request.signal.is_set():
                    logger.log("aborted by signal")
                    break

                if hasattr(msg, "text") and msg.text:
                    assistant_text += msg.text
                    yield ctx.utils.sse({"type": "ai_response", "content": msg.text})

                elif hasattr(msg, "tool_name") and msg.tool_name:
                    logger.log(f"tool: {msg.tool_name}")
                    yield ctx.utils.sse({"type": "tool_call", "name": msg.tool_name})

        except Exception as e:
            if not ctx.request.signal.is_set():
                logger.error(str(e))
                yield ctx.utils.sse({"type": "error_message", "content": str(e)})

        # Save assistant response
        if cid and assistant_text.strip():
            try:
                await ctx.store.append_message(cid, "assistant", assistant_text.strip())
            except Exception as e:
                logger.error(f"store save assistant failed: {e}")

        yield b"data: [DONE]\n\n"

    return ctx.utils.stream_sse(gen())
