"""Iteration 7 backend tests: translation limits, visitors VIP lock, room caps,
new-chat caps, animated frames, block/hide/mute/clear, admin dashboard."""
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
if not BASE_URL:
    # fallback: read frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip()
                break
BASE_URL = (BASE_URL or "").rstrip("/")
API = f"{BASE_URL}/api"

DEMO_PW = "Demo1234!"


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def login(email: str, password: str = DEMO_PW) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=10)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def signup(email: str, name: str, password: str = DEMO_PW, **extra) -> tuple[str, str]:
    payload = {"email": email, "password": password, "name": name, **extra}
    r = requests.post(f"{API}/auth/register", json=payload, timeout=10)
    assert r.status_code in (200, 201), f"Signup failed: {r.status_code} {r.text}"
    data = r.json()
    return data["token"], data["user"]["id"]


# ---------- Health / basics ----------
def test_health():
    r = requests.get(f"{API}/", timeout=10)
    assert r.status_code == 200


# ---------- Admin ----------
@pytest.fixture(scope="module")
def admin_token():
    return login("admin@lingua.app", "Admin1234!")


def test_admin_stats(admin_token):
    r = requests.get(f"{API}/admin/stats", headers=auth_headers(admin_token), timeout=10)
    assert r.status_code == 200
    body = r.json()
    for k in ("total_users", "vip_users", "banned_users", "total_moments", "coins_in_circulation"):
        assert k in body


def test_admin_users_search(admin_token):
    r = requests.get(f"{API}/admin/users?search=demo", headers=auth_headers(admin_token), timeout=10)
    assert r.status_code == 200
    users = r.json()
    assert isinstance(users, list)
    assert any(u["email"] == "demo@demo.com" for u in users)


def test_admin_non_admin_forbidden():
    t = login("mei@demo.com")
    r = requests.get(f"{API}/admin/stats", headers=auth_headers(t), timeout=10)
    assert r.status_code == 403


def test_admin_get_config(admin_token):
    r = requests.get(f"{API}/admin/config", headers=auth_headers(admin_token), timeout=10)
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["free_translations_per_day"] >= 1


def test_admin_market_list(admin_token):
    r = requests.get(f"{API}/admin/market", headers=auth_headers(admin_token), timeout=10)
    assert r.status_code == 200
    items = r.json()
    ids = {i["id"] for i in items}
    assert "frame_rainbow" in ids and "frame_neon" in ids


# ---------- Ban / Restrict test: fresh user ----------
@pytest.fixture(scope="module")
def fresh_test_user():
    """Create a throwaway user for ban/restrict tests."""
    email = f"test_i7_{uuid.uuid4().hex[:8]}@demo.com"
    token, uid = signup(email, "TEST Iter7 User")
    yield {"email": email, "token": token, "id": uid}
    # cleanup: try to delete via admin
    try:
        admin_t = login("admin@lingua.app", "Admin1234!")
        requests.delete(f"{API}/admin/users/{uid}", headers=auth_headers(admin_t), timeout=10)
    except Exception:
        pass


def test_admin_ban_and_login_blocked(admin_token, fresh_test_user):
    uid = fresh_test_user["id"]
    r = requests.post(f"{API}/admin/users/{uid}/ban", headers=auth_headers(admin_token), timeout=10)
    assert r.status_code == 200
    assert r.json().get("banned") is True
    # Banned user login should fail
    r2 = requests.post(
        f"{API}/auth/login",
        json={"email": fresh_test_user["email"], "password": DEMO_PW},
        timeout=10,
    )
    assert r2.status_code == 403, f"Banned user login must return 403, got {r2.status_code} {r2.text}"
    # unban to allow next tests
    requests.post(f"{API}/admin/users/{uid}/ban", headers=auth_headers(admin_token), timeout=10)


def test_admin_restrict_and_moment_blocked(admin_token, fresh_test_user):
    uid = fresh_test_user["id"]
    # login fresh (unbanned)
    tok = login(fresh_test_user["email"])
    # restrict
    r = requests.post(f"{API}/admin/users/{uid}/restrict", headers=auth_headers(admin_token), timeout=10)
    assert r.status_code == 200 and r.json().get("restricted") is True
    # posting moment must fail
    r2 = requests.post(f"{API}/moments", headers=auth_headers(tok), json={"text": "TEST_restricted_post"}, timeout=10)
    assert r2.status_code == 403, f"Restricted post must return 403, got {r2.status_code}"
    # untoggle
    requests.post(f"{API}/admin/users/{uid}/restrict", headers=auth_headers(admin_token), timeout=10)


def test_admin_set_coins(admin_token, fresh_test_user):
    uid = fresh_test_user["id"]
    r = requests.put(
        f"{API}/admin/users/{uid}/coins",
        headers=auth_headers(admin_token),
        json={"coins": 777},
        timeout=10,
    )
    assert r.status_code == 200 and r.json()["coins"] == 777


def test_admin_grant_and_revoke_vip(admin_token, fresh_test_user):
    uid = fresh_test_user["id"]
    r = requests.put(
        f"{API}/admin/users/{uid}/vip",
        headers=auth_headers(admin_token),
        json={"is_vip": True, "tier": "lifetime"},
        timeout=10,
    )
    assert r.status_code == 200 and r.json()["is_vip"] is True
    r2 = requests.put(
        f"{API}/admin/users/{uid}/vip",
        headers=auth_headers(admin_token),
        json={"is_vip": False},
        timeout=10,
    )
    assert r2.status_code == 200 and r2.json()["is_vip"] is False


# ---------- Market catalog: animated frames ----------
def test_market_catalog_has_animated_frames():
    tok = login("demo@demo.com")
    r = requests.get(f"{API}/market", headers=auth_headers(tok), timeout=10)
    assert r.status_code == 200, f"GET /market failed: {r.status_code} {r.text}"
    items = r.json()["items"]
    rainbow = next((i for i in items if i["id"] == "frame_rainbow"), None)
    neon = next((i for i in items if i["id"] == "frame_neon"), None)
    assert rainbow and rainbow.get("animated") is True and rainbow.get("colors")
    assert neon and neon.get("animated") is True and neon.get("colors")


def test_admin_disable_item_hides_it(admin_token):
    # Disable badge_heart, verify hidden from market, then re-enable
    r = requests.put(
        f"{API}/admin/market/badge_heart",
        headers=auth_headers(admin_token),
        json={"disabled": True},
        timeout=10,
    )
    assert r.status_code == 200
    try:
        tok = login("demo@demo.com")
        m = requests.get(f"{API}/market", headers=auth_headers(tok), timeout=10).json()
        ids = {i["id"] for i in m["items"]}
        assert "badge_heart" not in ids, "Disabled item should be hidden from market"
    finally:
        requests.put(
            f"{API}/admin/market/badge_heart",
            headers=auth_headers(admin_token),
            json={"disabled": False},
            timeout=10,
        )


# ---------- Visitors VIP lock ----------
def test_visitors_free_user_locked():
    tok = login("mei@demo.com")
    # visit demo profile so there's a visit generated
    demo_tok = login("demo@demo.com")
    me = requests.get(f"{API}/auth/me", headers=auth_headers(demo_tok), timeout=10).json()
    # mei visits demo
    requests.get(f"{API}/users/{me['id']}", headers=auth_headers(tok), timeout=10)
    # demo checks visitors (demo is VIP weekly)
    r = requests.get(f"{API}/users/me/visitors", headers=auth_headers(demo_tok), timeout=10)
    assert r.status_code == 200
    data = r.json()
    # demo is VIP -> should see visitors list
    assert data.get("vip_required") in (False, None)
    # Now free user perspective (mei): use a fresh non-VIP user
    email = f"free_visit_{uuid.uuid4().hex[:8]}@demo.com"
    ftok, _ = signup(email, "TEST Free Visit")
    fdata = requests.get(f"{API}/users/me/visitors", headers=auth_headers(ftok), timeout=10).json()
    assert fdata.get("vip_required") is True
    assert fdata.get("visitors") == []


# ---------- Translation limits ----------
def test_translate_free_user_limit_and_vip_unlimited():
    # Fresh free user
    email = f"tr_free_{uuid.uuid4().hex[:8]}@demo.com"
    tok, _ = signup(email, "TEST Translate Free")
    # 3 free translations, then 429
    limit = 3
    for i in range(limit):
        r = requests.post(
            f"{API}/ai/translate",
            headers=auth_headers(tok),
            json={"text": "Hello world", "target_language": "es"},
            timeout=30,
        )
        assert r.status_code == 200, f"Attempt {i}: {r.status_code} {r.text}"
        body = r.json()
        assert "translated" in body
        assert body["remaining"] == limit - i - 1
    # 4th should be 429
    r4 = requests.post(
        f"{API}/ai/translate",
        headers=auth_headers(tok),
        json={"text": "Hello world", "target_language": "es"},
        timeout=30,
    )
    assert r4.status_code == 429, f"Expected 429, got {r4.status_code}"

    # VIP unlimited (demo is VIP weekly)
    vip_tok = login("demo@demo.com")
    rv = requests.post(
        f"{API}/ai/translate",
        headers=auth_headers(vip_tok),
        json={"text": "Bonjour", "target_language": "en"},
        timeout=30,
    )
    assert rv.status_code == 200
    assert rv.json().get("remaining") is None


# ---------- Room creation caps (free = 1/day) ----------
def test_free_user_room_cap():
    email = f"room_free_{uuid.uuid4().hex[:8]}@demo.com"
    tok, _ = signup(email, "TEST Room Free")
    r1 = requests.post(
        f"{API}/rooms",
        headers=auth_headers(tok),
        json={"title": "TEST Room 1", "language": "en"},
        timeout=10,
    )
    assert r1.status_code == 201, f"First room create failed: {r1.status_code} {r1.text}"
    r2 = requests.post(
        f"{API}/rooms",
        headers=auth_headers(tok),
        json={"title": "TEST Room 2", "language": "en"},
        timeout=10,
    )
    assert r2.status_code == 403


# ---------- Hide moments ----------
def test_hide_moments_toggle_filters_feed():
    a_tok = login("mei@demo.com")
    b_tok = login("diego@demo.com")
    b_me = requests.get(f"{API}/auth/me", headers=auth_headers(b_tok), timeout=10).json()
    # diego posts a moment (may be restricted from earlier tests; unrestrict via admin if needed)
    m = requests.post(f"{API}/moments", headers=auth_headers(b_tok), json={"text": f"TEST_hide_{uuid.uuid4().hex[:6]}"}, timeout=10)
    assert m.status_code == 201, f"Post moment failed: {m.text}"
    mid = m.json()["id"]
    # mei sees the moment
    feed = requests.get(f"{API}/moments", headers=auth_headers(a_tok), timeout=10).json()
    assert any(x["id"] == mid for x in feed)
    # mei hides diego
    h = requests.post(f"{API}/users/{b_me['id']}/hide-moments", headers=auth_headers(a_tok), timeout=10)
    assert h.status_code == 200 and h.json()["hidden"] is True
    feed2 = requests.get(f"{API}/moments", headers=auth_headers(a_tok), timeout=10).json()
    assert not any(x["id"] == mid for x in feed2)
    # unhide (toggle back)
    requests.post(f"{API}/users/{b_me['id']}/hide-moments", headers=auth_headers(a_tok), timeout=10)
    # cleanup: delete moment via admin
    admin_t = login("admin@lingua.app", "Admin1234!")
    requests.delete(f"{API}/admin/moments/{mid}", headers=auth_headers(admin_t), timeout=10)


# ---------- Block user prevents messaging ----------
def test_block_user_prevents_messaging():
    a_email = f"blk_a_{uuid.uuid4().hex[:6]}@demo.com"
    b_email = f"blk_b_{uuid.uuid4().hex[:6]}@demo.com"
    a_tok, a_id = signup(a_email, "TEST Block A")
    b_tok, b_id = signup(b_email, "TEST Block B")
    # A creates conversation with B
    conv = requests.post(f"{API}/chats", headers=auth_headers(a_tok), json={"partner_id": b_id}, timeout=10)
    assert conv.status_code == 200, conv.text
    conv_id = conv.json()["id"]
    # A blocks B
    r = requests.post(f"{API}/users/{b_id}/block", headers=auth_headers(a_tok), timeout=10)
    assert r.status_code == 200 and r.json()["blocked"] is True
    # B tries to message A -> should be 403 (partner blocked me)
    m = requests.post(
        f"{API}/chats/{conv_id}/messages",
        headers=auth_headers(b_tok),
        json={"text": "TEST block msg"},
        timeout=10,
    )
    assert m.status_code == 403


# ---------- Chat mute + clear history endpoints (from spec) ----------
def test_chat_mute_endpoint_exists():
    """Spec calls for POST /api/chats/{id}/mute -- verify it exists."""
    a_email = f"mute_a_{uuid.uuid4().hex[:6]}@demo.com"
    b_email = f"mute_b_{uuid.uuid4().hex[:6]}@demo.com"
    a_tok, _ = signup(a_email, "TEST Mute A")
    _, b_id = signup(b_email, "TEST Mute B")
    conv = requests.post(f"{API}/chats", headers=auth_headers(a_tok), json={"partner_id": b_id}, timeout=10)
    conv_id = conv.json()["id"]
    r = requests.post(f"{API}/chats/{conv_id}/mute", headers=auth_headers(a_tok), timeout=10)
    assert r.status_code in (200, 201), f"Mute endpoint missing/broken: {r.status_code} {r.text}"


def test_chat_clear_history_endpoint_exists():
    """Spec calls for DELETE /api/chats/{id}/messages -- verify it exists."""
    a_email = f"clr_a_{uuid.uuid4().hex[:6]}@demo.com"
    b_email = f"clr_b_{uuid.uuid4().hex[:6]}@demo.com"
    a_tok, _ = signup(a_email, "TEST Clear A")
    _, b_id = signup(b_email, "TEST Clear B")
    conv = requests.post(f"{API}/chats", headers=auth_headers(a_tok), json={"partner_id": b_id}, timeout=10)
    conv_id = conv.json()["id"]
    requests.post(f"{API}/chats/{conv_id}/messages", headers=auth_headers(a_tok), json={"text": "hi"}, timeout=10)
    r = requests.delete(f"{API}/chats/{conv_id}/messages", headers=auth_headers(a_tok), timeout=10)
    assert r.status_code in (200, 204), f"Clear-history endpoint missing/broken: {r.status_code} {r.text}"
    msgs = requests.get(f"{API}/chats/{conv_id}/messages", headers=auth_headers(a_tok), timeout=10).json()
    assert msgs == [] or len(msgs) == 0


# ---------- Regression: normal login, chats, moments feed, rooms ----------
def test_regression_login_and_feeds():
    tok = login("demo@demo.com")
    for path in ("/chats", "/moments", "/rooms"):
        r = requests.get(f"{API}{path}", headers=auth_headers(tok), timeout=10)
        assert r.status_code == 200, f"{path} regression failed: {r.status_code}"
