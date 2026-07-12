"""
GET /history?conversation_id=xxx — get messages for a conversation.
"""
from __future__ import annotations
from typing import Any

async def handler(ctx: Any) -> Any:
    store = getattr(ctx, "store", None) or getattr(getattr(ctx, "agent", None), "store", None)
    if not store:
        return {"messages": [], "error": "store not available"}

    cid = ""
    if hasattr(ctx, "request"):
        body = getattr(ctx.request, "body", {}) or {}
        if isinstance(body, dict):
            cid = body.get("conversation_id", "")
        if not cid:
            qs = getattr(ctx.request, "query", {}) or {}
            if isinstance(qs, dict):
                cid = qs.get("conversation_id", "")

    if not cid:
        return {"messages": [], "error": "missing conversation_id"}

    try:
        messages = await store.get_messages(cid, limit=100, order="asc")
        result = []
        for m in messages:
            result.append({
                "id": m.get("id", ""),
                "role": m.get("role", ""),
                "content": m.get("content", ""),
                "created_at": m.get("created_at") or m.get("createdAt", ""),
            })
        return {"conversation_id": cid, "messages": result}
    except Exception as e:
        return {"conversation_id": cid, "messages": [], "error": str(e)}
