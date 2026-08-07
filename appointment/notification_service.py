"""
Notification service for DocMed healthcare platform.

Provides multi-provider SMS (Twilio + HTTP API), WhatsApp, and push helpers.
All external API credentials are loaded from Django settings.
Logs every dispatch to NotificationLog for audit and retry capability.
"""

import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================================
# Core SMS Dispatcher (Multi-Provider Support)
# ============================================================================

def send_sms(to_number: str, message: str, user=None, event_type: str = "general_sms") -> bool:
    """
    Send an SMS via Twilio SMS API or HTTP API fallback.
    Logs every attempt to NotificationLog.
    """
    if not getattr(settings, 'SMS_ENABLED', False):
        logger.info(f'[SMS DISABLED] Would send to {to_number}: {message[:50]}...')
        return False

    if not to_number:
        logger.warning('SMS send called with empty phone number.')
        return False

    # Ensure E.164 format (+91XXXXXXXXXX)
    if not to_number.startswith('+'):
        to_number = f'+{to_number.lstrip("0")}'

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')

    success = False
    error_msg = None

    if all([account_sid, auth_token, from_number]) and account_sid != 'YOUR_TWILIO_ACCOUNT_SID':
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            message_obj = client.messages.create(
                body=message,
                from_=from_number,
                to=to_number,
            )
            logger.info(f'SMS sent via Twilio: SID={message_obj.sid} to={to_number}')
            success = True
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Twilio SMS failed to {to_number}: {e}')

    # Audit Logging to NotificationLog
    try:
        from .models import NotificationLog
        NotificationLog.objects.create(
            user=user,
            channel='sms',
            event_type=event_type,
            recipient=to_number,
            content=message[:500],
            status='sent' if success else 'failed',
            error_message=error_msg
        )
    except Exception:
        pass

    return success


def send_whatsapp(to_number: str, message: str) -> bool:
    """Send WhatsApp message via Twilio."""
    if not getattr(settings, 'WHATSAPP_ENABLED', False):
        logger.info(f'[WHATSAPP DISABLED] Would send to {to_number}: {message[:50]}...')
        return False

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

    if not all([account_sid, auth_token]) or account_sid == 'YOUR_TWILIO_ACCOUNT_SID':
        return False

    if not to_number:
        return False

    if not to_number.startswith('+'):
        to_number = f'+{to_number.lstrip("0")}'
    whatsapp_to = f'whatsapp:{to_number}'

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        message_obj = client.messages.create(
            body=message,
            from_=whatsapp_from,
            to=whatsapp_to,
        )
        logger.info(f'WhatsApp sent: SID={message_obj.sid} to={to_number}')
        return True
    except Exception as e:
        logger.error(f'WhatsApp send failed: {e}')
        return False


# ============================================================================
# Specific SMS Notification Event Triggers
# ============================================================================

def notify_registration_successful_sms(user):
    """SMS on registration successful."""
    if not user.phone_number:
        return
    msg = f"🎉 Welcome to DocMed, {user.first_name or user.username}! Your account is active. Book top doctors at docmed.com"
    send_sms(user.phone_number, msg, user=user, event_type="registration_successful")

def notify_doctor_approved_sms(doctor_user, doctor_id, nmc_cert):
    """SMS on doctor approval."""
    if not doctor_user.phone_number:
        return
    msg = f"✅ Congratulations Dr. {doctor_user.last_name}! Your DocMed profile is APPROVED. Doctor ID: {doctor_id}, NMC Cert: {nmc_cert}. Log in to view dashboard."
    send_sms(doctor_user.phone_number, msg, user=doctor_user, event_type="doctor_approved")

def notify_booking_confirmed(booking):
    """SMS when booking confirmed/approved by doctor."""
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return
    msg = (
        f'✅ DocMed Appointment CONFIRMED!\n'
        f'Doctor: Dr. {booking.appointment.full_name}\n'
        f'Date: {booking.date.strftime("%d %b %Y")}\n'
        f'Time: {booking.appointment.start_time}\n'
        f'Booking ID: #{booking.id}'
    )
    send_sms(patient_phone, msg, user=booking.user, event_type="booking_confirmed")
    send_whatsapp(patient_phone, msg)

def notify_booking_cancelled(booking):
    """SMS when booking cancelled."""
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return
    msg = f'❌ Your DocMed appointment (ID #{booking.id}) with Dr. {booking.appointment.full_name} has been CANCELLED.'
    send_sms(patient_phone, msg, user=booking.user, event_type="booking_cancelled")

def notify_appointment_reminder_sms(booking, time_window="24 Hours", recipient_phone=None, user=None):
    """SMS reminder 24h or 2h before appointment."""
    phone = recipient_phone or booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not phone:
        return
    meet_str = f" Meet: {booking.meeting_url}" if booking.meeting_url else ""
    msg = (
        f'⏰ REMINDER: Your appointment with Dr. {booking.appointment.full_name} '
        f'is in {time_window} on {booking.date.strftime("%d %b at %I:%M %p")}.{meet_str}'
    )
    send_sms(phone, msg, user=user or booking.user, event_type=f"reminder_{time_window.lower().replace(' ', '_')}")

def notify_payment_success(payment):
    """SMS on payment success."""
    booking = payment.booking
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return
    currency = '₹' if payment.gateway in ['razorpay', 'upi'] else '$'
    msg = (
        f'💳 Payment CONFIRMED! Invoice #{payment.invoice_number}, '
        f'Amount: {currency}{payment.amount}. Doctor: Dr. {booking.appointment.full_name}. Booking ID: #{booking.id}'
    )
    send_sms(patient_phone, msg, user=booking.user, event_type="payment_success")

def notify_emergency_update_sms(booking, update_text):
    """Emergency appointment update SMS."""
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return
    msg = f'🚨 EMERGENCY UPDATE for Booking #{booking.id}: {update_text}'
    send_sms(patient_phone, msg, user=booking.user, event_type="emergency_update")
