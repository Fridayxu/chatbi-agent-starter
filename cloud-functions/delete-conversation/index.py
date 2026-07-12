"""POST /delete-conversation — permanently delete a conversation."""


async def handler(ctx):
    body = ctx.request.body or {}
    cid = body.get("conversation_id", "")
    if not cid:
        return {"error": "conversation_id is required"}, 400

    try:
        await ctx.store.delete_conversation(cid)
        return {"status": "deleted", "conversation_id": cid}
    except Exception as e:
        return {"error": str(e)}, 500
