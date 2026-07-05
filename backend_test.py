#!/usr/bin/env python3
"""
Backend API Test Suite for LinguaConnect Voice Bio Feature
Tests POST /api/users/me/voice-bio and DELETE /api/users/me/voice-bio endpoints
"""

import base64
import requests
import sys
import time

# Backend URL from frontend/.env
BASE_URL = "https://edf855b1-a946-4795-a4f1-66392dbb697e.preview.emergentagent.com/api"

# Test credentials - using a fresh user to avoid destroying mei's voice bio
TEST_EMAIL = f"voicebio_test_{int(time.time())}@lingua.app"
TEST_PASSWORD = "Test1234!"
TEST_NAME = "Voice Bio Test User"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def log_test(test_name, passed, details=""):
    """Log test result with color coding"""
    status = f"{GREEN}✅ PASSED{RESET}" if passed else f"{RED}❌ FAILED{RESET}"
    print(f"\n{status} - {test_name}")
    if details:
        print(f"  {details}")
    return passed

def register_user():
    """Register a fresh test user"""
    print(f"\n{YELLOW}=== Registering Fresh Test User ==={RESET}")
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "name": TEST_NAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "native_language": "en",
            "learning_language": "ja"
        }
    )
    if response.status_code == 201:
        data = response.json()
        token = data.get("token")
        
        # Get user_id from /auth/me endpoint
        me_response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        user_id = None
        if me_response.status_code == 200:
            user_id = me_response.json().get("id")  # Changed from "_id" to "id"
        
        print(f"  ✓ Registered user: {TEST_EMAIL}")
        print(f"  ✓ User ID: {user_id}")
        return token, user_id
    else:
        print(f"  ✗ Registration failed: {response.status_code} - {response.text}")
        return None, None

def test_voice_bio_without_auth():
    """Test 1: POST /api/users/me/voice-bio without auth should return 401/403"""
    print(f"\n{YELLOW}=== Test 1: Voice Bio Upload Without Auth ==={RESET}")
    
    # Create minimal valid audio data
    audio_data = b"fake_audio_data_for_testing"
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    response = requests.post(
        f"{BASE_URL}/users/me/voice-bio",
        json={
            "audio_base64": audio_base64,
            "mime": "audio/webm",
            "duration_ms": 5000
        }
    )
    
    passed = response.status_code in [401, 403]
    return log_test(
        "Voice bio upload without auth returns 401/403",
        passed,
        f"Status: {response.status_code}"
    )

def test_voice_bio_valid_upload(token, user_id):
    """Test 2: POST /api/users/me/voice-bio with valid data"""
    print(f"\n{YELLOW}=== Test 2: Voice Bio Upload With Valid Data ==={RESET}")
    
    # Create valid audio data (simulating audio bytes)
    audio_data = b"RIFF" + b"\x00" * 100  # Minimal RIFF header + data
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    response = requests.post(
        f"{BASE_URL}/users/me/voice-bio",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "audio_base64": audio_base64,
            "mime": "audio/webm",
            "duration_ms": 5000
        }
    )
    
    if response.status_code != 200:
        return log_test(
            "Voice bio upload with valid data",
            False,
            f"Status: {response.status_code}, Response: {response.text}"
        )
    
    data = response.json()
    
    # Verify response contains voice_bio_id and voice_bio_duration_ms
    has_voice_bio_id = "voice_bio_id" in data and data["voice_bio_id"] is not None
    has_duration = "voice_bio_duration_ms" in data and data["voice_bio_duration_ms"] == 5000
    
    passed = has_voice_bio_id and has_duration
    
    if passed:
        voice_bio_id = data["voice_bio_id"]
        print(f"  ✓ voice_bio_id: {voice_bio_id}")
        print(f"  ✓ voice_bio_duration_ms: {data['voice_bio_duration_ms']}")
        return log_test(
            "Voice bio upload with valid data returns user with voice_bio_id and duration",
            True,
            f"voice_bio_id: {voice_bio_id}, duration: 5000ms"
        ), voice_bio_id
    else:
        return log_test(
            "Voice bio upload with valid data",
            False,
            f"Missing fields. Response: {data}"
        ), None

def test_voice_bio_invalid_base64(token):
    """Test 3: POST /api/users/me/voice-bio with invalid base64"""
    print(f"\n{YELLOW}=== Test 3: Voice Bio Upload With Invalid Base64 ==={RESET}")
    
    response = requests.post(
        f"{BASE_URL}/users/me/voice-bio",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "audio_base64": "!!!invalid_base64!!!",
            "mime": "audio/webm",
            "duration_ms": 5000
        }
    )
    
    passed = response.status_code == 400
    return log_test(
        "Voice bio upload with invalid base64 returns 400",
        passed,
        f"Status: {response.status_code}"
    )

def test_voice_bio_duration_capping(token):
    """Test 4: POST /api/users/me/voice-bio with duration > 60000 gets capped"""
    print(f"\n{YELLOW}=== Test 4: Voice Bio Duration Capping (>60000ms) ==={RESET}")
    
    audio_data = b"audio_data_for_long_duration_test"
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    response = requests.post(
        f"{BASE_URL}/users/me/voice-bio",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "audio_base64": audio_base64,
            "mime": "audio/webm",
            "duration_ms": 75000  # 75 seconds, should be capped to 60000
        }
    )
    
    if response.status_code != 200:
        return log_test(
            "Voice bio duration capping",
            False,
            f"Status: {response.status_code}, Response: {response.text}"
        )
    
    data = response.json()
    duration = data.get("voice_bio_duration_ms")
    
    passed = duration == 60000
    return log_test(
        "Voice bio duration > 60000ms gets capped to 60000",
        passed,
        f"Sent: 75000ms, Got: {duration}ms"
    ), data.get("voice_bio_id")

def test_audio_retrieval(voice_bio_id):
    """Test 5: GET /api/audio/{voice_bio_id} returns audio bytes"""
    print(f"\n{YELLOW}=== Test 5: Audio Retrieval ==={RESET}")
    
    if not voice_bio_id:
        return log_test(
            "Audio retrieval",
            False,
            "No voice_bio_id available from previous test"
        )
    
    response = requests.get(f"{BASE_URL}/audio/{voice_bio_id}")
    
    if response.status_code != 200:
        return log_test(
            "GET /api/audio/{voice_bio_id} returns audio",
            False,
            f"Status: {response.status_code}"
        )
    
    # Check that we got binary data back
    has_content = len(response.content) > 0
    has_mime = "audio" in response.headers.get("content-type", "").lower() or \
               "application/octet-stream" in response.headers.get("content-type", "").lower()
    
    passed = has_content
    return log_test(
        "GET /api/audio/{voice_bio_id} returns audio bytes",
        passed,
        f"Content-Type: {response.headers.get('content-type')}, Size: {len(response.content)} bytes"
    )

def test_user_profile_includes_voice_bio(token, user_id):
    """Test 6: GET /api/users/{user_id} includes voice_bio_id and duration"""
    print(f"\n{YELLOW}=== Test 6: User Profile Includes Voice Bio ==={RESET}")
    
    # Login as mei to view the test user's profile
    mei_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "mei@demo.com", "password": "Demo1234!"}
    )
    
    if mei_response.status_code != 200:
        return log_test(
            "User profile includes voice_bio_id",
            False,
            "Could not login as mei@demo.com to view profile"
        )
    
    mei_token = mei_response.json().get("token")
    
    response = requests.get(
        f"{BASE_URL}/users/{user_id}",
        headers={"Authorization": f"Bearer {mei_token}"}
    )
    
    if response.status_code != 200:
        return log_test(
            "GET /api/users/{user_id} includes voice_bio_id",
            False,
            f"Status: {response.status_code}"
        )
    
    data = response.json()
    has_voice_bio_id = "voice_bio_id" in data and data["voice_bio_id"] is not None
    has_duration = "voice_bio_duration_ms" in data
    
    passed = has_voice_bio_id and has_duration
    return log_test(
        "GET /api/users/{user_id} includes voice_bio_id and duration",
        passed,
        f"voice_bio_id present: {has_voice_bio_id}, duration present: {has_duration}"
    )

def test_delete_voice_bio(token):
    """Test 7: DELETE /api/users/me/voice-bio removes voice bio"""
    print(f"\n{YELLOW}=== Test 7: Delete Voice Bio ==={RESET}")
    
    response = requests.delete(
        f"{BASE_URL}/users/me/voice-bio",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        return log_test(
            "DELETE /api/users/me/voice-bio",
            False,
            f"Status: {response.status_code}, Response: {response.text}"
        )
    
    data = response.json()
    
    # Check that voice_bio_id is now null or absent
    voice_bio_id_removed = data.get("voice_bio_id") is None or "voice_bio_id" not in data
    
    passed = voice_bio_id_removed
    return log_test(
        "DELETE /api/users/me/voice-bio removes voice_bio_id",
        passed,
        f"voice_bio_id in response: {data.get('voice_bio_id')}"
    ), data.get("voice_bio_id")

def test_audio_deleted(old_voice_bio_id):
    """Test 8: GET /api/audio/{old_voice_bio_id} returns 404 after deletion"""
    print(f"\n{YELLOW}=== Test 8: Audio Document Deleted ==={RESET}")
    
    if not old_voice_bio_id:
        return log_test(
            "Audio document deleted",
            False,
            "No old voice_bio_id available"
        )
    
    response = requests.get(f"{BASE_URL}/audio/{old_voice_bio_id}")
    
    passed = response.status_code == 404
    return log_test(
        "GET /api/audio/{old_voice_bio_id} returns 404 after deletion",
        passed,
        f"Status: {response.status_code}"
    )

def test_smoke_update_user(token):
    """Test 9: Smoke test - PUT /api/users/me still works"""
    print(f"\n{YELLOW}=== Test 9: Smoke Test - PUT /api/users/me ==={RESET}")
    
    response = requests.put(
        f"{BASE_URL}/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"hometown": "TestTown"}
    )
    
    if response.status_code != 200:
        return log_test(
            "PUT /api/users/me {hometown: TestTown}",
            False,
            f"Status: {response.status_code}, Response: {response.text}"
        )
    
    data = response.json()
    passed = data.get("hometown") == "TestTown"
    
    return log_test(
        "PUT /api/users/me updates hometown",
        passed,
        f"hometown: {data.get('hometown')}"
    )

def test_smoke_auth_me(token):
    """Test 10: Smoke test - GET /api/auth/me includes hometown update"""
    print(f"\n{YELLOW}=== Test 10: Smoke Test - GET /api/auth/me ==={RESET}")
    
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        return log_test(
            "GET /api/auth/me",
            False,
            f"Status: {response.status_code}"
        )
    
    data = response.json()
    passed = data.get("hometown") == "TestTown"
    
    return log_test(
        "GET /api/auth/me includes hometown update",
        passed,
        f"hometown: {data.get('hometown')}"
    )

def test_smoke_checkin(token):
    """Test 11: Smoke test - POST /api/users/me/check-in returns valid shape"""
    print(f"\n{YELLOW}=== Test 11: Smoke Test - POST /api/users/me/check-in ==={RESET}")
    
    response = requests.post(
        f"{BASE_URL}/users/me/check-in",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        return log_test(
            "POST /api/users/me/check-in",
            False,
            f"Status: {response.status_code}, Response: {response.text}"
        )
    
    data = response.json()
    
    # Check for required fields
    has_already_checked_in = "already_checked_in" in data
    has_coins_awarded = "coins_awarded" in data
    has_streak_count = "streak_count" in data
    has_coins = "coins" in data
    
    passed = has_already_checked_in and has_coins_awarded and has_streak_count and has_coins
    
    return log_test(
        "POST /api/users/me/check-in returns valid shape",
        passed,
        f"Fields present: already_checked_in={has_already_checked_in}, coins_awarded={has_coins_awarded}, streak_count={has_streak_count}, coins={has_coins}"
    )

def main():
    """Run all voice bio tests"""
    print(f"\n{'='*70}")
    print(f"  LinguaConnect Voice Bio Backend API Tests")
    print(f"  Backend: {BASE_URL}")
    print(f"{'='*70}")
    
    results = []
    
    # Test 1: Without auth
    results.append(test_voice_bio_without_auth())
    
    # Register fresh user
    token, user_id = register_user()
    if not token:
        print(f"\n{RED}FATAL: Could not register test user. Aborting.{RESET}")
        sys.exit(1)
    
    # Test 2: Valid upload
    test2_result, voice_bio_id = test_voice_bio_valid_upload(token, user_id)
    results.append(test2_result)
    
    # Test 3: Invalid base64
    results.append(test_voice_bio_invalid_base64(token))
    
    # Test 4: Duration capping
    test4_result, capped_voice_bio_id = test_voice_bio_duration_capping(token)
    results.append(test4_result)
    
    # Use the capped voice bio ID for audio retrieval test
    if capped_voice_bio_id:
        voice_bio_id = capped_voice_bio_id
    
    # Test 5: Audio retrieval
    results.append(test_audio_retrieval(voice_bio_id))
    
    # Test 6: User profile includes voice bio
    results.append(test_user_profile_includes_voice_bio(token, user_id))
    
    # Test 7: Delete voice bio
    test7_result, old_voice_bio_id = test_delete_voice_bio(token)
    results.append(test7_result)
    
    # Store the voice_bio_id before deletion for test 8
    if old_voice_bio_id is None and voice_bio_id:
        old_voice_bio_id = voice_bio_id
    
    # Test 8: Audio deleted
    results.append(test_audio_deleted(old_voice_bio_id))
    
    # Test 9-11: Smoke tests
    results.append(test_smoke_update_user(token))
    results.append(test_smoke_auth_me(token))
    results.append(test_smoke_checkin(token))
    
    # Summary
    print(f"\n{'='*70}")
    print(f"  TEST SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Total Tests: {total}")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    print(f"  {RED}Failed: {total - passed}{RESET}")
    
    if passed == total:
        print(f"\n  {GREEN}✅ ALL TESTS PASSED{RESET}")
        sys.exit(0)
    else:
        print(f"\n  {RED}❌ SOME TESTS FAILED{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
