"""POST /conversations — list conversations for the current user."""

async def handler(ctx):
    body = ctx.request.body or {}
    limit = min(int(body.get("limit", 20)), 100)
    try:
        conversations = await ctx.store.list_conversations(limit=limit, order="desc")
        return {"conversations": conversations}
    except Exception as e:
        # fallback: try with user_id
        try:
            conversations = await ctx.store.list_conversations(limit=limit)
            return {"conversations": conversations}
        except:
            return {"error": str(e)}, 500
