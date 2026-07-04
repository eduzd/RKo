#!/usr/bin/env python3
"""
Backend API Test Suite for LinguaConnect
Tests newly added/modified endpoints for profile redesign
"""

import base64
import requests
import sys

# Base URL from frontend/.env EXPO_PUBLIC_BACKEND_URL
BASE_URL = "https://design-system-update-10.preview.emergentagent.com/api"

# Test credentials
TEST_EMAIL = "fahad@lingua.app"
TEST_PASSWORD = "Test1234!"
SECOND_USER_ID = "star-demo-id-207"

# Test results tracking
test_results = []


def log_test(name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")


def get_auth_token():
    """Login and get JWT token"""
    print("\n=== Authenticating ===")
    url = f"{BASE_URL}/auth/login"
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            if token:
                print(f"✅ Authentication successful")
                return token
            else:
                print(f"❌ No token in response: {data}")
                return None
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None


def test_extended_profile_update(token):
    """Test 1: Extended profile update - PUT /api/users/me"""
    print("\n=== Test 1: Extended Profile Update ===")
    
    url = f"{BASE_URL}/users/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test data with all new fields
    profile_data = {
        "mbti": "ENTP",
        "blood_type": "AB",
        "hometown": "Lahore",
        "occupation": "Engineer",
        "school": "MIT",
        "places_to_go": "Japan",
        "birthday": "1999-05-10",
        "gender": "male"
    }
    
    try:
        response = requests.put(url, json=profile_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify all fields are echoed back
            all_match = True
            mismatches = []
            
            for key, expected_value in profile_data.items():
                actual_value = data.get(key)
                if actual_value != expected_value:
                    all_match = False
                    mismatches.append(f"{key}: expected '{expected_value}', got '{actual_value}'")
            
            if all_match:
                log_test(
                    "PUT /api/users/me - Extended profile fields",
                    True,
                    "All fields (mbti, blood_type, hometown, occupation, school, places_to_go, birthday, gender) updated and echoed correctly"
                )
                return True
            else:
                log_test(
                    "PUT /api/users/me - Extended profile fields",
                    False,
                    f"Field mismatches: {', '.join(mismatches)}"
                )
                return False
        else:
            log_test(
                "PUT /api/users/me - Extended profile fields",
                False,
                f"HTTP {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        log_test("PUT /api/users/me - Extended profile fields", False, f"Exception: {e}")
        return False


def test_profile_persistence(token):
    """Test 1b: Verify profile fields persist - GET /api/auth/me"""
    print("\n=== Test 1b: Profile Persistence ===")
    
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    expected_values = {
        "mbti": "ENTP",
        "blood_type": "AB",
        "hometown": "Lahore",
        "occupation": "Engineer",
        "school": "MIT",
        "places_to_go": "Japan",
        "birthday": "1999-05-10",
        "gender": "male"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            all_match = True
            mismatches = []
            
            for key, expected_value in expected_values.items():
                actual_value = data.get(key)
                if actual_value != expected_value:
                    all_match = False
                    mismatches.append(f"{key}: expected '{expected_value}', got '{actual_value}'")
            
            if all_match:
                log_test(
                    "GET /api/auth/me - Profile persistence",
                    True,
                    "All extended profile fields persisted correctly"
                )
                return True
            else:
                log_test(
                    "GET /api/auth/me - Profile persistence",
                    False,
                    f"Field mismatches: {', '.join(mismatches)}"
                )
                return False
        else:
            log_test(
                "GET /api/auth/me - Profile persistence",
                False,
                f"HTTP {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        log_test("GET /api/auth/me - Profile persistence", False, f"Exception: {e}")
        return False


def test_my_moments_count_with_auth(token):
    """Test 2a: GET /api/moments/mine/count with auth"""
    print("\n=== Test 2a: My Moments Count (with auth) ===")
    
    url = f"{BASE_URL}/moments/mine/count"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "count" in data and isinstance(data["count"], int):
                log_test(
                    "GET /api/moments/mine/count (with auth)",
                    True,
                    f"Returned count: {data['count']}"
                )
                return True
            else:
                log_test(
                    "GET /api/moments/mine/count (with auth)",
                    False,
                    f"Invalid response format: {data}"
                )
                return False
        else:
            log_test(
                "GET /api/moments/mine/count (with auth)",
                False,
                f"HTTP {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        log_test("GET /api/moments/mine/count (with auth)", False, f"Exception: {e}")
        return False


def test_user_moments_count_with_auth(token):
    """Test 2b: GET /api/moments/user/{id}/count with auth"""
    print("\n=== Test 2b: User Moments Count (with auth) ===")
    
    url = f"{BASE_URL}/moments/user/{SECOND_USER_ID}/count"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "count" in data and isinstance(data["count"], int):
                log_test(
                    f"GET /api/moments/user/{SECOND_USER_ID}/count (with auth)",
                    True,
                    f"Returned count: {data['count']}"
                )
                return True
            else:
                log_test(
                    f"GET /api/moments/user/{SECOND_USER_ID}/count (with auth)",
                    False,
                    f"Invalid response format: {data}"
                )
                return False
        else:
            log_test(
                f"GET /api/moments/user/{SECOND_USER_ID}/count (with auth)",
                False,
                f"HTTP {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        log_test(f"GET /api/moments/user/{SECOND_USER_ID}/count (with auth)", False, f"Exception: {e}")
        return False


def test_my_moments_count_without_auth():
    """Test 2c: GET /api/moments/mine/count without auth (expect 401/403)"""
    print("\n=== Test 2c: My Moments Count (without auth) ===")
    
    url = f"{BASE_URL}/moments/mine/count"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code in [401, 403]:
            log_test(
                "GET /api/moments/mine/count (without auth)",
                True,
                f"Correctly rejected with HTTP {response.status_code}"
            )
            return True
        else:
            log_test(
                "GET /api/moments/mine/count (without auth)",
                False,
                f"Expected 401/403, got HTTP {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        log_test("GET /api/moments/mine/count (without auth)", False, f"Exception: {e}")
        return False


def test_cover_upload_valid(token):
    """Test 3a: POST /api/users/me/cover with valid base64 image"""
    print("\n=== Test 3a: Cover Upload (valid image) ===")
    
    url = f"{BASE_URL}/users/me/cover"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a tiny 1x1 PNG image (valid base64)
    # This is a minimal valid PNG file
    tiny_png = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    image_base64 = base64.b64encode(tiny_png).decode('utf-8')
    
    payload = {
        "image_base64": image_base64,
        "mime": "image/png"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            cover_url = data.get("cover_url")
            
            if cover_url and cover_url.startswith("/api/media/"):
                log_test(
                    "POST /api/users/me/cover (valid image)",
                    True,
                    f"Cover uploaded successfully, cover_url: {cover_url}"
                )
                return True
            else:
                log_test(
                    "POST /api/users/me/cover (valid image)",
                    False,
                    f"Invalid cover_url in response: {cover_url}"
                )
                return False
        else:
            log_test(
                "POST /api/users/me/cover (valid image)",
                False,
                f"HTTP {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        log_test("POST /api/users/me/cover (valid image)", False, f"Exception: {e}")
        return False


def test_cover_upload_invalid(token):
    """Test 3b: POST /api/users/me/cover with invalid base64 (expect 400)"""
    print("\n=== Test 3b: Cover Upload (invalid base64) ===")
    
    url = f"{BASE_URL}/users/me/cover"
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "image_base64": "!!!notbase64!!!",
        "mime": "image/png"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 400:
            log_test(
                "POST /api/users/me/cover (invalid base64)",
                True,
                f"Correctly rejected with HTTP 400"
            )
            return True
        else:
            log_test(
                "POST /api/users/me/cover (invalid base64)",
                False,
                f"Expected 400, got HTTP {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        log_test("POST /api/users/me/cover (invalid base64)", False, f"Exception: {e}")
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)
    
    print(f"\nTotal: {passed}/{total} tests passed\n")
    
    for result in test_results:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['name']}")
        if result["details"] and not result["passed"]:
            print(f"   {result['details']}")
    
    print("\n" + "="*60)
    
    return passed == total


def main():
    """Run all tests"""
    print("="*60)
    print("LinguaConnect Backend API Tests")
    print("Profile Redesign - New Endpoints")
    print("="*60)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("\n❌ CRITICAL: Authentication failed. Cannot proceed with tests.")
        sys.exit(1)
    
    # Run all tests
    test_extended_profile_update(token)
    test_profile_persistence(token)
    test_my_moments_count_with_auth(token)
    test_user_moments_count_with_auth(token)
    test_my_moments_count_without_auth()
    test_cover_upload_valid(token)
    test_cover_upload_invalid(token)
    
    # Print summary
    all_passed = print_summary()
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
