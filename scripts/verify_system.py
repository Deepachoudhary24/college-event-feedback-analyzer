#!/usr/bin/env python3
"""
Automated System Verification Script for College Event Feedback Analyzer.
Tests backend authentication and all enterprise, text media, and IT PM endpoints.
"""

import json
import sys
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows consoles (avoid charmap/cp1252 errors)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

API_BASE = "http://localhost:8800"

def test_endpoints():
    print(f"Connecting to {API_BASE}...")
    try:
        # 1. Login as Admin
        login_url = f"{API_BASE}/api/auth/login"
        login_payload = json.dumps({"username": "admin", "password": "Admin@Event123"}).encode("utf-8")
        req = urllib.request.Request(
            login_url,
            data=login_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            login_data = json.loads(resp.read().decode("utf-8"))
            token = login_data.get("access_token")

        if not token:
            print("[FAIL] No access token received from login.")
            return False

        print("[OK] Authentication successful (Admin JWT token issued)")

        # 2. Test Endpoints
        headers = {"Authorization": f"Bearer {token}"}
        endpoints = [
            ("Text Media Past Analyses", "/api/analyses"),
            ("IT PM Project Governance", "/api/project"),
            ("IT PM Kanban Tasks", "/api/tasks"),
            ("IT PM Milestones", "/api/milestones"),
            ("IT PM Risk Register", "/api/risks"),
            ("IT PM Stakeholders Directory", "/api/stakeholders"),
            ("Enterprise Issue Tracking", "/api/issues"),
            ("Enterprise Issue Statistics", "/api/issues/stats"),
        ]

        for name, ep in endpoints:
            url = f"{API_BASE}{ep}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                count_str = f"{len(data)} records" if isinstance(data, list) else "Active/OK"
                print(f"[OK] Verified {name} ({ep}): {count_str}")

        print("\nAll 3 academic modules operational and verified successfully!")
        return True

    except urllib.error.URLError as e:
        print(f"[FAIL] Connection error: {e}. Ensure the backend server is running on port 8800.")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error during verification: {e}")
        return False

if __name__ == "__main__":
    success = test_endpoints()
    sys.exit(0 if success else 1)
