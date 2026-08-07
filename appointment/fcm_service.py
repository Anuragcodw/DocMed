"""
Firebase Cloud Messaging (FCM) Push Notification Service.

Handles sending push notifications to registered devices using
the firebase_admin SDK (already in requirements.txt as firebase-admin==6.7.0).

HOW TO CONFIGURE:
  1. Go to Firebase Console → Project Settings → Service Accounts.
  2. Click "Generate new private key" → download JSON.
  3. Set FIREBASE_SERVICE_ACCOUNT_JSON (JSON string) or
     FIREBASE_SERVICE_ACCOUNT_PATH (path to JSON file) in .env.
  4. Set FIREBASE_VAPID_PUBLIC_KEY to your Web Push public key.
  5. Set FCM_ENABLED=True in .env to activate push notifications.

Notifications are sent in a background thread so they never block HTTP responses.
"""

import json
import logging
import threading
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Firebase Admin SDK Initializer (singleton pattern)
# ============================================================================

_firebase_initialized = False
_firebase_init_lock = threading.Lock()


def _initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK once (singleton).
    Returns True if Firebase is ready, False if credentials are missing/invalid.
    """
    global _firebase_initialized

    if _firebase_initialized:
        return True

    with _firebase_init_lock:
        if _firebase_initialized:
            return True

        try:
            import firebase_admin
            from firebase_admin import credentials

            # Prevent double-initialization
            if firebase_admin._apps:
                _firebase_initialized = True
                return True

            service_account_json = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', '')
            service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_PATH', '')

            if service_account_json and service_account_json not in ('', '{}'):
                # JSON string provided directly (recommended for Render/cloud)
                try:
                    cred_dict = json.loads(service_account_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    _firebase_initialized = True
                    logger.info('[FCM] Firebase Admin SDK initialized from JSON string.')
                    return True
                except (json.JSONDecodeError, Exception) as exc:
                    logger.error(f'[FCM] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {exc}')
                    return False

            elif service_account_path and service_account_path not in ('', 'YOUR_SERVICE_ACCOUNT_PATH'):
                # File path provided
                import os
                if os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                    _firebase_initialized = True
                    logger.info('[FCM] Firebase Admin SDK initialized from file path.')
                    return True
                else:
                    logger.warning(f'[FCM] Service account file not found: {service_account_path}')
                    return False

            else:
                logger.warning(
                    '[FCM] Firebase credentials not configured. '
                    'Set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH in .env'
                )
                return False

        except ImportError:
            logger.warning('[FCM] firebase_admin not installed. Run: pip install firebase-admin')
            return False
        except Exception as exc:
            logger.error(f'[FCM] Firebase initialization error: {exc}')
            return False


# ============================================================================
# Core FCM Sender
# ============================================================================

def send_fcm_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    image_url: Optional[str] = None,
) -> bool:
    """
    Send a push notification to a single device via FCM.

    Args:
        fcm_token: The device registration token (stored on the User model).
        title: Notification title (shown in browser/device notification bar).
        body: Notification body text.
        data: Optional key-value dict of extra data sent to service worker.
        image_url: Optional URL to show an image in the notification.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not getattr(settings, 'FCM_ENABLED', False):
        logger.info(f'[FCM DISABLED] Would send to token {fcm_token[:20]}... title="{title}"')
        return False

    if not fcm_token:
        logger.warning('[FCM] send_fcm_notification called with empty fcm_token.')
        return False

    if not _initialize_firebase():
        return False

    try:
        from firebase_admin import messaging

        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url,
        )

        # Web Push config (for browsers/PWA)
        webpush = messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title,
                body=body,
                icon='/static/img/logo.png',
                badge='/static/img/badge.png',
                image=image_url,
                actions=[
                    messaging.WebpushNotificationAction(
                        action='view',
                        title='View Booking',
                    )
                ],
            ),
            fcm_options=messaging.WebpushFCMOptions(
                link=getattr(settings, 'SITE_URL', 'http://localhost:8000') + '/patient/bookings/',
            ),
        )

        # Android Push config (for Android apps if applicable)
        android = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                icon='ic_notification',
                color='#2563EB',
                sound='default',
            ),
        )

        message = messaging.Message(
            notification=notification,
            webpush=webpush,
            android=android,
            data={str(k): str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )

        response = messaging.send(message)
        logger.info(f'[FCM] Notification sent successfully. Message ID: {response}')
        return True

    except Exception as exc:
        logger.error(f'[FCM] Failed to send notification: {exc}', exc_info=True)
        return False


def send_fcm_to_user(user, title: str, body: str, data: Optional[dict] = None) -> bool:
    """
    Send a push notification to a user's registered FCM device token.
    Safe to call even if the user has no FCM token (no-op).

    Args:
        user: Django User model instance (must have fcm_token field).
        title: Notification title.
        body: Notification body text.
        data: Optional extra data dict.

    Returns:
        True if sent, False if no token or on error.
    """
    fcm_token = getattr(user, 'fcm_token', None)
    if not fcm_token:
        logger.debug(f'[FCM] User {user.email} has no FCM token. Skipping.')
        return False
    return send_fcm_notification(fcm_token, title, body, data)


def send_fcm_to_user_async(user, title: str, body: str, data: Optional[dict] = None) -> None:
    """
    Send a push notification to a user in a background thread.
    This ensures FCM sending never blocks HTTP request processing.
    """
    thread = threading.Thread(
        target=send_fcm_to_user,
        args=(user, title, body, data),
        daemon=True,
    )
    thread.start()


# ============================================================================
# High-Level Appointment Notification Helpers
# ============================================================================

def notify_appointment_approved(booking) -> None:
    """Notify patient that their appointment has been approved by the doctor."""
    send_fcm_to_user_async(
        user=booking.user,
        title='✅ Appointment Approved!',
        body=f'Your appointment with Dr. {booking.appointment.full_name} on '
             f'{booking.date.strftime("%b %d, %Y")} has been approved.',
        data={
            'type': 'appointment_approved',
            'booking_id': str(booking.id),
        },
    )


def notify_appointment_cancelled(booking) -> None:
    """Notify patient that their appointment has been cancelled."""
    send_fcm_to_user_async(
        user=booking.user,
        title='❌ Appointment Cancelled',
        body=f'Your appointment with Dr. {booking.appointment.full_name} has been cancelled.',
        data={
            'type': 'appointment_cancelled',
            'booking_id': str(booking.id),
        },
    )


def notify_appointment_rescheduled(booking) -> None:
    """Notify patient that their appointment has been rescheduled."""
    send_fcm_to_user_async(
        user=booking.user,
        title='📅 Appointment Rescheduled',
        body=f'Your appointment with Dr. {booking.appointment.full_name} has been rescheduled '
             f'to {booking.date.strftime("%b %d, %Y at %I:%M %p")}.',
        data={
            'type': 'appointment_rescheduled',
            'booking_id': str(booking.id),
        },
    )


def notify_appointment_reminder(booking) -> None:
    """
    Send a reminder notification 24 hours before the appointment.
    Call this from a management command or scheduled task.
    """
    send_fcm_to_user_async(
        user=booking.user,
        title='⏰ Appointment Reminder',
        body=f'Reminder: You have an appointment with Dr. {booking.appointment.full_name} '
             f'tomorrow at {booking.appointment.start_time}.',
        data={
            'type': 'appointment_reminder',
            'booking_id': str(booking.id),
        },
    )


def notify_new_booking_to_doctor(booking) -> None:
    """Notify the doctor that a new booking has been received."""
    doctor_user = booking.appointment.user
    send_fcm_to_user_async(
        user=doctor_user,
        title='🔔 New Appointment Request',
        body=f'{booking.full_name} has requested an appointment on '
             f'{booking.date.strftime("%b %d, %Y")}.',
        data={
            'type': 'new_booking',
            'booking_id': str(booking.id),
        },
    )


def notify_payment_received(payment) -> None:
    """Notify doctor that payment was received for a booking."""
    booking = payment.booking
    doctor_user = booking.appointment.user
    send_fcm_to_user_async(
        user=doctor_user,
        title='💳 Payment Received',
        body=f'Payment of ₹{payment.amount} received from {booking.full_name}.',
        data={
            'type': 'payment_received',
            'payment_id': str(payment.id),
            'booking_id': str(booking.id),
        },
    )
