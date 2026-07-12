"""POST /conversations — list conversations for the current user."""

async def handler(ctx):
    # ctx in cloud-functions IS the request; body is at ctx.body
    body = getattr(ctx, 'body', {}) or {}
    limit = min(int(body.get("limit", 20)), 100)
    store = getattr(ctx, 'store', None) or getattr(getattr(ctx, 'agent', None), 'store', None)
    if not store:
        return {"error": "store not available"}, 500
    try:
        conversations = await store.list_conversations(limit=limit, order="desc")
        return {"conversations": conversations}
    except Exception as e:
        return {"error": str(e)}, 500
