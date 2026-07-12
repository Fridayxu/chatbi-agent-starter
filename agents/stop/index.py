"""POST /stop — abort the running agent for a conversation."""


async def handler(ctx):
    target = ctx.request.body.get("conversation_id") or ""
    if not target:
        return {"error": "Missing conversation_id"}, 400

    result = ctx.utils.abortActiveRun(target)
    return {
        "status": "aborted" if result.aborted else "idle",
        "conversation_id": result.conversation_id,
        "run_id": result.run_id,
    }
