import os
from fastapi import Header, HTTPException
from typing import Annotated


def get_api_keys() -> set[str]:
    raw = os.getenv("CIF_API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> str:
    keys = get_api_keys()
    if not keys:
        raise HTTPException(status_code=500, detail="No API keys configured")
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
