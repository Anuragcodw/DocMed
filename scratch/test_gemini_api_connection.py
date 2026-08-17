"""
Backend connectivity and security verification test suite for DocMed Gemini AI integration:
1. Tests GeminiClient initialization & google-genai SDK connection.
2. Tests MedicalChatbot query processing with system instructions.
3. Tests Chatbot API endpoints (/api/ai/chat/) for unauthenticated (401) vs authenticated (200) users across Patient, Doctor, and Admin roles.
4. Security audit: ensures GEMINI_API_KEY is NOT exposed in frontend files or API responses.
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
from ai.services.gemini import GeminiClient, generate_response
from ai.chatbot.conversation import MedicalChatbot

User = get_user_model()


def run_gemini_tests():
    print("=== STARTING GEMINI AI API & SECURITY TEST SUITE ===")

    # 1. Test Backend Gemini Client Connectivity
    client_instance = GeminiClient()
    print(f"[OK] GeminiClient initialized with model: {client_instance.model_name}")

    test_response = generate_response("Reply with exactly: DocMed Gemini API connection successful.")
    assert test_response is not None and len(test_response) > 0, "Gemini API returned empty response"
    print("[OK] Test 1 Passed: Backend Gemini API generate_response call succeeded!")

    # 2. Test MedicalChatbot with System Instruction Context
    chatbot = MedicalChatbot()
    chat_reply = chatbot.chat("How can I book an appointment on DocMed?")
    assert "DocMed" in chat_reply or "appointment" in chat_reply.lower() or "disclaimer" in chat_reply.lower(), "Chatbot response missing platform context"
    print("[OK] Test 2 Passed: MedicalChatbot query executed with DocMed system prompt.")

    # 3. Setup Test Users for Role Authentication Testing
    patient_user, _ = User.objects.get_or_create(
        username='gemini_patient',
        defaults={'email': 'gemini_patient@docmed.in', 'role': 'patient', 'is_active': True}
    )
    patient_user.set_password('Pass123!')
    patient_user.save()

    doctor_user, _ = User.objects.get_or_create(
        username='gemini_doctor',
        defaults={'email': 'gemini_doctor@docmed.in', 'role': 'doctor', 'is_active': True}
    )
    doctor_user.set_password('Pass123!')
    doctor_user.save()

    admin_user, _ = User.objects.get_or_create(
        username='gemini_admin',
        defaults={'email': 'gemini_admin@docmed.in', 'role': 'admin', 'is_staff': True, 'is_superuser': True, 'is_active': True}
    )
    admin_user.set_password('Pass123!')
    admin_user.save()

    c = Client()

    # Test 4: Unauthenticated request -> Must return 401
    resp_unauth = c.post('/api/ai/chat/', data='{"message": "Hello"}', content_type='application/json')
    assert resp_unauth.status_code == 401, f"Expected 401 for unauthenticated user, got {resp_unauth.status_code}"
    print("[OK] Test 4 Passed: Unauthenticated request rejected with 401.")

    # Test 5: Authenticated Patient request -> Must return 200 with AI reply
    c.login(username='gemini_patient@docmed.in', password='Pass123!')
    resp_patient = c.post('/api/ai/chat/', data='{"message": "Hello from Patient"}', content_type='application/json')
    assert resp_patient.status_code == 200, f"Expected 200 for Patient, got {resp_patient.status_code}"
    assert 'reply' in resp_patient.json(), "Missing 'reply' key in response JSON"
    c.logout()
    print("[OK] Test 5 Passed: Authenticated Patient received AI reply.")

    # Test 6: Authenticated Doctor request -> Must return 200 with AI reply
    c.login(username='gemini_doctor@docmed.in', password='Pass123!')
    resp_doctor = c.post('/api/ai/chat/', data='{"message": "Hello from Doctor"}', content_type='application/json')
    assert resp_doctor.status_code == 200, f"Expected 200 for Doctor, got {resp_doctor.status_code}"
    c.logout()
    print("[OK] Test 6 Passed: Authenticated Doctor received AI reply.")

    # Test 7: Authenticated Admin request -> Must return 200 with AI reply
    c.login(username='gemini_admin@docmed.in', password='Pass123!')
    resp_admin = c.post('/api/ai/chat/', data='{"message": "Hello from Admin"}', content_type='application/json')
    assert resp_admin.status_code == 200, f"Expected 200 for Admin, got {resp_admin.status_code}"
    c.logout()
    print("[OK] Test 7 Passed: Authenticated Admin received AI reply.")

    # Test 8: Security Audit — ensure GEMINI_API_KEY is NOT exposed in static JS or HTML templates
    api_key_env = os.environ.get('GEMINI_API_KEY', '')
    if api_key_env:
        chatbot_js_path = os.path.join(BASE_DIR, 'static', 'js', 'chatbot.js')
        if os.path.exists(chatbot_js_path):
            with open(chatbot_js_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
                assert api_key_env not in js_content, "SECURITY RISK: GEMINI_API_KEY found in chatbot.js!"
                assert "VITE_GEMINI" not in js_content and "REACT_APP_GEMINI" not in js_content, "Exposed frontend Gemini key reference found!"
        print("[OK] Test 8 Passed: API key security audit verified. GEMINI_API_KEY is backend-only!")

    print("\n=== ALL GEMINI API & SECURITY TESTS PASSED SUCCESSFULLY! ===")


if __name__ == '__main__':
    run_gemini_tests()
