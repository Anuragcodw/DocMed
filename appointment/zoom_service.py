import os
import logging
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Zoom Service API Credentials & Settings
# ============================================================================
# INSTRUCTIONS:
# 1. Register a Zoom developer account (https://marketplace.zoom.us/)
# 2. Build a "Server-to-Server OAuth" app.
# 3. Retrieve Client ID, Client Secret, and Account ID.
# 4. Configure these in your settings.py or environment variables.

ZOOM_CLIENT_ID = getattr(settings, 'ZOOM_CLIENT_ID', 'YOUR_ZOOM_CLIENT_ID')
ZOOM_CLIENT_SECRET = getattr(settings, 'ZOOM_CLIENT_SECRET', 'YOUR_ZOOM_CLIENT_SECRET')
ZOOM_ACCOUNT_ID = getattr(settings, 'ZOOM_ACCOUNT_ID', 'YOUR_ZOOM_ACCOUNT_ID')

def create_zoom_meeting(booking):
    """
    Placeholder service function to generate a Zoom Meeting link.
    
    To implement Zoom Server-to-Server OAuth:
    - POST to https://zoom.us/oauth/token with basic auth headers using client ID/secret.
    - Set grant_type=account_credentials and account_id.
    - Call POST /users/me/meetings with JWT token in authorization header.
    - Extract join_url from response.
    """
    # ── PLACEHOLDER GENERATOR ───────────────────────────────────────────────
    # Generates a standard Zoom meeting link: zoom.us/j/1234567890
    meeting_id = "".join(str(uuid.uuid4().int)[:11])
    meeting_url = f"https://zoom.us/j/{meeting_id}"
    
    logger.info(f"Created placeholder Zoom meeting link: {meeting_url} for Booking #{booking.id}")
    return meeting_url
