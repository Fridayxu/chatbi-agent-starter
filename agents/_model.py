"""
Model configuration — follows EdgeOne Makers Python Claude Agent SDK conventions.
Reads from ctx.env (never os.environ per platform rules).
"""

DEFAULT_MODEL = "@makers/deepseek-v4-flash"


def resolve_model_name(env: dict) -> str:
    return env.get("AI_GATEWAY_MODEL") or DEFAULT_MODEL


def collect_gateway_env(env: dict) -> dict:
    """Map AI_GATEWAY_* -> ANTHROPIC_* variables the SDK expects."""
    result = {}
    if env.get("AI_GATEWAY_BASE_URL"):
        result["ANTHROPIC_BASE_URL"] = env["AI_GATEWAY_BASE_URL"]
    if env.get("AI_GATEWAY_API_KEY"):
        result["ANTHROPIC_API_KEY"] = env["AI_GATEWAY_API_KEY"]
    small = env.get("AI_GATEWAY_SMALL_MODEL") or env.get("AI_GATEWAY_MODEL") or DEFAULT_MODEL
    result["ANTHROPIC_SMALL_FAST_MODEL"] = small
    if env.get("ANTHROPIC_CUSTOM_HEADERS"):
        result["ANTHROPIC_CUSTOM_HEADERS"] = env["ANTHROPIC_CUSTOM_HEADERS"]
    return result
