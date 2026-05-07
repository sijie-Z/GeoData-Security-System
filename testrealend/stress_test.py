#!/usr/bin/env python3
"""
Stress testing script for Flask backend at http://127.0.0.1:5003
Uses ThreadPoolExecutor for concurrent requests.
"""

import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import statistics

BASE_URL = "http://127.0.0.1:5003"

class StressTestResult:
    def __init__(self):
        self.total_requests = 0
        self.successful = 0
        self.failed = 0
        self.response_times = []
        self.errors = []

def stress_test_get(endpoint_path, concurrent_users, requests_per_user, params=None, token=None):
    """Test a GET endpoint with concurrent users."""
    result = StressTestResult()
    result.total_requests = concurrent_users * requests_per_user
    url = f"{BASE_URL}{endpoint_path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    def make_request(thread_id, req_num):
        try:
            start = time.time()
            response = requests.get(url, params=params, headers=headers, timeout=30)
            elapsed = (time.time() - start) * 1000  # Convert to ms

            return {
                "status": response.status_code,
                "response_time": elapsed,
                "success": 200 <= response.status_code < 300,
                "text": response.text[:500] if response.status_code >= 400 else None,
                "error": None
            }
        except Exception as e:
            elapsed = (time.time() - start) * 1000 if 'start' in dir() else 0
            return {
                "status": 0,
                "response_time": elapsed,
                "success": False,
                "text": None,
                "error": str(e)
            }

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = []
        for thread_id in range(concurrent_users):
            for req_num in range(requests_per_user):
                futures.append(executor.submit(make_request, thread_id, req_num))

        for future in as_completed(futures):
            res = future.result()
            result.response_times.append(res["response_time"])
            if res["success"]:
                result.successful += 1
            else:
                result.failed += 1
                if res["text"]:
                    result.errors.append(f"Status {res['status']}: {res['text'][:200]}")
                elif res["error"]:
                    result.errors.append(f"Error: {res['error']}")

    return result

def stress_test_post(endpoint_path, concurrent_users, requests_per_user, json_data):
    """Test a POST endpoint with concurrent users."""
    result = StressTestResult()
    result.total_requests = concurrent_users * requests_per_user
    url = f"{BASE_URL}{endpoint_path}"

    def make_request(thread_id, req_num):
        try:
            start = time.time()
            response = requests.post(url, json=json_data, timeout=30)
            elapsed = (time.time() - start) * 1000

            return {
                "status": response.status_code,
                "response_time": elapsed,
                "success": 200 <= response.status_code < 300,
                "text": response.text[:500] if response.status_code >= 400 else None,
                "error": None
            }
        except Exception as e:
            return {
                "status": 0,
                "response_time": 0,
                "success": False,
                "text": None,
                "error": str(e)
            }

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = []
        for thread_id in range(concurrent_users):
            for req_num in range(requests_per_user):
                futures.append(executor.submit(make_request, thread_id, req_num))

        for future in as_completed(futures):
            res = future.result()
            result.response_times.append(res["response_time"])
            if res["success"]:
                result.successful += 1
            else:
                result.failed += 1
                if res["text"]:
                    result.errors.append(f"Status {res['status']}: {res['text'][:200]}")
                elif res["error"]:
                    result.errors.append(f"Error: {res['error']}")

    return result

def print_result(endpoint_name, result):
    """Print stress test results for an endpoint."""
    print(f"\n{'='*60}")
    print(f"ENDPOINT: {endpoint_name}")
    print(f"{'='*60}")
    print(f"Total requests sent:    {result.total_requests}")
    print(f"Successful (2xx):        {result.successful}")
    print(f"Failed (4xx/5xx):       {result.failed}")

    if result.response_times:
        avg_time = statistics.mean(result.response_times)
        min_time = min(result.response_times)
        max_time = max(result.response_times)
        print(f"Average response time:  {avg_time:.2f} ms")
        print(f"Min response time:      {min_time:.2f} ms")
        print(f"Max response time:      {max_time:.2f} ms")

    if result.errors:
        print(f"\nERRORS ENCOUNTERED ({len(set(result.errors))} unique):")
        unique_errors = list(set(result.errors))[:5]
        for i, err in enumerate(unique_errors, 1):
            print(f"  {i}. {err}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more errors")

def main():
    print("Starting Stress Test for Flask Backend at http://127.0.0.1:5003")
    print("="*60)

    # Get auth token first
    print("Getting auth token...")
    login_data = {"username": "admin", "password": "admin123", "role": "admin"}
    resp = requests.post(f"{BASE_URL}/api/login", json=login_data, timeout=10)
    token = resp.json()["access_token"]
    print(f"Token obtained: ...{token[-20:]}")

    # Test 1: GET /api/vector_data_viewing
    result1 = stress_test_get(
        "/api/vector_data_viewing",
        concurrent_users=20, requests_per_user=10,
        params={"page": 1, "pageSize": 10}
    )
    print_result("GET /api/vector_data_viewing (public, 200 req)", result1)

    # Test 2: GET /api/raster_data_viewing
    result2 = stress_test_get(
        "/api/raster_data_viewing",
        concurrent_users=20, requests_per_user=10,
        params={"page": 1, "pageSize": 10}
    )
    print_result("GET /api/raster_data_viewing (public, 200 req)", result2)

    # Test 3: GET /api/announcements
    result3 = stress_test_get(
        "/api/announcements",
        concurrent_users=20, requests_per_user=10,
        params={"page": 1, "pageSize": 5}
    )
    print_result("GET /api/announcements (public, 200 req)", result3)

    # Test 4: GET /api/protected (auth)
    result4 = stress_test_get(
        "/api/protected",
        concurrent_users=20, requests_per_user=10,
        token=token
    )
    print_result("GET /api/protected (auth, 200 req)", result4)

    # Test 5: GET /api/admin/dashboard (auth)
    result5 = stress_test_get(
        "/api/admin/dashboard",
        concurrent_users=20, requests_per_user=5,
        token=token
    )
    print_result("GET /api/admin/dashboard (auth, 100 req)", result5)

    # Test 6: GET /api/adm1_get_applications (auth)
    result6 = stress_test_get(
        "/api/adm1_get_applications",
        concurrent_users=20, requests_per_user=5,
        token=token
    )
    print_result("GET /api/adm1_get_applications (auth, 100 req)", result6)

    # Test 7: POST /api/login
    login_payload = {"username": "admin", "password": "admin123", "role": "admin"}
    result7 = stress_test_post(
        "/api/login",
        concurrent_users=5, requests_per_user=6,
        json_data=login_payload
    )
    print_result("POST /api/login (rate-limited, 30 req)", result7)

    # Test 8: GET /api/adm1_get_applications_generate_watermark (auth)
    result8 = stress_test_get(
        "/api/adm1_get_applications_generate_watermark",
        concurrent_users=10, requests_per_user=5,
        token=token
    )
    print_result("GET /api/adm1 watermark list (auth, 50 req)", result8)

    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    all_results = [
        ("GET /api/vector_data_viewing", result1),
        ("GET /api/raster_data_viewing", result2),
        ("GET /api/announcements", result3),
        ("GET /api/protected", result4),
        ("GET /api/admin/dashboard", result5),
        ("GET /api/adm1_get_applications", result6),
        ("POST /api/login", result7),
        ("GET /api/adm1 watermark list", result8),
    ]

    total_2xx = 0
    total_5xx = 0
    for name, res in all_results:
        success_rate = (res.successful / res.total_requests * 100) if res.total_requests > 0 else 0
        avg_time = statistics.mean(res.response_times) if res.response_times else 0
        err_5xx = sum(1 for t in res.errors if '500' in t)
        total_2xx += res.successful
        total_5xx += err_5xx
        print(f"  {name}:")
        print(f"    2xx={res.successful}/{res.total_requests} ({success_rate:.1f}%) | "
              f"AvgRT={avg_time:.1f}ms | 5xx={err_5xx}")

    print(f"\n  TOTAL 2xx: {total_2xx} | TOTAL 5xx: {total_5xx}")
    print(f"  SYSTEM STATUS: {'STABLE' if total_5xx == 0 else 'HAS 5xx ERRORS'}")
    print("="*60)

if __name__ == "__main__":
    main()