from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_appointment_email(booking, subject, template_name, context_update=None):
    """
    Generic helper to render and send appointment emails as HTML and plain-text fallbacks.
    """
    recipient_email = booking.user.email
    if not recipient_email:
        return

    context = {
        'booking': booking,
        'doctor_name': booking.appointment.full_name,
        'hospital_name': booking.appointment.hospital_name,
        'date': booking.date.strftime('%B %d, %Y'),
        'time': f"{booking.appointment.start_time} - {booking.appointment.end_time}",
        'booking_id': booking.id,
        'status': booking.get_status_display(),
    }
    if context_update:
        context.update(context_update)
        
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
        to=[recipient_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=True)

def send_appointment_booked_email(booking):
    """Send confirmation email to patient after a slot is successfully booked."""
    send_appointment_email(
        booking=booking,
        subject=f"[DocMed] Booking Request Received - ID #{booking.id}",
        template_name='emails/appointment_booked.html'
    )

def send_appointment_status_update_email(booking, status_action):
    """Send email update to patient when the doctor approves, cancels, or reschedules."""
    send_appointment_email(
        booking=booking,
        subject=f"[DocMed] Appointment Status Updated - ID #{booking.id}",
        template_name='emails/appointment_status_updated.html',
        context_update={'action': status_action}
    )


def send_payment_confirmation_email(payment):
    """
    Send payment confirmation email to patient after successful payment.
    Includes invoice number, transaction ID, and appointment details.
    """
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

    html_content = render_to_string('emails/payment_confirmation.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=f"[DocMed] Payment Confirmed - Invoice #{payment.invoice_number}",
        body=text_content,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
        to=[recipient_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=True)

    # Also send SMS/WhatsApp notification
    try:
        from .notification_service import notify_payment_success
        notify_payment_success(payment)
    except Exception:
        pass


def send_doctor_verified_email(doctor_user):
    """
    Send congratulatory email to doctor when admin verifies their profile.
    """
    recipient_email = doctor_user.email
    if not recipient_email:
        return

    context = {
        'doctor_name': f"Dr. {doctor_user.first_name} {doctor_user.last_name}",
        'email': recipient_email,
    }

    html_content = render_to_string('emails/doctor_verified.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject="[DocMed] Your Profile Has Been Verified ✅",
        body=text_content,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
        to=[recipient_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=True)

