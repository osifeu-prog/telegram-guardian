import os

def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def get_api_id() -> int:
    return int(require_env("TG_API_ID"))

def get_api_hash() -> str:
    return require_env("TG_API_HASH")
