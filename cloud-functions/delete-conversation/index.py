"""POST /delete-conversation — permanently delete a conversation."""

async def handler(ctx):
    body = getattr(ctx, 'body', {}) or {}
    cid = body.get("conversation_id", "")
    if not cid:
        return {"error": "conversation_id is required"}, 400
    store = getattr(ctx, 'store', None) or getattr(getattr(ctx, 'agent', None), 'store', None)
    if not store:
        return {"error": "store not available"}, 500
    try:
        await store.delete_conversation(cid)
        return {"status": "deleted", "conversation_id": cid}
    except Exception as e:
        return {"error": str(e)}, 500
