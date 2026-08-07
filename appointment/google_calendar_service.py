"""
Google Calendar & Google Meet Integration Service for DocMed.

Creates Google Calendar events with Meet conference links whenever a doctor
approves an appointment booking. Cancels the event when the appointment is cancelled.

HOW TO CONFIGURE:
  1. Go to Google Cloud Console → APIs & Services → Enable:
     - Google Calendar API
     - Google Meet API (optional; Meet links come from Calendar)
  2. Create a Service Account → download JSON key file.
  3. Share the service account email with the doctor's Google Calendar
     (or use domain-wide delegation for G Workspace).
  4. Set in .env:
     - GOOGLE_SERVICE_ACCOUNT_JSON  (JSON string, recommended for Render)
     - GOOGLE_CALENDAR_ID           (typically the doctor's Google Calendar ID
                                     or 'primary' for the service account calendar)
  5. Set GOOGLE_CALENDAR_ENABLED=True in .env to activate.

NOTE: Without real credentials, this service gracefully falls back to the
      placeholder UUID-based Meet link generator.
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Google Calendar Service
# ============================================================================

class GoogleCalendarService:
    """
    Service for creating and managing Google Calendar events with Meet links.

    Usage:
        service = GoogleCalendarService()
        event_id, meet_url = service.create_appointment_event(booking)
        service.cancel_appointment_event(event_id)
    """

    def __init__(self):
        self.enabled = getattr(settings, 'GOOGLE_CALENDAR_ENABLED', False)
        self.calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')
        self._service = None

    def _build_service(self):
        """
        Authenticate and build the Google Calendar API service client.
        Uses service account credentials from settings.
        """
        if self._service is not None:
            return self._service

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            service_account_json = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON', '')
            service_account_path = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_PATH', '')

            SCOPES = ['https://www.googleapis.com/auth/calendar']

            creds = None

            if service_account_json and service_account_json not in ('', '{}'):
                cred_dict = json.loads(service_account_json)
                creds = service_account.Credentials.from_service_account_info(
                    cred_dict, scopes=SCOPES
                )
            elif service_account_path:
                import os
                if os.path.exists(service_account_path):
                    creds = service_account.Credentials.from_service_account_file(
                        service_account_path, scopes=SCOPES
                    )

            if creds is None:
                logger.warning(
                    '[Google Calendar] No service account credentials configured. '
                    'Set GOOGLE_SERVICE_ACCOUNT_JSON in .env'
                )
                return None

            self._service = build('calendar', 'v3', credentials=creds)
            return self._service

        except ImportError:
            logger.warning(
                '[Google Calendar] google-api-python-client not installed. '
                'Run: pip install google-api-python-client google-auth'
            )
            return None
        except Exception as exc:
            logger.error(f'[Google Calendar] Failed to build service: {exc}', exc_info=True)
            return None

    def create_appointment_event(self, booking) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a Google Calendar event for an approved appointment.
        Automatically requests a Google Meet conference link.

        Args:
            booking: TakeAppointment model instance (must be approved).

        Returns:
            Tuple of (event_id, meet_url). Both may be None on failure.
        """
        if not self.enabled:
            logger.info('[Google Calendar] Disabled. Set GOOGLE_CALENDAR_ENABLED=True in .env')
            return None, None

        service = self._build_service()
        if service is None:
            return None, None

        try:
            appointment = booking.appointment
            doctor_name = appointment.full_name
            patient_name = booking.full_name
            patient_email = booking.user.email

            # Build event start/end datetimes
            booking_date = booking.date
            if hasattr(appointment, 'start_time') and appointment.start_time:
                start_dt = datetime.combine(
                    booking_date.date() if hasattr(booking_date, 'date') else booking_date,
                    appointment.start_time
                )
            else:
                start_dt = booking_date if isinstance(booking_date, datetime) else datetime.combine(booking_date, datetime.min.time())

            if hasattr(appointment, 'end_time') and appointment.end_time:
                end_dt = datetime.combine(
                    start_dt.date(),
                    appointment.end_time
                )
            else:
                end_dt = start_dt + timedelta(minutes=30)

            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

            event_body = {
                'summary': f'DocMed Appointment: {patient_name} with Dr. {doctor_name}',
                'description': (
                    f'Patient: {patient_name}\n'
                    f'Doctor: Dr. {doctor_name}\n'
                    f'Booking ID: #{booking.id}\n'
                    f'Message: {booking.message}\n\n'
                    f'View Booking: {site_url}/booking/{booking.id}/detail/\n\n'
                    f'Join via DocMed portal for secure video consultation.'
                ),
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': getattr(settings, 'TIME_ZONE', 'Asia/Kolkata'),
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': getattr(settings, 'TIME_ZONE', 'Asia/Kolkata'),
                },
                'attendees': [
                    {'email': patient_email, 'displayName': patient_name},
                ],
                # Request Google Meet conference link
                'conferenceData': {
                    'createRequest': {
                        'requestId': f'docmed-booking-{booking.id}',
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},         # 30 min before
                    ],
                },
                'status': 'confirmed',
            }

            # conferenceDataVersion=1 is required to get Meet link
            created_event = service.events().insert(
                calendarId=self.calendar_id,
                body=event_body,
                conferenceDataVersion=1,
                sendUpdates='all',  # Send email invites to attendees
            ).execute()

            event_id = created_event.get('id')
            meet_url = None

            # Extract Meet URL from response
            conference_data = created_event.get('conferenceData', {})
            entry_points = conference_data.get('entryPoints', [])
            for ep in entry_points:
                if ep.get('entryPointType') == 'video':
                    meet_url = ep.get('uri')
                    break

            # Fallback: try hangoutLink field
            if not meet_url:
                meet_url = created_event.get('hangoutLink')

            logger.info(
                f'[Google Calendar] Event created: {event_id} | '
                f'Meet URL: {meet_url} | Booking #{booking.id}'
            )
            return event_id, meet_url

        except Exception as exc:
            logger.error(
                f'[Google Calendar] Failed to create event for Booking #{booking.id}: {exc}',
                exc_info=True
            )
            return None, None

    def cancel_appointment_event(self, event_id: str) -> bool:
        """
        Cancel (delete) a Google Calendar event for a cancelled appointment.

        Args:
            event_id: The Google Calendar event ID to delete.

        Returns:
            True if cancelled, False on error.
        """
        if not self.enabled or not event_id:
            return False

        service = self._build_service()
        if service is None:
            return False

        try:
            service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
                sendUpdates='all',  # Notify attendees of cancellation
            ).execute()
            logger.info(f'[Google Calendar] Event {event_id} cancelled successfully.')
            return True

        except Exception as exc:
            logger.error(f'[Google Calendar] Failed to cancel event {event_id}: {exc}', exc_info=True)
            return False


# ============================================================================
# Async Calendar Operations
# ============================================================================

def create_calendar_event_async(booking, on_complete=None) -> None:
    """
    Create a Google Calendar event in a background thread.
    Optionally calls on_complete(event_id, meet_url) after creation.
    """
    def _task():
        service = GoogleCalendarService()
        event_id, meet_url = service.create_appointment_event(booking)
        if event_id and on_complete:
            try:
                on_complete(event_id, meet_url)
            except Exception as exc:
                logger.error(f'[Google Calendar] on_complete callback error: {exc}')

    threading.Thread(target=_task, daemon=True).start()


def cancel_calendar_event_async(event_id: str) -> None:
    """Cancel a Google Calendar event in a background thread."""
    def _task():
        service = GoogleCalendarService()
        service.cancel_appointment_event(event_id)

    threading.Thread(target=_task, daemon=True).start()


# ============================================================================
# Updated Google Meet Service (replaces placeholder in google_meet_service.py)
# ============================================================================

def create_google_meeting(booking) -> str:
    """
    Generate a Google Meet link for a booking.

    Attempts to create a real Meet link via Google Calendar API.
    Falls back to a formatted placeholder UUID link if credentials
    are not configured.

    Args:
        booking: TakeAppointment model instance.

    Returns:
        A Google Meet URL string.
    """
    # Try real Calendar API Meet link first
    if getattr(settings, 'GOOGLE_CALENDAR_ENABLED', False):
        service = GoogleCalendarService()
        event_id, meet_url = service.create_appointment_event(booking)
        if meet_url:
            # Save event ID back to booking for future cancellation
            try:
                if hasattr(booking, 'google_calendar_event_id'):
                    booking.google_calendar_event_id = event_id
                    booking.save(update_fields=['google_calendar_event_id'])
            except Exception:
                pass
            return meet_url

    # Fallback: generate placeholder Meet-format link
    import uuid
    parts = uuid.uuid4().hex
    meeting_id = f"{parts[:3]}-{parts[3:7]}-{parts[7:10]}"
    meet_url = f"https://meet.google.com/{meeting_id}"
    logger.info(f'[Google Meet] Generated placeholder Meet link: {meet_url} for Booking #{booking.id}')
    return meet_url
