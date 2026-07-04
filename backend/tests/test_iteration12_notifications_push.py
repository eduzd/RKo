"""
Iteration 12 feature tests:
- Notification counts scoping (moments vs profile)
- Notification list only returns moments-type
- Mark-read by category
- Follow -> creates follow notification (only on follow, not unfollow), push failure graceful
- Visit (GET /users/{id}) -> creates visit notification only on first visit, push failure graceful
- Push register endpoint fails gracefully (placeholder key) without 500 crash blocking primary actions
- Admin integration-files upload/list/delete
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "").rstrip("/") or os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL", ""
).rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    return requests.Session()


def login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def mei_token(session):
    return login(session, "mei@demo.com", "Demo1234!")


@pytest.fixture(scope="module")
def diego_token(session):
    return login(session, "diego@demo.com", "Demo1234!")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestNotificationCounts:
    def test_counts_endpoint_shape(self, session, mei_token):
        r = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token))
        assert r.status_code == 200
        data = r.json()
        assert "moments_unread" in data
        assert "profile_unread" in data
        assert isinstance(data["moments_unread"], int)
        assert isinstance(data["profile_unread"], int)

    def test_list_notifications_only_moments_types(self, session, mei_token):
        r = session.get(f"{API}/notifications", headers=auth_headers(mei_token))
        assert r.status_code == 200
        data = r.json()
        assert "unread" in data
        assert "notifications" in data
        for n in data["notifications"]:
            assert n["type"] in ("like", "comment", "reply")

    def test_list_unread_matches_counts_moments_unread(self, session, mei_token):
        counts = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token)).json()
        listing = session.get(f"{API}/notifications", headers=auth_headers(mei_token)).json()
        assert counts["moments_unread"] == listing["unread"]


class TestMarkRead:
    def test_mark_read_moments_category(self, session, mei_token):
        r = session.post(
            f"{API}/notifications/read", params={"category": "moments"}, headers=auth_headers(mei_token)
        )
        assert r.status_code == 200
        counts = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token)).json()
        assert counts["moments_unread"] == 0

    def test_mark_read_profile_category(self, session, mei_token):
        r = session.post(
            f"{API}/notifications/read", params={"category": "profile"}, headers=auth_headers(mei_token)
        )
        assert r.status_code == 200
        counts = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token)).json()
        assert counts["profile_unread"] == 0

    def test_mark_read_no_category_marks_all(self, session, mei_token):
        r = session.post(f"{API}/notifications/read", headers=auth_headers(mei_token))
        assert r.status_code == 200
        counts = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token)).json()
        assert counts["moments_unread"] == 0
        assert counts["profile_unread"] == 0


class TestFollowNotification:
    def test_follow_creates_notification_and_succeeds_despite_push_failure(
        self, session, mei_token, diego_token
    ):
        # get diego's id
        me_diego = session.get(f"{API}/auth/me", headers=auth_headers(diego_token)).json()
        diego_id = me_diego["id"] if "id" in me_diego else me_diego.get("_id")

        # ensure unfollowed first (toggle twice if already following)
        r = session.get(f"{API}/users/{diego_id}", headers=auth_headers(mei_token))
        is_following = r.json().get("is_following")
        if is_following:
            session.post(f"{API}/users/{diego_id}/follow", headers=auth_headers(mei_token))

        before = session.get(f"{API}/notifications/counts", headers=auth_headers(diego_token)).json()

        r = session.post(f"{API}/users/{diego_id}/follow", headers=auth_headers(mei_token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["following"] is True

        after = session.get(f"{API}/notifications/counts", headers=auth_headers(diego_token)).json()
        assert after["profile_unread"] == before["profile_unread"] + 1

        # unfollow: must NOT create new notification
        before2 = session.get(f"{API}/notifications/counts", headers=auth_headers(diego_token)).json()
        r2 = session.post(f"{API}/users/{diego_id}/follow", headers=auth_headers(mei_token))
        assert r2.status_code == 200
        assert r2.json()["following"] is False
        after2 = session.get(f"{API}/notifications/counts", headers=auth_headers(diego_token)).json()
        assert after2["profile_unread"] == before2["profile_unread"]


class TestVisitNotification:
    def test_visit_creates_notification_only_once(self, session, mei_token, diego_token):
        me_mei = session.get(f"{API}/auth/me", headers=auth_headers(mei_token)).json()
        mei_id = me_mei["id"] if "id" in me_mei else me_mei.get("_id")

        before = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token)).json()

        r = session.get(f"{API}/users/{mei_id}", headers=auth_headers(diego_token))
        assert r.status_code == 200

        after = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token)).json()
        assert after["profile_unread"] == before["profile_unread"] + 1

        # visit again (repeat) - should NOT create a new notification
        r2 = session.get(f"{API}/users/{mei_id}", headers=auth_headers(diego_token))
        assert r2.status_code == 200
        after2 = session.get(f"{API}/notifications/counts", headers=auth_headers(mei_token)).json()
        assert after2["profile_unread"] == after["profile_unread"]


class TestPushRegisterGraceful:
    def test_register_push_fails_gracefully_with_placeholder_key(self, session, mei_token):
        r = session.post(
            f"{API}/register-push",
            json={"user_id": "spoofed", "platform": "android", "device_token": "TEST_faketoken"},
            headers=auth_headers(mei_token),
        )
        # Must not be a raw crash (200-599 fine but not connection error); expect 500/502 per contract
        assert r.status_code in (201, 500, 502), r.text

    def test_register_push_requires_auth(self, session):
        r = session.post(
            f"{API}/register-push",
            json={"user_id": "x", "platform": "android", "device_token": "y"},
        )
        assert r.status_code in (401, 403)


class TestAdminIntegrationFiles:
    @pytest.fixture(scope="class")
    def admin_token(self, session):
        return login(session, "admin@lingua.app", "Admin1234!")

    def test_list_integration_files(self, session, admin_token):
        r = session.get(f"{API}/admin/integration-files", headers=auth_headers(admin_token))
        assert r.status_code == 200
        files = r.json()
        assert isinstance(files, list)
        assert any(f["id"] == "google_services_json" for f in files)

    def test_upload_and_remove_integration_file(self, session, admin_token):
        import base64

        dummy = base64.b64encode(b'{"TEST": "dummy"}').decode()
        r = session.post(
            f"{API}/admin/integration-files/google_services_json",
            json={"content_base64": dummy},
            headers=auth_headers(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["exists"] is True
        assert r.json()["updated_at"] is not None

        # verify via GET list
        listing = session.get(f"{API}/admin/integration-files", headers=auth_headers(admin_token)).json()
        item = next(f for f in listing if f["id"] == "google_services_json")
        assert item["exists"] is True

        # delete
        r2 = session.delete(
            f"{API}/admin/integration-files/google_services_json", headers=auth_headers(admin_token)
        )
        assert r2.status_code == 200
        assert r2.json()["exists"] is False

        listing2 = session.get(f"{API}/admin/integration-files", headers=auth_headers(admin_token)).json()
        item2 = next(f for f in listing2 if f["id"] == "google_services_json")
        assert item2["exists"] is False

    def test_unknown_integration_file_404(self, session, admin_token):
        r = session.get(f"{API}/admin/integration-files", headers=auth_headers(admin_token))
        assert r.status_code == 200
        r2 = session.post(
            f"{API}/admin/integration-files/nonexistent_file",
            json={"content_base64": "AAAA"},
            headers=auth_headers(admin_token),
        )
        assert r2.status_code == 404

    def test_admin_other_tabs_regression(self, session, admin_token):
        for ep in ["/admin/stats", "/admin/users", "/admin/market", "/admin/moments", "/admin/config"]:
            r = session.get(f"{API}{ep}", headers=auth_headers(admin_token))
            assert r.status_code == 200, f"{ep} failed: {r.text}"
