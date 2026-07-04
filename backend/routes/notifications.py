from fastapi import APIRouter

from auth_utils import CurrentUser
from db import notifications_col, users_col
from models import user_card

router = APIRouter(prefix="/notifications", tags=["notifications"])

# "Moments" activity = interactions on a user's own moments (feed screen).
# "Profile" activity = new followers / new profile visitors (Me tab dot).
MOMENTS_TYPES = ["like", "comment", "reply"]
PROFILE_TYPES = ["follow", "visit"]


@router.get("")
async def list_notifications(current_user: CurrentUser):
    """Moment-interaction activity feed (likes/comments/replies)."""
    uid = current_user["_id"]
    docs = (
        await notifications_col.find(
            {"user_id": uid, "type": {"$in": MOMENTS_TYPES}}
        )
        .sort("created_at", -1)
        .to_list(50)
    )
    actor_ids = list({d["actor_id"] for d in docs})
    actors = await users_col.find({"_id": {"$in": actor_ids}}).to_list(100)
    amap = {a["_id"]: a for a in actors}
    items = []
    for d in docs:
        actor = amap.get(d["actor_id"])
        items.append(
            {
                "id": d["_id"],
                "type": d["type"],
                "moment_id": d.get("moment_id"),
                "text": d.get("text"),
                "read": d.get("read", False),
                "created_at": d["created_at"],
                "actor": user_card(actor) if actor else None,
            }
        )
    unread = await notifications_col.count_documents(
        {"user_id": uid, "read": False, "type": {"$in": MOMENTS_TYPES}}
    )
    return {"unread": unread, "notifications": items}


@router.get("/counts")
async def notification_counts(current_user: CurrentUser):
    """Lightweight unread counters used to badge the bottom tab bar."""
    uid = current_user["_id"]
    moments_unread = await notifications_col.count_documents(
        {"user_id": uid, "read": False, "type": {"$in": MOMENTS_TYPES}}
    )
    profile_unread = await notifications_col.count_documents(
        {"user_id": uid, "read": False, "type": {"$in": PROFILE_TYPES}}
    )
    return {"moments_unread": moments_unread, "profile_unread": profile_unread}


@router.post("/read")
async def mark_all_read(current_user: CurrentUser, category: str | None = None):
    """Mark notifications read. `category` narrows to "moments" or "profile";
    omitted marks everything read (used by the legacy full-list screen)."""
    query: dict = {"user_id": current_user["_id"], "read": False}
    if category == "moments":
        query["type"] = {"$in": MOMENTS_TYPES}
    elif category == "profile":
        query["type"] = {"$in": PROFILE_TYPES}
    await notifications_col.update_many(query, {"$set": {"read": True}})
    return {"ok": True}
