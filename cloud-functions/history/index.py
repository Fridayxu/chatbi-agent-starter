"""POST /history — fetch message history for a conversation."""

async def handler(ctx):
    body = getattr(ctx, 'body', {}) or {}
    cid = body.get("conversation_id", "")
    if not cid:
        return {"error": "conversation_id is required"}, 400
    store = getattr(ctx, 'store', None) or getattr(getattr(ctx, 'agent', None), 'store', None)
    if not store:
        return {"error": "store not available"}, 500
    limit = min(int(body.get("limit", 50)), 100)
    try:
        messages = await store.get_messages(cid, limit=limit)
        return {"conversation_id": cid, "messages": messages}
    except Exception as e:
        return {"error": str(e)}, 500
