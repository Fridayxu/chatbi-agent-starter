"""
POST /delete-conversation — delete a conversation and its messages.
"""
from __future__ import annotations
from typing import Any

async def handler(ctx: Any) -> Any:
    store = getattr(ctx, "store", None) or getattr(getattr(ctx, "agent", None), "store", None)
    if not store:
        return {"ok": False, "error": "store not available"}

    body = getattr(ctx.request, "body", {}) or {}
    cid = body.get("conversation_id", "") if isinstance(body, dict) else ""

    if not cid:
        return {"ok": False, "error": "missing conversation_id"}

    try:
        await store.delete_conversation(cid)
        return {"ok": True, "deleted": cid}
    except Exception as e:
        return {"ok": False, "error": str(e)}
