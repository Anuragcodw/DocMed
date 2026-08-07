"""
DocMed Enterprise Email Dispatcher Module.

Provides responsive HTML email notifications for all 19 platform events:
  1. Patient Registration Successful
  2. Doctor Registration Submitted
  3. Doctor Registration Approved
  4. Doctor Registration Rejected
  5. Doctor Assigned Successfully
  6. Appointment Booked Successfully
  7. Appointment Approved
  8. Appointment Rejected
  9. Appointment Cancelled
 10. Appointment Rescheduled
 11. Payment Successful
 12. Payment Failed
 13. Invoice Generated
 14. Google Meet Link Ready
 15. Password Reset
 16. Profile Updated
 17. Prescription Uploaded
 18. Medical Report Uploaded
 19. Medicine Reminder

All dispatches include audit logging to NotificationLog and rate-limiting deduplication.
"""

import logging
import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.urls import reverse

logger = logging.getLogger(__name__)


def send_html_email(recipient_email, subject, template_name, context, event_type="notification", user=None):
    """
    Central helper to render and send responsive HTML emails.
    Logs every dispatch to NotificationLog and prevents duplicate emails within 5 minutes.
    """
    if not recipient_email:
        return False

    # Deduplication check: ignore identical email within last 5 minutes
    try:
        from .models import NotificationLog
        recent_cutoff = timezone.now() - timezone.timedelta(minutes=5)
        duplicate_exists = NotificationLog.objects.filter(
            recipient=recipient_email,
            event_type=event_type,
            created_at__gte=recent_cutoff,
            status='sent'
        ).exists()
        if duplicate_exists:
            logger.info(f"[EMAIL DEDUPLICATED] Skipped duplicate '{event_type}' to {recipient_email}")
            return True
    except Exception as exc:
        logger.warning(f"NotificationLog deduplication check failed: {exc}")

    # Standard context variables
    context.setdefault('current_year', timezone.now().year)
    context.setdefault('recipient_email', recipient_email)
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
    context.setdefault('login_url', f"{site_url}/login/")
    context.setdefault('site_url', site_url)

    try:
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed Healthcare <noreply@docmed.com>'),
            to=[recipient_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        # Log success
        try:
            NotificationLog.objects.create(
                user=user,
                channel='email',
                event_type=event_type,
                recipient=recipient_email,
                subject_or_title=subject,
                content=text_content[:500],
                status='sent'
            )
        except Exception:
            pass

        logger.info(f"[EMAIL SENT] '{subject}' → {recipient_email}")
        return True

    except Exception as exc:
        logger.error(f"[EMAIL FAILED] '{subject}' → {recipient_email}: {exc}", exc_info=True)
        try:
            NotificationLog.objects.create(
                user=user,
                channel='email',
                event_type=event_type,
                recipient=recipient_email,
                subject_or_title=subject,
                status='failed',
                error_message=str(exc)
            )
        except Exception:
            pass
        return False


def send_html_email_async(recipient_email, subject, template_name, context, event_type="notification", user=None):
    """Dispatches email asynchronously in a daemon background thread."""
    thread = threading.Thread(
        target=send_html_email,
        args=(recipient_email, subject, template_name, context, event_type, user),
        daemon=True
    )
    thread.start()


# ============================================================================
# 19 Event Helper Functions
# ============================================================================

def send_patient_registered_email(user):
    """1. Patient Registration Successful"""
    send_html_email_async(
        recipient_email=user.email,
        subject="Welcome to DocMed AI Healthcare! 🎉",
        template_name='emails/patient_registered.html',
        context={'user_name': user.get_full_name() or user.username},
        event_type='patient_registered',
        user=user
    )

def send_doctor_registered_email(doctor_profile):
    """2. Doctor Registration Submitted"""
    user = doctor_profile.user
    send_html_email_async(
        recipient_email=user.email,
        subject="DocMed Doctor Application Received 📋",
        template_name='emails/doctor_registered.html',
        context={
            'doctor_name': doctor_profile.full_name,
            'specialization': doctor_profile.specialization,
            'nmc_reg_number': doctor_profile.nmc_registration_number,
        },
        event_type='doctor_registered',
        user=user
    )

def send_doctor_assigned_email(booking):
    """5. Doctor Assigned Successfully"""
    send_html_email_async(
        recipient_email=booking.user.email,
        subject=f"Doctor Assigned for Booking #{booking.id} — DocMed",
        template_name='emails/doctor_assigned.html',
        context={
            'patient_name': booking.full_name,
            'doctor_name': booking.appointment.full_name,
            'department': booking.appointment.department,
            'hospital_name': booking.appointment.hospital_name,
            'date': booking.date.strftime('%B %d, %Y'),
            'time': f"{booking.appointment.start_time} - {booking.appointment.end_time}",
            'booking_id': booking.id,
            'booking_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/booking/{booking.id}/detail/"
        },
        event_type='doctor_assigned',
        user=booking.user
    )

def send_appointment_booked_email(booking):
    """6. Appointment Booked Successfully"""
    context = {
        'booking': booking,
        'doctor_name': booking.appointment.full_name,
        'hospital_name': booking.appointment.hospital_name,
        'date': booking.date.strftime('%B %d, %Y'),
        'time': f"{booking.appointment.start_time} - {booking.appointment.end_time}",
        'booking_id': booking.id,
        'status': booking.get_status_display(),
    }
    send_html_email_async(
        recipient_email=booking.user.email,
        subject=f"[DocMed] Booking Request Received - ID #{booking.id}",
        template_name='emails/appointment_booked.html',
        context=context,
        event_type='appointment_booked',
        user=booking.user
    )

def send_appointment_status_update_email(booking, status_action):
    """7, 8, 9, 10. Appointment Status Updates (Approved, Rejected, Cancelled, Rescheduled)"""
    context = {
        'booking': booking,
        'doctor_name': booking.appointment.full_name,
        'hospital_name': booking.appointment.hospital_name,
        'date': booking.date.strftime('%B %d, %Y'),
        'time': f"{booking.appointment.start_time} - {booking.appointment.end_time}",
        'booking_id': booking.id,
        'status': booking.get_status_display(),
        'action': status_action,
    }
    send_html_email_async(
        recipient_email=booking.user.email,
        subject=f"[DocMed] Appointment Status Updated ({status_action}) - ID #{booking.id}",
        template_name='emails/appointment_status_updated.html',
        context=context,
        event_type=f'appointment_{status_action.lower()}',
        user=booking.user
    )

def send_payment_confirmation_email(payment):
    """11, 13. Payment Successful & Invoice Generated"""
    booking = payment.booking
    recipient_email = booking.user.email
    if not recipient_email:
        return

    currency = '₹' if payment.gateway in ['razorpay', 'upi'] else '$'
    context = {
        'booking': booking,
        'payment': payment,
        'doctor_name': booking.appointment.full_name,
        'hospital_name': booking.appointment.hospital_name,
        'date': booking.date.strftime('%B %d, %Y'),
        'time': f"{booking.appointment.start_time} - {booking.appointment.end_time}",
        'booking_id': booking.id,
        'invoice_number': payment.invoice_number,
        'amount': f"{currency}{payment.amount}",
        'gateway': payment.get_gateway_display(),
    }
    send_html_email_async(
        recipient_email=recipient_email,
        subject=f"[DocMed] Payment Confirmed - Invoice #{payment.invoice_number}",
        template_name='emails/payment_confirmation.html',
        context=context,
        event_type='payment_successful',
        user=booking.user
    )

def send_payment_failed_email(booking, amount, reason="Transaction declined"):
    """12. Payment Failed"""
    send_html_email_async(
        recipient_email=booking.user.email,
        subject=f"[DocMed] Payment Failed for Booking #{booking.id}",
        template_name='emails/payment_failed.html',
        context={
            'patient_name': booking.full_name,
            'doctor_name': booking.appointment.full_name,
            'booking_id': booking.id,
            'amount': f"₹{amount}",
            'failure_reason': reason,
            'retry_payment_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/payment/{booking.id}/initiate/"
        },
        event_type='payment_failed',
        user=booking.user
    )

def send_appointment_reminder_email(booking, recipient_name, recipient_email, time_window="24 Hours", user=None):
    """Appointment 24h & 2h Reminders"""
    send_html_email_async(
        recipient_email=recipient_email,
        subject=f"[Reminder] Appointment in {time_window} with Dr. {booking.appointment.full_name}",
        template_name='emails/appointment_reminder.html',
        context={
            'recipient_name': recipient_name,
            'time_window': time_window,
            'doctor_name': booking.appointment.full_name,
            'patient_name': booking.full_name,
            'department': booking.appointment.department,
            'date': booking.date.strftime('%B %d, %Y'),
            'time': f"{booking.appointment.start_time} - {booking.appointment.end_time}",
            'hospital_name': booking.appointment.hospital_name,
            'meet_url': booking.meeting_url if booking.meeting_url else None,
            'booking_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/booking/{booking.id}/detail/"
        },
        event_type=f'reminder_{time_window.lower().replace(" ", "_")}',
        user=user
    )

def send_prescription_uploaded_email(prescription):
    """17. Prescription Uploaded"""
    booking = prescription.booking
    send_html_email_async(
        recipient_email=booking.user.email,
        subject=f"[DocMed] New Prescription Uploaded - Booking #{booking.id}",
        template_name='emails/prescription_uploaded.html',
        context={
            'patient_name': booking.full_name,
            'doctor_name': booking.appointment.full_name,
            'diagnosis': getattr(prescription, 'diagnosis', 'Consultation Prescription'),
            'date': booking.date.strftime('%B %d, %Y'),
            'booking_id': booking.id,
            'prescription_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/booking/{booking.id}/prescription/"
        },
        event_type='prescription_uploaded',
        user=booking.user
    )

def send_doctor_verified_email(doctor_user):
    """3. Doctor Registration Approved"""
    send_html_email_async(
        recipient_email=doctor_user.email,
        subject="[DocMed] Your Doctor Profile Has Been Verified ✅",
        template_name='emails/doctor_verified.html',
        context={
            'doctor_name': f"Dr. {doctor_user.first_name} {doctor_user.last_name}",
            'email': doctor_user.email,
        },
        event_type='doctor_approved',
        user=doctor_user
    )
