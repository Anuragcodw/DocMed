"""
Notification service for DocMed healthcare platform.

Provides email, SMS (Twilio), and WhatsApp notification helpers.
All external API credentials are loaded from Django settings.

HOW TO CONFIGURE:
  SMS/WhatsApp: Sign up at https://www.twilio.com/
    Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env
  Enable: Set SMS_ENABLED=True and WHATSAPP_ENABLED=True in .env
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# SMS Notifications (Twilio)
# ============================================================================

def send_sms(to_number: str, message: str) -> bool:
    """
    Send an SMS via Twilio SMS API.

    ⚠️ CONFIGURE:
      1. Sign up at https://www.twilio.com/
      2. Set TWILIO_ACCOUNT_SID in .env
      3. Set TWILIO_AUTH_TOKEN in .env
      4. Set TWILIO_PHONE_NUMBER in .env (your Twilio number)
      5. Set SMS_ENABLED=True in .env

    Returns True if sent successfully, False otherwise.
    """
    if not getattr(settings, 'SMS_ENABLED', False):
        logger.info(f'[SMS DISABLED] Would send to {to_number}: {message[:50]}...')
        return False

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')

    if not all([account_sid, auth_token, from_number]) or account_sid == 'YOUR_TWILIO_ACCOUNT_SID':
        logger.warning('Twilio credentials not configured. Set TWILIO_* in .env')
        return False

    if not to_number:
        logger.warning('SMS send called with empty phone number.')
        return False

    # Ensure E.164 format (+91XXXXXXXXXX)
    if not to_number.startswith('+'):
        to_number = f'+{to_number.lstrip("0")}'

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )
        logger.info(f'SMS sent: SID={message_obj.sid} to={to_number}')
        return True
    except ImportError:
        logger.error('twilio package not installed. Run: pip install twilio')
        return False
    except Exception as e:
        logger.error(f'SMS send failed to {to_number}: {e}')
        return False


def send_whatsapp(to_number: str, message: str) -> bool:
    """
    Send a WhatsApp message via Twilio WhatsApp Business API.

    ⚠️ CONFIGURE:
      1. Set up WhatsApp Business at: https://www.twilio.com/whatsapp
      2. Set TWILIO_WHATSAPP_NUMBER in .env (usually whatsapp:+14155238886 for sandbox)
      3. Set WHATSAPP_ENABLED=True in .env

    Returns True if sent successfully, False otherwise.
    """
    if not getattr(settings, 'WHATSAPP_ENABLED', False):
        logger.info(f'[WHATSAPP DISABLED] Would send to {to_number}: {message[:50]}...')
        return False

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

    if not all([account_sid, auth_token]) or account_sid == 'YOUR_TWILIO_ACCOUNT_SID':
        logger.warning('Twilio credentials not configured.')
        return False

    if not to_number:
        return False

    # Format for WhatsApp
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
    except ImportError:
        logger.error('twilio package not installed.')
        return False
    except Exception as e:
        logger.error(f'WhatsApp send failed: {e}')
        return False


# ============================================================================
# Appointment Notification Helpers
# ============================================================================

def notify_booking_confirmed(booking):
    """
    Send SMS + WhatsApp notification when a booking is confirmed by doctor.
    Safe to call even if Twilio is not configured (logs only).
    """
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return

    msg = (
        f'✅ Your DocMed appointment is CONFIRMED!\n'
        f'Doctor: Dr. {booking.appointment.full_name}\n'
        f'Date: {booking.date.strftime("%d %b %Y")}\n'
        f'Time: {booking.appointment.start_time} - {booking.appointment.end_time}\n'
        f'Hospital: {booking.appointment.hospital_name}\n'
        f'Booking ID: #{booking.id}'
    )

    send_sms(patient_phone, msg)
    send_whatsapp(patient_phone, msg)


def notify_booking_cancelled(booking):
    """Send SMS + WhatsApp when booking is cancelled."""
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return

    msg = (
        f'❌ Your DocMed appointment has been CANCELLED.\n'
        f'Doctor: Dr. {booking.appointment.full_name}\n'
        f'Booking ID: #{booking.id}\n'
        f'Please rebook at DocMed if needed.'
    )
    send_sms(patient_phone, msg)
    send_whatsapp(patient_phone, msg)


def notify_appointment_reminder(booking):
    """
    Send appointment reminder SMS + WhatsApp (typically 24h before).
    Call this from a management command or celery task.
    """
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return

    msg = (
        f'⏰ REMINDER: Your DocMed appointment is TOMORROW!\n'
        f'Doctor: Dr. {booking.appointment.full_name}\n'
        f'Date: {booking.date.strftime("%d %b %Y")}\n'
        f'Time: {booking.appointment.start_time}\n'
        f'Hospital: {booking.appointment.hospital_name}'
    )
    send_sms(patient_phone, msg)
    send_whatsapp(patient_phone, msg)


def notify_payment_success(payment):
    """Send SMS + WhatsApp on successful payment."""
    booking = payment.booking
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    if not patient_phone:
        return

    currency = '₹' if payment.gateway in ['razorpay', 'upi'] else '$'
    msg = (
        f'💳 Payment CONFIRMED for DocMed!\n'
        f'Invoice: {payment.invoice_number}\n'
        f'Amount: {currency}{payment.amount}\n'
        f'Doctor: Dr. {booking.appointment.full_name}\n'
        f'Booking ID: #{booking.id}\n'
        f'Thank you for choosing DocMed!'
    )
    send_sms(patient_phone, msg)
    send_whatsapp(patient_phone, msg)


# ============================================================================
# Additional Notification Channels & Events (Placeholders)
# ============================================================================

def send_email(to_email: str, subject: str, message: str) -> bool:
    """
    Placeholder service for email notifications.
    ⚠️ CONFIGURE SMTP details in settings.py / .env
    """
    logger.info(f'[EMAIL PLACEHOLDER] To: {to_email} | Subject: {subject} | Msg: {message[:60]}...')
    # Future integration: django.core.mail.send_mail
    return True


def send_browser_notification(user, title: str, message: str) -> bool:
    """
    Placeholder service for Web Push / Browser notifications.
    ⚠️ CONFIGURE WebPush / VAPID keys / FCM credentials later
    """
    logger.info(f'[BROWSER PUSH PLACEHOLDER] User: {user.username} | Title: {title} | Msg: {message[:60]}...')
    return True


def notify_appointment_booked(booking):
    """Notify when appointment is booked."""
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    msg = f'🗓️ DocMed Appointment Requested! ID #{booking.id}. Status: Pending Doctor Approval.'
    if patient_phone:
        send_sms(patient_phone, msg)
        send_whatsapp(patient_phone, msg)
    send_email(booking.user.email, 'DocMed: Appointment Booked', msg)
    send_browser_notification(booking.user, 'Appointment Booked', msg)


def notify_payment_failed(payment):
    """Notify when payment fails."""
    booking = payment.booking
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    msg = f'⚠️ Payment FAILED for Booking #{booking.id}. Please try paying again.'
    if patient_phone:
        send_sms(patient_phone, msg)
    send_email(booking.user.email, 'DocMed: Payment Failed', msg)


def notify_prescription_ready(prescription):
    """Notify when a doctor writes/updates a prescription."""
    booking = prescription.booking
    patient_phone = booking.phone_number or getattr(booking.user, 'phone_number', '')
    msg = f'💊 Your prescription from Dr. {booking.appointment.full_name} is ready on DocMed!'
    if patient_phone:
        send_sms(patient_phone, msg)
        send_whatsapp(patient_phone, msg)
    send_email(booking.user.email, 'DocMed: Prescription Ready', msg)
    send_browser_notification(booking.user, 'Prescription Ready', msg)


def notify_medicine_reminder(user, medicine_name: str, dosage_time: str):
    """Periodic reminder to take medicines."""
    msg = f'🔔 HEALTH REMINDER: Take your medicine ({medicine_name}) scheduled at {dosage_time}.'
    if getattr(user, 'phone_number', ''):
        send_sms(user.phone_number, msg)
    send_browser_notification(user, 'Medicine Reminder', msg)


def notify_birthday_wishes(user):
    """Send automated birthday wishes."""
    msg = f'🎂 Happy Birthday {user.first_name}! DocMed wishes you a healthy year ahead!'
    send_email(user.email, 'Happy Birthday from DocMed!', msg)


def notify_doctor_availability(doctor, status: str):
    """Alert patients of changes in doctor availability status."""
    msg = f'📢 Dr. {doctor.full_name} status updated: {status}.'
    logger.info(f'[AVAILABILITY UPDATE] {msg}')


def notify_admin_alert(subject: str, message: str):
    """Internal admin alert notifications."""
    msg = f'🚨 [ADMIN ALERT] {subject}: {message}'
    logger.info(msg)

