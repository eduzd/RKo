import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from auth_utils import CurrentUser

PUSH_BASE_URL = "https://integrations.emergentagent.com"
PUSH_KEY = os.environ.get("EMERGENT_PUSH_KEY", "placeholder")

_client = httpx.AsyncClient(
    base_url=PUSH_BASE_URL,
    headers={"X-Push-Key": PUSH_KEY},
    timeout=10.0,
)

router = APIRouter(tags=["push"])


class RegisterPushBody(BaseModel):
    user_id: str
    platform: str  # "android" | "ios"
    device_token: str


@router.post("/register-push", status_code=201)
async def register_push(body: RegisterPushBody, current_user: CurrentUser):
    # Always register against the authenticated user, never a spoofed id.
    payload = body.model_dump()
    payload["user_id"] = current_user["_id"]
    resp = await _client.post("/api/v1/push/users/register", json=payload)
    if resp.status_code == 401:
        raise HTTPException(status_code=500, detail="EMERGENT_PUSH_KEY missing or invalid")
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="Push provider unavailable")
    resp.raise_for_status()
    return {"status": "registered"}


async def send_push(
    recipients: list[str],
    data: dict,
    idempotency_key: str | None = None,
) -> None:
    """Relay a push to one or more user ids via the Emergent push service.
    Callers MUST wrap this in try/except — a push failure must never block
    the primary operation (sending a message, following a user, etc.)."""
    if not recipients:
        return
    recipients = recipients[:100]
    if "title" not in data or "message" not in data:
        raise ValueError("data must include title and message")
    payload: dict = {"recipients": recipients, "data": data}
    if idempotency_key:
        payload["$idempotency_key"] = idempotency_key
    resp = await _client.post("/api/v1/push/trigger", json=payload)
    if resp.status_code == 401:
        raise HTTPException(status_code=500, detail="EMERGENT_PUSH_KEY missing or invalid")
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="Push provider unavailable")
    resp.raise_for_status()
