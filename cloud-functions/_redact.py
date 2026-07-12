"""Redact sensitive fields from log output."""

REDACT_KEYS = {"api_key", "token", "password", "secret", "authorization"}


def redact(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    result = {}
    for k, v in data.items():
        if k.lower() in REDACT_KEYS:
            result[k] = "***"
        elif isinstance(v, dict):
            result[k] = redact(v)
        else:
            result[k] = v
    return result
