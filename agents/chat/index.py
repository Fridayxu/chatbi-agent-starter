"""
ChatBI Agent — POST /chat
Supply chain data analysis powered by Claude Agent SDK + EdgeOne Makers.
"""

from __future__ import annotations

import time
from typing import Any

from claude_agent_sdk import query, create_sdk_mcp_server, ClaudeAgentOptions

from .._model import resolve_model_name, collect_gateway_env
from .._logger import create_logger

logger = create_logger("chatbi")

CHATBI_SYSTEM_PROMPT = """You are **ChatBI Agent** — a supply chain data analyst on EdgeOne Makers.

## Capabilities
- EDA: summary stats, missing values, distributions, correlations, trends
- Forecasting: time series, WMAPE/MAPE, baseline comparison
- ABC/XYZ: product classification by revenue and demand variability
- Inventory: safety stock, ROP, EOQ, service level
- Promotional Impact: lift analysis, significance testing
- Pricing: elasticity, competitor analysis
- Visualization: matplotlib (line, bar, heatmap, scatter, donut)

## Tools
- code_interpreter: Python (pandas, numpy, matplotlib, scipy)
- files: read/write sandbox files
- commands: shell commands
- browser: fetch web data

## File Upload
Uploaded files saved to /tmp/uploads/. Read with files tool first.

## Rules
- Chinese when user writes Chinese
- Use tools one at a time, wait for each result
- Key Finding -> Evidence -> Recommendation

Reply concisely."""


async def handler(ctx: Any) -> Any:
    """EdgeOne Makers entry point for POST /chat."""
    cid = ctx.conversation_id or ""
    logger.log(f"handler entered, cid={cid}")

    try:
        body = ctx.request.body
        user_message = body.get("message", "") if isinstance(body, dict) else ""
        files_data = body.get("files", []) if isinstance(body, dict) else []

        # ---- File uploads ----
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
                    file_context += f"\n[Uploaded: {fname} ({len(raw)} bytes)]"
                except Exception as e:
                    logger.error(f"upload failed: {e}")

        if not user_message.strip() and not files_data:
            return {"error": "'message' is required"}, 400

        if file_context:
            user_message = file_context + "\n" + (user_message.strip() or "Analyze the uploaded data")

        # Save user message
        if cid:
            try:
                await ctx.store.append_message(cid, "user", user_message)
            except Exception as e:
                logger.error(f"store failed: {e}")

        # ---- Build options ----
        env = ctx.env
        gateway_env = collect_gateway_env(env)
        gateway_env["CLAUDE_CONFIG_DIR"] = "/tmp/claude-agent-sdk"
        gateway_env["CLAUDE_CODE_TMPDIR"] = "/tmp"
        gateway_env["HOME"] = "/tmp"
        gateway_env["TMPDIR"] = "/tmp"
        gateway_env["CLAUDE_CODE_HOME"] = "/tmp"
        model = resolve_model_name(env)  # keep @makers/ prefix per EdgeOne docs
        logger.log(f"model={model}, base_url={gateway_env.get('ANTHROPIC_BASE_URL','')}")

        edgeone_bundle = ctx.tools.to_claude_mcp_server("edgeone")
        edgeone_mcp = create_sdk_mcp_server(name=edgeone_bundle.name, tools=edgeone_bundle.tools)

        options = ClaudeAgentOptions(
            model=model,
            system_prompt=CHATBI_SYSTEM_PROMPT,
            env=gateway_env,
            max_turns=30,
            mcp_servers={"edgeone": edgeone_mcp},
            allowed_tools=edgeone_bundle.allowed_tools,
            permission_mode="dontAsk",
            include_partial_messages=True,
        )

        # ---- SSE stream ----
        async def gen():
            assistant_text = ""
            try:
                logger.log("starting query stream")
                stream = query(prompt=user_message, options=options)
                first = True
                async for msg in stream:
                    if first:
                        logger.log(f"msg_type={type(msg).__name__}, attrs={[a for a in dir(msg) if not a.startswith('_')]}")
                        first = False
                    if ctx.request.signal.is_set():
                        logger.log("aborted")
                        break

                    # Handle all message types from Claude Agent SDK
                    text = ""
                    if hasattr(msg, "text") and msg.text:
                        text = msg.text
                    elif hasattr(msg, "content") and msg.content:
                        # AssistantMessage has content blocks
                        blocks = msg.content if isinstance(msg.content, list) else [msg.content]
                        for b in blocks:
                            if hasattr(b, "text") and b.text:
                                text += b.text

                    if text:
                        assistant_text += text
                        yield ctx.utils.sse({"type": "ai_response", "content": text})

                    if hasattr(msg, "tool_name") and msg.tool_name:
                        logger.log(f"tool: {msg.tool_name}")
                        yield ctx.utils.sse({"type": "tool_call", "name": msg.tool_name})
            except Exception as e:
                err_msg = str(e)
                logger.error(f"stream error: {err_msg}")
                yield ctx.utils.sse({"type": "error_message", "content": err_msg})

            if cid and assistant_text.strip():
                try:
                    await ctx.store.append_message(cid, "assistant", assistant_text.strip())
                except Exception as e:
                    logger.error(f"save assistant failed: {e}")

            yield b"data: [DONE]\n\n"

        return ctx.utils.stream_sse(gen())

    except Exception as e:
        err_msg = str(e)
        logger.error(f"handler error: {err_msg}")

        async def err_gen():
            yield ctx.utils.sse({"type": "error_message", "content": f"Agent error: {err_msg}"})
            yield b"data: [DONE]\n\n"

        return ctx.utils.stream_sse(err_gen())
