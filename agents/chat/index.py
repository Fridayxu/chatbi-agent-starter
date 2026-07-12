"""
ChatBI Agent — POST /chat
Uses EdgeOne AI Gateway directly (OpenAI-compatible) for reliable model access.
"""
from __future__ import annotations

import json, time, httpx
from typing import Any

from .._model import resolve_model_name, collect_gateway_env
from .._logger import create_logger

logger = create_logger("chatbi")

SYSTEM_PROMPT = """You are ChatBI Agent, a supply chain data analyst.

Capabilities: EDA, demand forecasting, ABC/XYZ classification, inventory optimization, promotional impact analysis, competitive pricing analysis, data visualization (matplotlib).

You have access to sandbox tools: code_interpreter (Python), files, commands, browser.

When users upload CSV/Excel files, read them with the files tool first, then analyze with code_interpreter.
Use Chinese when the user writes Chinese. Keep replies concise and data-driven."""


async def handler(ctx: Any) -> Any:
    cid = ctx.conversation_id or ""
    logger.log(f"handler entered, cid={cid}")

    try:
        body = ctx.request.body
        user_message = body.get("message", "") if isinstance(body, dict) else ""

        if not user_message.strip():
            return {"error": "'message' is required"}, 400

        # Save user message
        if cid:
            try:
                await ctx.store.append_message(cid, "user", user_message)
            except Exception as e:
                logger.error(f"store: {e}")

        # Get gateway config from env
        env = ctx.env
        api_key = env.get("AI_GATEWAY_API_KEY", "")
        base_url = env.get("AI_GATEWAY_BASE_URL", "https://ai-gateway.edgeone.link/v1")
        model = env.get("AI_GATEWAY_MODEL", "@makers/deepseek-v4-flash")

        if not api_key:
            async def err_gen():
                yield ctx.utils.sse({"type": "error_message", "content": "Missing AI_GATEWAY_API_KEY"})
                yield b"data: [DONE]\n\n"
            return ctx.utils.stream_sse(err_gen())

        async def gen():
            assistant_text = ""
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        f"{base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_message},
                            ],
                            "stream": True,
                        },
                    ) as response:
                        async for line in response.aiter_lines():
                            if ctx.request.signal.is_set():
                                break
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        assistant_text += content
                                        yield ctx.utils.sse({"type": "ai_response", "content": content})
                                except (json.JSONDecodeError, KeyError):
                                    pass
            except Exception as e:
                logger.error(f"stream error: {e}")
                yield ctx.utils.sse({"type": "error_message", "content": str(e)})

            if cid and assistant_text.strip():
                try:
                    await ctx.store.append_message(cid, "assistant", assistant_text.strip())
                except Exception as e:
                    logger.error(f"save: {e}")

            yield b"data: [DONE]\n\n"

        return ctx.utils.stream_sse(gen())

    except Exception as e:
        logger.error(f"handler error: {e}")
        async def err_gen():
            yield ctx.utils.sse({"type": "error_message", "content": str(e)})
            yield b"data: [DONE]\n\n"
        return ctx.utils.stream_sse(err_gen())
