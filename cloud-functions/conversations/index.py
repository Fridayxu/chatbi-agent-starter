"""
GET /conversations — list all conversations for the current user.
"""
from __future__ import annotations
from typing import Any

async def handler(ctx: Any) -> Any:
    store = getattr(ctx, "store", None) or getattr(getattr(ctx, "agent", None), "store", None)
    if not store:
        return {"conversations": [], "error": "store not available"}

    try:
        conversations = await store.list_conversations(limit=30, order="desc")
        result = []
        for c in conversations:
            result.append({
                "id": c.get("id") or c.get("conversation_id", ""),
                "created_at": c.get("created_at") or c.get("createdAt", ""),
                "updated_at": c.get("updated_at") or c.get("updatedAt", ""),
                "title": c.get("title") or c.get("metadata", {}).get("title", ""),
            })
        return {"conversations": result}
    except Exception as e:
        return {"conversations": [], "error": str(e)}
