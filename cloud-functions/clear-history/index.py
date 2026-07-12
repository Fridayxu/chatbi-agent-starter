"""POST /clear-history — clear messages for a conversation."""


async def handler(ctx):
    body = ctx.request.body or {}
    cid = body.get("conversation_id", "")
    if not cid:
        return {"error": "conversation_id is required"}, 400

    try:
        await ctx.store.clear_messages(cid)
        return {"status": "cleared", "conversation_id": cid}
    except Exception as e:
        return {"error": str(e)}, 500
