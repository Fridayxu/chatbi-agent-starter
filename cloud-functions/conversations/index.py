"""POST /conversations — list conversations for a user."""


async def handler(ctx):
    body = ctx.request.body or {}
    user_id = body.get("user_id", "")
    if not user_id:
        return {"error": "user_id is required"}, 400

    limit = min(int(body.get("limit", 20)), 100)
    try:
        conversations = await ctx.store.list_conversations(user_id, limit=limit)
        return {"conversations": conversations}
    except Exception as e:
        return {"error": str(e)}, 500
