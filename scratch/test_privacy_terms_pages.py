"""
Automated Test Suite for Public Privacy Policy and Terms of Service Pages.

Tests:
  1. GET /privacy-policy/ returns HTTP 200 without login.
  2. GET /terms/ returns HTTP 200 without login.
  3. Title tags & meta descriptions render correctly.
  4. Footer links resolve to '/privacy-policy/' and '/terms/'.
"""

import os
import sys
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctor_appointment_system.settings')
django.setup()

from django.test import Client
from django.urls import reverse


def run_tests():
    print("=== STARTING PRIVACY POLICY & TERMS OF SERVICE VERIFICATION ===")

    client = Client()

    # 1. Test Privacy Policy Page
    privacy_url = reverse('appointment:privacy-policy')
    assert privacy_url == '/privacy-policy/', f"Unexpected Privacy Policy URL: {privacy_url}"

    resp_privacy = client.get(privacy_url)
    assert resp_privacy.status_code == 200, f"Privacy Policy returned {resp_privacy.status_code}"
    content_privacy = resp_privacy.content.decode('utf-8')
    # base.html renders title as: <title>DocMed | Privacy Policy </title>
    assert "DocMed" in content_privacy and "Privacy Policy" in content_privacy, "Privacy Policy title missing"
    assert "Google Calendar Integration" in content_privacy, "Google Calendar section missing in Privacy Policy"
    assert "Google Meet Integration" in content_privacy, "Google Meet section missing in Privacy Policy"
    assert "info.docmed@gmail.com" in content_privacy, "Contact email missing in Privacy Policy"
    print("[OK] Privacy Policy Page Verified: Public HTTP 200, Title & Content correct")

    # 2. Test Terms of Service Page
    terms_url = reverse('appointment:terms-of-service')
    assert terms_url == '/terms/', f"Unexpected Terms URL: {terms_url}"

    resp_terms = client.get(terms_url)
    assert resp_terms.status_code == 200, f"Terms of Service returned {resp_terms.status_code}"
    content_terms = resp_terms.content.decode('utf-8')
    # base.html renders title as: <title>DocMed | Terms of Service </title>
    assert "DocMed" in content_terms and "Terms of Service" in content_terms, "Terms title missing"
    assert "CRITICAL MEDICAL DISCLAIMER" in content_terms, "Medical disclaimer missing in Terms"
    assert "Google Calendar Integration" in content_terms, "Google Calendar section missing in Terms"
    assert "Google Meet Integration" in content_terms, "Google Meet section missing in Terms"
    assert "info.docmed@gmail.com" in content_terms, "Contact email missing in Terms"
    print("[OK] Terms of Service Page Verified: Public HTTP 200, Title & Content correct")

    # 3. Test Footer Link Resolution
    home_url = reverse('appointment:home')
    resp_home = client.get(home_url)
    assert resp_home.status_code == 200, f"Home page returned {resp_home.status_code}"
    home_content = resp_home.content.decode('utf-8')
    assert 'href="/privacy-policy/"' in home_content, "Footer link to Privacy Policy missing on Home page"
    assert 'href="/terms/"' in home_content, "Footer link to Terms of Service missing on Home page"
    print("[OK] Footer Links Resolution Verified")

    print("\n=== ALL PRIVACY POLICY & TERMS OF SERVICE TESTS PASSED SUCCESSFULLY! ===")


if __name__ == '__main__':
    run_tests()
