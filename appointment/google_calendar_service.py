"""
Google Calendar API & Google Meet Service Module.

Provides robust integration for:
  1. Google OAuth 2.0 Flow & Token Management
  2. Google Calendar Event Creation with Google Meet (conferenceDataVersion=1)
  3. Google Calendar Event Updates on Reschedule
  4. Google Calendar Event Deletion on Cancellation
  5. Fallback & Retry Logic (ensuring paid appointments are never cancelled if API fails)

Security & Credentials:
  - Credentials stored per Doctor on DoctorProfile.google_calendar_credentials (JSON)
  - Secrets loaded from Django settings / .env
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
import pytz

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Required Google OAuth Scope
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def get_google_oauth_flow(redirect_uri=None):
    """
    Returns a configured google_auth_oauthlib.flow.Flow instance.
    Uses GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from Django settings.
    """
    from google_auth_oauthlib.flow import Flow

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    redirect_uri = redirect_uri or getattr(settings, 'GOOGLE_REDIRECT_URI', 'https://docmed-fx0m.onrender.com/api/google/calendar/callback/')

    if not client_id or not client_secret:
        logger.warning('GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing from settings.')

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow


def get_doctor_credentials(doctor_profile):
    """
    Retrieves and refreshes Google OAuth2 Credentials for a doctor.
    Returns google.oauth2.credentials.Credentials object or None if not connected.
    """
    if not doctor_profile or not doctor_profile.google_calendar_credentials:
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds_data = json.loads(doctor_profile.google_calendar_credentials)
        credentials = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=creds_data.get('client_id', getattr(settings, 'GOOGLE_CLIENT_ID', '')),
            client_secret=creds_data.get('client_secret', getattr(settings, 'GOOGLE_CLIENT_SECRET', '')),
            scopes=creds_data.get('scopes', SCOPES)
        )

        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            # Save refreshed token back to doctor profile
            updated_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
            }
            doctor_profile.google_calendar_credentials = json.dumps(updated_data)
            doctor_profile.save(update_fields=['google_calendar_credentials'])

        return credentials
    except Exception as exc:
        logger.error(f'Failed to load/refresh credentials for Dr. {doctor_profile.full_name}: {exc}', exc_info=True)
        return None


def create_google_calendar_event(booking):
    """
    Creates a Google Calendar Event with an automatically generated Google Meet link.
    
    Workflow:
      1. Fetch Doctor's Google Calendar credentials.
      2. If doctor not connected: set calendar_sync_status = 'not_connected'.
      3. Call Google Calendar API events.insert with conferenceDataVersion=1.
      4. Extract event ID and Google Meet URI.
      5. Save google_event_id, google_meet_link, meeting_url, calendar_sync_status = 'synced'.
      6. On error: set calendar_sync_status = 'failed' (PAID APPOINTMENT IS NEVER CANCELLED).
    """
    doctor_profile = getattr(booking.appointment.user, 'doctor_profile', None)

    if not doctor_profile or not doctor_profile.google_calendar_connected:
        logger.info(f'Booking #{booking.id}: Doctor Google Calendar not connected.')
        booking.calendar_sync_status = 'not_connected'
        booking.save(update_fields=['calendar_sync_status'])
        return False

    credentials = get_doctor_credentials(doctor_profile)
    if not credentials:
        logger.warning(f'Booking #{booking.id}: Doctor Google Calendar credentials invalid/expired.')
        booking.calendar_sync_status = 'failed'
        booking.save(update_fields=['calendar_sync_status'])
        return False

    try:
        from googleapiclient.discovery import build
        service = build('calendar', 'v3', credentials=credentials)

        tz_str = getattr(booking, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
        tz = pytz.timezone(tz_str)

        # Datetime calculation
        if booking.date:
            start_dt = booking.date
        elif booking.appointment_date and booking.appointment_start_time:
            start_dt = datetime.combine(booking.appointment_date, booking.appointment_start_time)
            start_dt = tz.localize(start_dt)
        else:
            start_dt = timezone.now() + timedelta(days=1)

        # Duration 30 mins
        end_dt = start_dt + timedelta(minutes=30)

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        req_id = f"docmed-meet-{booking.id}-{uuid.uuid4().hex[:8]}"

        event_body = {
            'summary': f"DocMed Appointment - Dr. {booking.appointment.full_name}",
            'description': (
                f"🏥 DocMed Healthcare Consultation\n\n"
                f"Booking ID: #{booking.id}\n"
                f"Patient: {booking.full_name} ({booking.user.email})\n"
                f"Doctor: Dr. {booking.appointment.full_name}\n"
                f"Department: {booking.appointment.department}\n"
                f"Hospital: {booking.appointment.hospital_name}\n"
                f"Payment Status: Paid (Confirmed)\n"
                f"Notes: {booking.message or 'N/A'}"
            ),
            'start': {'dateTime': start_iso, 'timeZone': tz_str},
            'end': {'dateTime': end_iso, 'timeZone': tz_str},
            'attendees': [
                {'email': booking.user.email, 'displayName': booking.full_name},
                {'email': booking.appointment.user.email, 'displayName': f"Dr. {booking.appointment.full_name}"},
            ],
            'conferenceData': {
                'createRequest': {
                    'requestId': req_id,
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 16 * 60},
                    {'method': 'popup', 'minutes': 8 * 60},
                    {'method': 'popup', 'minutes': 2 * 60},
                    {'method': 'popup', 'minutes': 30},
                ]
            }
        }

        calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary') or 'primary'
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            conferenceDataVersion=1
        ).execute()

        event_id = event.get('id')
        meet_link = None

        # Extract Google Meet link
        conf_data = event.get('conferenceData', {})
        entry_points = conf_data.get('entryPoints', [])
        for entry in entry_points:
            if entry.get('entryPointType') == 'video':
                meet_link = entry.get('uri')
                break

        if not meet_link and event.get('hangoutLink'):
            meet_link = event.get('hangoutLink')

        booking.google_event_id = event_id
        booking.google_calendar_event_id = event_id
        if meet_link:
            booking.google_meet_link = meet_link
            booking.meeting_url = meet_link
            booking.meeting_provider = 'meet'
            booking.meeting_status = 'waiting'

        booking.calendar_sync_status = 'synced'
        booking.save()

        logger.info(f'[GOOGLE CALENDAR SUCCESS] Event created #{event_id}, Meet Link: {meet_link} for Booking #{booking.id}')
        return True

    except Exception as exc:
        logger.error(f'[GOOGLE CALENDAR ERROR] Failed for Booking #{booking.id}: {exc}', exc_info=True)
        booking.calendar_sync_status = 'failed'
        booking.save(update_fields=['calendar_sync_status'])
        # Return False but DO NOT throw exception — appointment remains paid & valid
        return False


def update_google_calendar_event(booking):
    """
    Updates existing Google Calendar event when appointment is rescheduled.
    Keeps Google Meet link intact and updates start/end time and description.
    """
    if not booking.google_event_id and not booking.google_calendar_event_id:
        # Create event if missing
        return create_google_calendar_event(booking)

    doctor_profile = getattr(booking.appointment.user, 'doctor_profile', None)
    credentials = get_doctor_credentials(doctor_profile)
    if not credentials:
        booking.calendar_sync_status = 'failed'
        booking.save(update_fields=['calendar_sync_status'])
        return False

    try:
        from googleapiclient.discovery import build
        service = build('calendar', 'v3', credentials=credentials)

        tz_str = getattr(booking, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
        tz = pytz.timezone(tz_str)

        start_dt = booking.date or timezone.now()
        end_dt = start_dt + timedelta(minutes=30)

        calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary') or 'primary'
        event_id = booking.google_event_id or booking.google_calendar_event_id

        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        event['summary'] = f"DocMed Appointment (Rescheduled) - Dr. {booking.appointment.full_name}"
        event['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': tz_str}
        event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': tz_str}
        event['description'] = (
            f"🏥 DocMed Healthcare Consultation (RESCHEDULED)\n\n"
            f"Booking ID: #{booking.id}\n"
            f"Patient: {booking.full_name}\n"
            f"Doctor: Dr. {booking.appointment.full_name}\n"
            f"New Date & Time: {start_dt.strftime('%d %b %Y %I:%M %p')}\n"
        )

        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event,
            conferenceDataVersion=1
        ).execute()

        booking.calendar_sync_status = 'synced'
        booking.save(update_fields=['calendar_sync_status'])
        logger.info(f'[GOOGLE CALENDAR RESCHEDULE] Updated event #{event_id} for Booking #{booking.id}')
        return True

    except Exception as exc:
        logger.error(f'[GOOGLE CALENDAR RESCHEDULE ERROR] Failed for Booking #{booking.id}: {exc}')
        booking.calendar_sync_status = 'failed'
        booking.save(update_fields=['calendar_sync_status'])
        return False


def delete_google_calendar_event(booking):
    """
    Deletes/cancels Google Calendar event when appointment is cancelled.
    Clears meeting link and status.
    """
    event_id = booking.google_event_id or booking.google_calendar_event_id
    if not event_id:
        return True

    doctor_profile = getattr(booking.appointment.user, 'doctor_profile', None)
    credentials = get_doctor_credentials(doctor_profile)
    if not credentials:
        return False

    try:
        from googleapiclient.discovery import build
        service = build('calendar', 'v3', credentials=credentials)
        calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary') or 'primary'

        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

        booking.google_event_id = None
        booking.google_calendar_event_id = None
        booking.google_meet_link = None
        booking.meeting_url = None
        booking.calendar_sync_status = 'pending'
        booking.save()

        logger.info(f'[GOOGLE CALENDAR CANCEL] Deleted event #{event_id} for Booking #{booking.id}')
        return True

    except Exception as exc:
        logger.error(f'[GOOGLE CALENDAR CANCEL ERROR] Failed for Booking #{booking.id}: {exc}')
        return False
