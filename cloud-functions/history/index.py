"""POST /history — fetch message history for a conversation."""


async def handler(ctx):
    body = ctx.request.body or {}
    cid = body.get("conversation_id", "")
    if not cid:
        return {"error": "conversation_id is required"}, 400

    limit = min(int(body.get("limit", 50)), 100)
    try:
        messages = await ctx.store.get_messages(cid, limit=limit)
        return {"conversation_id": cid, "messages": messages}
    except Exception as e:
        return {"error": str(e)}, 500
