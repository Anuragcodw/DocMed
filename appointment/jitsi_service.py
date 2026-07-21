import logging
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Jitsi Meet Service Settings
# ============================================================================
# INSTRUCTIONS:
# 1. By default, Jitsi is a free open-source service hosting calls at meet.jit.si.
# 2. To use a custom self-hosted or premium Jitsi 8x8 server, update the JITSI_DOMAIN.

JITSI_DOMAIN = getattr(settings, 'JITSI_DOMAIN', 'meet.jit.si')

def create_jitsi_meeting(booking):
    """
    Generate a secure, unique Jitsi room link.
    """
    # ── JITSI ROOM NAME GENERATOR ───────────────────────────────────────────
    # We combine app prefix, booking ID and short uuid to guarantee uniqueness.
    room_name = f"docmed-{booking.id}-{uuid.uuid4().hex[:8]}"
    meeting_url = f"https://{JITSI_DOMAIN}/{room_name}"
    
    logger.info(f"Created Jitsi meeting link: {meeting_url} for Booking #{booking.id}")
    return meeting_url
