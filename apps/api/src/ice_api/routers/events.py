"""Events router — Server-Sent Events stream for real-time notifications.

POST /api/v1/events/token — issue a short-lived SSE auth token (JWT-authed).
GET  /api/v1/events/stream  — SSE stream; subscribes to Redis pub/sub and
                               forwards ``notification`` events to the client.

Auth: EventSource cannot send Authorization headers, so the stream is authed
via a signed query token (HMAC of ``user_id:expiry``). Tokens are issued by the
authed ``POST /token`` endpoint and verified server-side.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ice_shared import settings
from ice_api.auth_utils import get_current_user
from ice_api.models import User

router = APIRouter(prefix="/api/v1/events", tags=["events"])

_TOKEN_TTL_SEC = 3600


def _secret() -> str:
    return settings.sse_token_secret or settings.jwt_secret


def _issue_token(user_id: str, ttl: int = _TOKEN_TTL_SEC) -> str:
    exp = int(time.time()) + ttl
    msg = f"{user_id}:{exp}".encode()
    sig = hmac.new(_secret().encode(), msg, hashlib.sha256).hexdigest()
    return f"{user_id}:{exp}:{sig}"


def _verify_token(token: str) -> str | None:
    try:
        uid_s, exp_s, sig = token.split(":")
        uid, exp = uid_s, int(exp_s)
    except (ValueError, AttributeError):
        return None
    if exp < int(time.time()):
        return None
    expected = hmac.new(
        _secret().encode(), f"{uid}:{exp}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return uid


@router.post("/token")
async def issue_sse_token(current_user: User = Depends(get_current_user)) -> dict:
    return {"token": _issue_token(str(current_user.id))}


@router.get("/stream")
async def event_stream(token: str, request: Request) -> StreamingResponse:
    user_id = _verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    async def generate():
        import redis.asyncio as aioredis

        r = aioredis.Redis.from_url(settings.redis.url)
        pubsub = r.pubsub()
        channel = f"ice:notifications:{user_id}"
        await pubsub.subscribe(channel)
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"event: notification\ndata: {data}\n\n"
                else:
                    yield ": ping\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await r.aclose()

    return StreamingResponse(generate(), media_type="text/event-stream")
