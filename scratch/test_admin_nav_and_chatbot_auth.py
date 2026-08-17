"""
Test suite to verify:
1. Admin Dashboard navbar logic (admin_nav.html rendered for admin users; nav.html rendered for non-admin users).
2. AI Chatbot authentication endpoint (Session Auth & SimpleJWT Bearer Auth support + 401 for unauthenticated).
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctor_appointment_system.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def run_tests():
    print("=== STARTING ADMIN NAVBAR & CHATBOT AUTHENTICATION VERIFICATION ===")

    # 1. Setup Test Users
    admin_user, _ = User.objects.get_or_create(
        username='test_admin_user',
        defaults={
            'email': 'admin_test@docmed.in',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    admin_user.set_password('AdminTest123!')
    admin_user.save()

    patient_user, _ = User.objects.get_or_create(
        username='test_patient_user',
        defaults={
            'email': 'patient_test@docmed.in',
            'role': 'patient',
            'is_staff': False,
            'is_superuser': False,
        }
    )
    patient_user.set_password('PatientTest123!')
    patient_user.save()

    client = Client()

    # ── Test 1: Public / Guest Navbar ──────────────────────────────────────────
    resp_guest = client.get('/')
    assert resp_guest.status_code == 200, f"Home page returned {resp_guest.status_code}"
    content_guest = resp_guest.content.decode('utf-8')
    assert "DocMed" in content_guest, "Guest navbar brand missing"
    assert "ADMIN PORTAL" not in content_guest, "Admin portal badge should NOT appear for guests"
    print("[OK] Test 1 Passed: Public/Guest Navbar rendered correctly (Admin Portal badge hidden).")

    # ── Test 2: Admin Dashboard Navbar ───────────────────────────────────────
    client.login(username='test_admin_user', password='AdminTest123!')
    resp_admin = client.get('/admin-dashboard/')
    assert resp_admin.status_code == 200, f"Admin Dashboard returned {resp_admin.status_code}"
    content_admin = resp_admin.content.decode('utf-8')
    assert "ADMIN PORTAL" in content_admin, "Admin Portal badge missing on Admin Dashboard"
    assert "Verification & Approvals" in content_admin, "Doctor Verification link missing in Admin Navbar"
    assert "Pending Registrations" in content_admin, "Pending Doctor Registrations link missing in Admin Navbar"
    assert "System Settings" in content_admin, "System Settings link missing in Admin Navbar"
    print("[OK] Test 2 Passed: Dedicated Admin Navbar rendered on Admin Dashboard with all modules.")

    # ── Test 3: Chatbot Unauthenticated Request ──────────────────────────────
    client.logout()
    resp_chat_unauth = client.post(
        '/api/ai/chat/',
        data='{"message": "Hello"}',
        content_type='application/json'
    )
    assert resp_chat_unauth.status_code == 401, f"Expected 401, got {resp_chat_unauth.status_code}"
    json_unauth = resp_chat_unauth.json()
    assert "Authentication required" in json_unauth.get('error', ''), "Unexpected 401 error message"
    print("[OK] Test 3 Passed: Chatbot endpoint rejects unauthenticated request with 401 JSON.")

    # ── Test 4: Chatbot Session Authenticated Request ────────────────────────
    client.login(username='test_patient_user', password='PatientTest123!')
    resp_chat_session = client.post(
        '/api/ai/chat/',
        data='{"message": "Hello DocMed"}',
        content_type='application/json'
    )
    assert resp_chat_session.status_code == 200, f"Expected 200 for Session Auth, got {resp_chat_session.status_code}"
    json_session = resp_chat_session.json()
    assert "reply" in json_session, "Reply missing in session auth response"
    print("[OK] Test 4 Passed: Chatbot endpoint accepted Session Auth request!")

    # ── Test 5: Chatbot JWT Bearer Token Authenticated Request ────────────────
    client.logout()
    refresh = RefreshToken.for_user(patient_user)
    access_token = str(refresh.access_token)

    resp_chat_jwt = client.post(
        '/api/ai/chat/',
        data='{"message": "Hello via JWT"}',
        content_type='application/json',
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )
    assert resp_chat_jwt.status_code == 200, f"Expected 200 for JWT Auth, got {resp_chat_jwt.status_code}"
    json_jwt = resp_chat_jwt.json()
    assert "reply" in json_jwt, "Reply missing in JWT auth response"
    print("[OK] Test 5 Passed: Chatbot endpoint accepted JWT Bearer Auth request!")

    print("\n=== ALL ADMIN NAVBAR & CHATBOT AUTHENTICATION TESTS PASSED! ===")


if __name__ == '__main__':
    run_tests()
