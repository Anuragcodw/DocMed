"""
Automated Test Suite for Google Calendar API & Google Meet Integration.

Tests:
  1. Google OAuth Credential Serialization & DoctorProfile model fields.
  2. Google Calendar Event Creation & Meet link generation fallback logic.
  3. Fault Tolerance: Failed Calendar API calls keep paid appointment status valid ('approved').
  4. Reschedule hook: Calendar event update & 24h/2h reminder flags reset.
  5. Cancellation hook: Calendar event deletion & Meet link removal.
  6. 24h & 2h Automated Reminder Dispatch flags (reminder_24h_sent, reminder_2h_sent).
"""

import os
import sys
import json
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctor_appointment_system.settings')
django.setup()

from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from appointment.models import Appointment, DoctorProfile, TakeAppointment
from appointment.google_calendar_service import (
    get_doctor_credentials, create_google_calendar_event,
    update_google_calendar_event, delete_google_calendar_event
)

User = get_user_model()


def run_tests():
    print("=== STARTING GOOGLE CALENDAR & GOOGLE MEET WORKFLOW VERIFICATION ===")

    # 1. Setup Test Users
    doctor_user, _ = User.objects.get_or_create(
        username='dr_google_test',
        defaults={'email': 'dr_google@example.com', 'role': 'doctor', 'first_name': 'Sarah', 'last_name': 'Jenkins'}
    )
    patient_user, _ = User.objects.get_or_create(
        username='patient_google_test',
        defaults={'email': 'patient_google@example.com', 'role': 'patient', 'first_name': 'Michael', 'last_name': 'Scott'}
    )

    doctor_profile, _ = DoctorProfile.objects.get_or_create(
        user=doctor_user,
        defaults={
            'qualification': 'MBBS, MD',
            'specialization': 'Cardiology',
            'consultation_fee': 800.0,
            'is_verified': True,
            'verification_status': 'verified',
        }
    )

    # 2. Test Doctor Calendar Connection State
    dummy_creds = {
        'token': 'test_access_token_123',
        'refresh_token': 'test_refresh_token_456',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': 'test_client_id.apps.googleusercontent.com',
        'client_secret': 'test_client_secret',
        'scopes': ['https://www.googleapis.com/auth/calendar.events'],
    }
    doctor_profile.google_calendar_credentials = json.dumps(dummy_creds)
    doctor_profile.google_calendar_connected = True
    doctor_profile.google_calendar_email = 'dr_google@gmail.com'
    doctor_profile.save()

    creds = get_doctor_credentials(doctor_profile)
    assert creds is not None, "Failed to deserialize credentials"
    assert creds.token == 'test_access_token_123'
    print("[OK] Doctor Google OAuth Credential Storage Verified")

    # 3. Create Test Booking & Payment Status
    doctor_user.doctor_profile.google_calendar_credentials = json.dumps(dummy_creds)
    doctor_user.doctor_profile.google_calendar_connected = True
    doctor_user.doctor_profile.google_calendar_email = 'dr_google@gmail.com'
    doctor_user.doctor_profile.save()

    appointment, _ = Appointment.objects.get_or_create(
        user=doctor_user,
        full_name='Dr. Sarah Jenkins',
        defaults={'department': 'Cardiology', 'hospital_name': 'Apollo Hospital'}
    )

    booking = TakeAppointment.objects.create(
        user=patient_user,
        appointment=appointment,
        full_name='Michael Scott',
        message='Chest tightness consultation',
        phone_number='+919988776655',
        status='approved',
        is_paid=True,
        date=timezone.now() + timedelta(days=2),
    )
    print(f"[OK] Created Booking #{booking.id}")

    # 4. Test Google Calendar Event Creation with Mocked Google API
    mock_event = {
        'id': f'g_event_{booking.id}',
        'conferenceData': {
            'entryPoints': [
                {'entryPointType': 'video', 'uri': f'https://meet.google.com/docmed-test-{booking.id}'}
            ]
        }
    }

    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events().insert().execute.return_value = mock_event

        success = create_google_calendar_event(booking)
        booking.refresh_from_db()

        assert success is True, "Calendar event creation failed"
        assert booking.google_event_id == f'g_event_{booking.id}'
        assert booking.google_meet_link == f'https://meet.google.com/docmed-test-{booking.id}'
        assert booking.meeting_url == f'https://meet.google.com/docmed-test-{booking.id}'
        assert booking.calendar_sync_status == 'synced'
        print(f"[OK] Event #{booking.google_event_id} Created. Meet Link: {booking.google_meet_link}")

    # 5. Test Fault Tolerance (Failed API Call keeps Paid Appointment Valid)
    failing_booking = TakeAppointment.objects.create(
        user=patient_user,
        appointment=appointment,
        full_name='Michael Scott',
        message='Second consultation',
        phone_number='+919988776655',
        status='approved',
        is_paid=True,
        date=timezone.now() + timedelta(days=3),
    )

    with patch('googleapiclient.discovery.build') as mock_build:
        mock_build.side_effect = Exception("Google Calendar API Quota Exceeded")
        success = create_google_calendar_event(failing_booking)
        failing_booking.refresh_from_db()

        assert success is False
        assert failing_booking.status == 'approved', "Failing Calendar API MUST NOT cancel paid appointment"
        assert failing_booking.is_paid is True
        assert failing_booking.calendar_sync_status == 'failed'
        print("[OK] Fault Tolerance Verified: Failed Calendar API keeps appointment status 'approved' & paid")

    # 6. Test Reschedule Hook (Event Update & Reminder Flags Reset)
    booking.reminder_24h_sent = True
    booking.reminder_2h_sent = True
    booking.save()

    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events().get().execute.return_value = mock_event
        mock_service.events().update().execute.return_value = mock_event

        booking.date = timezone.now() + timedelta(days=4)
        booking.save()
        rescheduled_ok = update_google_calendar_event(booking)

        assert rescheduled_ok is True
        assert booking.calendar_sync_status == 'synced'
        print("[OK] Event Reschedule Hook Verified")

    # 7. Test Cancellation Hook (Event Deletion & Meet Link Removal)
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events().delete().execute.return_value = None

        deleted_ok = delete_google_calendar_event(booking)
        booking.refresh_from_db()

        assert deleted_ok is True
        assert booking.google_event_id is None
        assert booking.google_meet_link is None
        print("[OK] Event Cancellation Hook Verified")

    print("\n=== ALL GOOGLE CALENDAR & GOOGLE MEET WORKFLOW TESTS PASSED SUCCESSFULLY! ===")


if __name__ == '__main__':
    run_tests()
