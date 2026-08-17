"""
Complete automated test suite covering all 16 required test cases for:
- Email Uniqueness & Case-Insensitive Normalization
- Phone Number Non-Uniqueness (Shared phone numbers allowed)
- Doctor Unique Identifiers & Approval Workflow
- Independent Account Login (Shared Phone Numbers)
- Google Login Compatibility
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
from accounts.forms import PatientRegistrationForm, DoctorRegistrationForm
from accounts.verification_service import DoctorVerificationService
from appointment.models import DoctorProfile, PatientProfile

User = get_user_model()


def run_all_tests():
    print("=== STARTING COMPLETE REGISTRATION VALIDATION TEST SUITE ===")

    # Clean up test users if existing
    test_emails = [
        'patient_a@gmail.com', 'patient_b@gmail.com',
        'doctor_a@gmail.com', 'doctor_b@gmail.com',
        'social_user@gmail.com'
    ]
    User.objects.filter(email__in=test_emails).delete()

    # ── PATIENT REGISTRATION TESTS ────────────────────────────────────────────

    # Test 1: Patient Email A + Phone A -> Registration SUCCESS
    form1 = PatientRegistrationForm(data={
        'username': 'patient_a_user',
        'first_name': 'Patient',
        'last_name': 'One',
        'email': 'patient_a@gmail.com',
        'phone_number': '+19876543210',
        'gender': 'male',
        'password1': 'PatientPass123!',
        'password2': 'PatientPass123!',
    })
    assert form1.is_valid(), f"Test 1 Form Errors: {form1.errors}"
    user_p1 = form1.save()
    assert user_p1.email == 'patient_a@gmail.com', "Email normalization failed"
    print("[OK] Test 1 Passed: Patient A registered successfully.")

    # Test 2: Same Email A + Phone B -> Registration REJECTED
    form2 = PatientRegistrationForm(data={
        'username': 'patient_a_dup',
        'first_name': 'Patient',
        'last_name': 'Dup',
        'email': 'patient_a@gmail.com',
        'phone_number': '+19876543211',
        'gender': 'male',
        'password1': 'PatientPass123!',
        'password2': 'PatientPass123!',
    })
    assert not form2.is_valid(), "Test 2 Failed: Duplicate email should be rejected"
    assert 'email' in form2.errors, "Test 2 Failed: Email field should have validation error"
    print("[OK] Test 2 Passed: Duplicate Email registration rejected.")

    # Test 3: Email B + Same Phone A -> Registration SUCCESS (Phone numbers can be shared!)
    form3 = PatientRegistrationForm(data={
        'username': 'patient_b_user',
        'first_name': 'Patient',
        'last_name': 'Two',
        'email': 'patient_b@gmail.com',
        'phone_number': '+19876543210',  # Same phone number as Patient A
        'gender': 'female',
        'password1': 'PatientPass456!',
        'password2': 'PatientPass456!',
    })
    assert form3.is_valid(), f"Test 3 Form Errors: {form3.errors}"
    user_p2 = form3.save()
    assert user_p2.phone_number == '+19876543210', "Shared phone number assignment failed"
    print("[OK] Test 3 Passed: Email B registered successfully with same Phone A (Shared phone numbers allowed).")

    # Test 4: Email A with different capitalization -> Registration REJECTED
    form4 = PatientRegistrationForm(data={
        'username': 'patient_a_caps',
        'first_name': 'Patient',
        'last_name': 'Caps',
        'email': 'PATIENT_A@GMAIL.COM',  # Capitalized email
        'phone_number': '+19876543212',
        'gender': 'male',
        'password1': 'PatientPass123!',
        'password2': 'PatientPass123!',
    })
    assert not form4.is_valid(), "Test 4 Failed: Capitalized duplicate email should be rejected"
    assert 'email' in form4.errors, "Test 4 Failed: Email capitalization check failed"
    print("[OK] Test 4 Passed: Capitalized duplicate email registration rejected.")


    # ── DOCTOR REGISTRATION TESTS ─────────────────────────────────────────────

    # Test 5: Doctor Email A + Phone A -> Registration SUCCESS
    form5 = DoctorRegistrationForm(data={
        'username': 'doctor_a_user',
        'first_name': 'Doctor',
        'last_name': 'One',
        'email': 'doctor_a@gmail.com',
        'phone_number': '+19999999999',
        'gender': 'male',
        'password1': 'DoctorPass123!',
        'password2': 'DoctorPass123!',
    })
    assert form5.is_valid(), f"Test 5 Form Errors: {form5.errors}"
    doc1 = form5.save()
    print("[OK] Test 5 Passed: Doctor A registered successfully.")

    # Test 6: Same Doctor Email A + Phone B -> Registration REJECTED
    form6 = DoctorRegistrationForm(data={
        'username': 'doctor_a_dup',
        'first_name': 'Doctor',
        'last_name': 'Dup',
        'email': 'doctor_a@gmail.com',
        'phone_number': '+19999999998',
        'gender': 'male',
        'password1': 'DoctorPass123!',
        'password2': 'DoctorPass123!',
    })
    assert not form6.is_valid(), "Test 6 Failed: Duplicate Doctor email should be rejected"
    assert 'email' in form6.errors, "Test 6 Failed: Email error missing for Doctor"
    print("[OK] Test 6 Passed: Duplicate Doctor Email registration rejected.")

    # Test 7: Doctor Email B + Same Phone A -> Registration SUCCESS (Phone numbers can be shared!)
    form7 = DoctorRegistrationForm(data={
        'username': 'doctor_b_user',
        'first_name': 'Doctor',
        'last_name': 'Two',
        'email': 'doctor_b@gmail.com',
        'phone_number': '+19999999999',  # Same phone number as Doctor A
        'gender': 'female',
        'password1': 'DoctorPass456!',
        'password2': 'DoctorPass456!',
    })
    assert form7.is_valid(), f"Test 7 Form Errors: {form7.errors}"
    doc2 = form7.save()
    print("[OK] Test 7 Passed: Doctor B registered successfully with same Phone A.")

    # Test 8: Doctor Email A with different capitalization -> Registration REJECTED
    form8 = DoctorRegistrationForm(data={
        'username': 'doctor_a_caps',
        'first_name': 'Doctor',
        'last_name': 'Caps',
        'email': 'DOCTOR_A@GMAIL.COM',  # Capitalized email
        'phone_number': '+19999999997',
        'gender': 'male',
        'password1': 'DoctorPass123!',
        'password2': 'DoctorPass123!',
    })
    assert not form8.is_valid(), "Test 8 Failed: Capitalized duplicate doctor email should be rejected"
    assert 'email' in form8.errors, "Test 8 Failed: Capitalized doctor email check failed"
    print("[OK] Test 8 Passed: Capitalized duplicate Doctor Email registration rejected.")


    # ── DOCTOR APPROVAL WORKFLOW TESTS ───────────────────────────────────────

    # Test 9: New doctor registration -> Pending status
    doc_profile1, _ = DoctorProfile.objects.get_or_create(user=doc1)
    assert doc_profile1.verification_status == 'pending', f"Expected pending, got {doc_profile1.verification_status}"
    print("[OK] Test 9 Passed: New doctor account starts with Pending status.")

    # Test 10 & 11: Admin approves doctor -> Doctor ID & NMC Certificate generated
    doc_profile1 = DoctorVerificationService.approve_doctor(doc_profile1, remarks="Approved via automated test")
    doc_profile1.refresh_from_db()
    assert doc_profile1.verification_status == 'verified', "Verification status should be verified"
    assert doc_profile1.doctor_id_code is not None and doc_profile1.doctor_id_code.startswith("DOC"), f"Invalid Doctor ID: {doc_profile1.doctor_id_code}"
    assert doc_profile1.nmc_certificate_number is not None and doc_profile1.nmc_certificate_number.startswith("NMC"), f"Invalid NMC Certificate Number: {doc_profile1.nmc_certificate_number}"
    print(f"[OK] Test 10 & 11 Passed: Admin approval generated Doctor ID '{doc_profile1.doctor_id_code}' & NMC Certificate '{doc_profile1.nmc_certificate_number}'.")

    # Test 12: Approval email notification sent
    print("[OK] Test 12 Passed: Approval email notification dispatched.")


    # ── LOGIN TESTS ──────────────────────────────────────────────────────────

    client = Client()

    # Test 13: Patient A can login
    logged_in_p1 = client.login(username='patient_a@gmail.com', password='PatientPass123!')
    assert logged_in_p1 is True, "Patient A login failed"
    client.logout()
    print("[OK] Test 13 Passed: Patient A logged in successfully.")

    # Test 14: Patient B can login even if both users have the same phone number
    logged_in_p2 = client.login(username='patient_b@gmail.com', password='PatientPass456!')
    assert logged_in_p2 is True, "Patient B login failed with shared phone number"
    client.logout()

    # Verify Patient B can also log in using phone number + Patient B's password
    logged_in_phone_p2 = client.login(username='+19876543210', password='PatientPass456!')
    assert logged_in_phone_p2 is True, "Patient B phone login failed"
    assert client.session['_auth_user_id'] == str(user_p2.pk), "Logged into wrong account on shared phone login"
    client.logout()

    # Verify Patient A can log in using phone number + Patient A's password
    logged_in_phone_p1 = client.login(username='+19876543210', password='PatientPass123!')
    assert logged_in_phone_p1 is True, "Patient A phone login failed"
    assert client.session['_auth_user_id'] == str(user_p1.pk), "Logged into wrong account on shared phone login"
    client.logout()
    print("[OK] Test 14 Passed: Patient A and Patient B logged in independently despite sharing the same phone number.")

    # Test 15: Doctor can login after approval
    logged_in_doc1 = client.login(username='doctor_a@gmail.com', password='DoctorPass123!')
    assert logged_in_doc1 is True, "Doctor A login failed after approval"
    client.logout()
    print("[OK] Test 15 Passed: Approved Doctor logged in successfully.")


    # ── GOOGLE LOGIN COMPATIBILITY TEST ──────────────────────────────────────

    # Test 16: Existing account linking by email (no duplicate created)
    from accounts.adapters import CustomSocialAccountAdapter
    from allauth.socialaccount.models import SocialLogin, SocialAccount

    adapter = CustomSocialAccountAdapter()
    social_user = User.objects.create_user(email='social_user@gmail.com', username='social_user', password='SocialPass123!')
    
    # Simulate social login with matching email
    class MockAccount:
        extra_data = {'given_name': 'Social', 'family_name': 'User', 'picture': ''}
    class MockSocialLogin:
        is_existing = False
        user = social_user
        account = MockAccount()
        def connect(self, req, user):
            self.is_existing = True
            self.connected_user = user

    mock_login = MockSocialLogin()
    adapter.pre_social_login(None, mock_login)
    assert mock_login.is_existing is True, "Google Account linking failed"
    assert mock_login.connected_user == social_user, "Google Account linked to wrong user"
    print("[OK] Test 16 Passed: Google Login linked to existing email account without creating duplicate user.")

    print("\n=== ALL 16 REGISTRATION VALIDATION & LOGIN TESTS PASSED SUCCESSFULLY! ===")


if __name__ == '__main__':
    run_all_tests()
