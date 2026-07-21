import os
import logging
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Google Meet Service API Credentials & Settings
# ============================================================================
# INSTRUCTIONS:
# 1. Go to Google Cloud Console (https://console.cloud.google.com/)
# 2. Create a new project, enable the "Google Calendar API" or "Google Meet API".
# 3. Create OAuth 2.0 Credentials (Client ID and Client Secret).
# 4. Set these credentials in your environment variables or settings.py.
# 5. Integrate standard oauth2 client code to request calendars.readwrite access.

GOOGLE_MEET_CLIENT_ID = getattr(settings, 'GOOGLE_MEET_CLIENT_ID', 'YOUR_GOOGLE_MEET_CLIENT_ID')
GOOGLE_MEET_CLIENT_SECRET = getattr(settings, 'GOOGLE_MEET_CLIENT_SECRET', 'YOUR_GOOGLE_MEET_CLIENT_SECRET')

def create_google_meeting(booking):
    """
    Placeholder service function to generate a Google Meet link.
    
    To implement Google Meet integration:
    - Install `google-auth`, `google-auth-oauthlib`, `google-api-python-client`.
    - Authenticate doctor credentials.
    - Create a calendar event containing conferenceData with type 'hangoutsMeet'.
    - Retrieve hangLink.
    """
    # ── PLACEHOLDER GENERATOR ───────────────────────────────────────────────
    # Generates a standard-format Google Meet link: meet.google.com/abc-defg-hij
    meeting_id = f"{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[3:7]}-{uuid.uuid4().hex[7:10]}"
    meeting_url = f"https://meet.google.com/{meeting_id}"
    
    logger.info(f"Created placeholder Google Meet link: {meeting_url} for Booking #{booking.id}")
    return meeting_url
