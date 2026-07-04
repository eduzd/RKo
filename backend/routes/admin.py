import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth_utils import get_current_user
from config_utils import DEFAULTS, get_app_config
from db import (
    config_col,
    conversations_col,
    market_config_col,
    messages_col,
    moments_col,
    rooms_col,
    users_col,
)
from routes.market import CATALOG
from ws_manager import manager

router = APIRouter(prefix="/admin", tags=["admin"])

# /app/backend/routes/admin.py -> parents: routes, backend, app (root)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FRONTEND_DIR = _REPO_ROOT / "frontend"

# Registry of build-time integration config files that can be managed from
# the Admin Console instead of being handed to the dev agent in chat. Add
# new entries here whenever a future integration needs an uploaded file
# (e.g. an iOS `GoogleService-Info.plist`).
INTEGRATION_FILES: dict[str, dict] = {
    "google_services_json": {
        "label": "google-services.json",
        "description": "Firebase config for Android push notifications (FCM). Re-upload here any time the Firebase project changes — no code changes needed.",
        "path": _FRONTEND_DIR / "google-services.json",
    },
}


async def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


AdminUser = Annotated[dict, Depends(require_admin)]


def admin_user_row(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "name": doc.get("name"),
        "email": doc.get("email"),
        "avatar_url": doc.get("avatar_url"),
        "country": doc.get("country"),
        "gender": doc.get("gender"),
        "native_language": doc.get("native_language"),
        "coins": doc.get("coins", 0),
        "is_vip": bool(doc.get("is_vip")),
        "vip_tier": doc.get("vip_tier"),
        "is_admin": bool(doc.get("is_admin")),
        "banned": bool(doc.get("banned")),
        "restricted": bool(doc.get("restricted")),
        "is_online": manager.is_online(doc["_id"]),
        "created_at": doc.get("created_at"),
    }


@router.get("/stats")
async def stats(admin: AdminUser):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_users = await users_col.count_documents({})
    vip_users = await users_col.count_documents({"is_vip": True})
    banned = await users_col.count_documents({"banned": True})
    new_today = await users_col.count_documents({"created_at": {"$gte": today}})
    total_moments = await moments_col.count_documents({})
    total_messages = await messages_col.count_documents({})
    total_convs = await conversations_col.count_documents({})
    live_rooms = await rooms_col.count_documents({"is_live": True})
    coins_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$coins"}}}]
    coins_agg = await users_col.aggregate(coins_pipeline).to_list(1)
    return {
        "total_users": total_users,
        "vip_users": vip_users,
        "banned_users": banned,
        "new_users_today": new_today,
        "online_now": len(manager.online_user_ids()),
        "total_moments": total_moments,
        "total_messages": total_messages,
        "total_conversations": total_convs,
        "live_rooms": live_rooms,
        "coins_in_circulation": coins_agg[0]["total"] if coins_agg else 0,
    }


@router.get("/users")
async def list_users(admin: AdminUser, search: str | None = None):
    query: dict = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]
    docs = (
        await users_col.find(query, {"password_hash": 0})
        .sort("created_at", -1)
        .to_list(300)
    )
    return [admin_user_row(d) for d in docs]


@router.post("/users/{user_id}/ban")
async def toggle_ban(user_id: str, admin: AdminUser):
    doc = await users_col.find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    if doc.get("is_admin"):
        raise HTTPException(status_code=400, detail="Cannot ban an admin")
    banned = not doc.get("banned", False)
    await users_col.update_one({"_id": user_id}, {"$set": {"banned": banned}})
    return {"banned": banned}


@router.post("/users/{user_id}/restrict")
async def toggle_restrict(user_id: str, admin: AdminUser):
    doc = await users_col.find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    restricted = not doc.get("restricted", False)
    await users_col.update_one({"_id": user_id}, {"$set": {"restricted": restricted}})
    return {"restricted": restricted}


class CoinsUpdate(BaseModel):
    coins: int


@router.put("/users/{user_id}/coins")
async def set_coins(user_id: str, body: CoinsUpdate, admin: AdminUser):
    if body.coins < 0:
        raise HTTPException(status_code=400, detail="Coins must be >= 0")
    res = await users_col.update_one({"_id": user_id}, {"$set": {"coins": body.coins}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"coins": body.coins}


class VipUpdate(BaseModel):
    is_vip: bool
    tier: str | None = None  # weekly | monthly | lifetime


@router.put("/users/{user_id}/vip")
async def set_vip(user_id: str, body: VipUpdate, admin: AdminUser):
    updates: dict = {"is_vip": body.is_vip}
    if body.is_vip:
        updates["vip_tier"] = body.tier or "lifetime"
        updates["vip_expires_at"] = None
    else:
        updates["vip_tier"] = None
        updates["vip_expires_at"] = None
    res = await users_col.update_one({"_id": user_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"is_vip": body.is_vip, "vip_tier": updates["vip_tier"]}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: AdminUser):
    doc = await users_col.find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    if doc.get("is_admin"):
        raise HTTPException(status_code=400, detail="Cannot delete an admin")
    await users_col.delete_one({"_id": user_id})
    await moments_col.delete_many({"user_id": user_id})
    return {"ok": True}


@router.get("/moments")
async def list_all_moments(admin: AdminUser):
    docs = (
        await moments_col.find(
            {},
            {"user_id": 1, "text": 1, "image_id": 1, "likes": 1, "comment_count": 1, "created_at": 1},
        )
        .sort("created_at", -1)
        .to_list(100)
    )
    author_ids = list({d["user_id"] for d in docs})
    authors = (
        await users_col.find(
            {"_id": {"$in": author_ids}}, {"name": 1, "email": 1}
        ).to_list(len(author_ids))
        if author_ids
        else []
    )
    author_map = {u["_id"]: u for u in authors}
    out = []
    for d in docs:
        author = author_map.get(d["user_id"])
        out.append(
            {
                "id": d["_id"],
                "text": d.get("text"),
                "author_name": author.get("name") if author else "Unknown",
                "author_email": author.get("email") if author else None,
                "like_count": len(d.get("likes", [])),
                "comment_count": d.get("comment_count", 0),
                "has_image": bool(d.get("image_id")),
                "created_at": d.get("created_at"),
            }
        )
    return out


@router.delete("/moments/{moment_id}")
async def delete_moment(moment_id: str, admin: AdminUser):
    res = await moments_col.delete_one({"_id": moment_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Moment not found")
    return {"ok": True}


@router.get("/market")
async def market_items(admin: AdminUser):
    overrides = {d["_id"]: d async for d in market_config_col.find({})}
    items = []
    for item in CATALOG:
        o = overrides.get(item["id"], {})
        items.append(
            {
                **{k: v for k, v in item.items()},
                "price": o.get("price", item["price"]),
                "default_price": item["price"],
                "disabled": bool(o.get("disabled", False)),
            }
        )
    return items


class MarketItemUpdate(BaseModel):
    price: int | None = None
    disabled: bool | None = None


@router.put("/market/{item_id}")
async def update_market_item(item_id: str, body: MarketItemUpdate, admin: AdminUser):
    if item_id not in {i["id"] for i in CATALOG}:
        raise HTTPException(status_code=404, detail="Item not found")
    updates: dict = {}
    if body.price is not None:
        if body.price < 0:
            raise HTTPException(status_code=400, detail="Price must be >= 0")
        updates["price"] = body.price
    if body.disabled is not None:
        updates["disabled"] = body.disabled
    if updates:
        await market_config_col.update_one({"_id": item_id}, {"$set": updates}, upsert=True)
    return {"ok": True, **updates}


@router.get("/config")
async def read_config(admin: AdminUser):
    return await get_app_config()


class ConfigUpdate(BaseModel):
    free_translations_per_day: int | None = None
    free_rooms_per_day: int | None = None
    free_new_chats_per_day: int | None = None
    vip_new_chats_per_day: int | None = None
    app_name: str | None = None


@router.put("/config")
async def update_config(body: ConfigUpdate, admin: AdminUser):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    unknown = set(updates) - set(DEFAULTS)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown keys: {unknown}")
    if updates:
        await config_col.update_one({"_id": "app"}, {"$set": updates}, upsert=True)
    return await get_app_config()


def _integration_file_status(file_id: str) -> dict:
    meta = INTEGRATION_FILES[file_id]
    path: Path = meta["path"]
    exists = path.exists()
    return {
        "id": file_id,
        "label": meta["label"],
        "description": meta["description"],
        "exists": exists,
        "updated_at": (
            datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            if exists
            else None
        ),
    }


@router.get("/integration-files")
async def list_integration_files(admin: AdminUser):
    """Build-time integration config files (e.g. Firebase google-services.json)
    that admins can upload/replace without a code change."""
    return [_integration_file_status(fid) for fid in INTEGRATION_FILES]


class IntegrationFileUpload(BaseModel):
    content_base64: str


@router.post("/integration-files/{file_id}")
async def upload_integration_file(
    file_id: str, body: IntegrationFileUpload, admin: AdminUser
):
    if file_id not in INTEGRATION_FILES:
        raise HTTPException(status_code=404, detail="Unknown integration file")
    try:
        raw = base64.b64decode(body.content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file data")
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")
    path: Path = INTEGRATION_FILES[file_id]["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return _integration_file_status(file_id)


@router.delete("/integration-files/{file_id}")
async def remove_integration_file(file_id: str, admin: AdminUser):
    if file_id not in INTEGRATION_FILES:
        raise HTTPException(status_code=404, detail="Unknown integration file")
    path: Path = INTEGRATION_FILES[file_id]["path"]
    if path.exists():
        path.unlink()
    return _integration_file_status(file_id)
