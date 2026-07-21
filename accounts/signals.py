import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from allauth.account.signals import email_confirmed, user_signed_up, user_logged_in
from accounts.models import User
from appointment.models import PatientProfile


@receiver(post_save, sender=User)
def auto_create_patient_profile(sender, instance, created, **kwargs):
    """
    Automatically create a PatientProfile for any user created with role='patient'
    to ensure every patient user has a profile.
    """
    if created and getattr(instance, 'role', 'patient') == 'patient':
        PatientProfile.objects.get_or_create(user=instance)


@receiver(email_confirmed)
def activate_user_on_email_confirm(email_address, **kwargs):
    """
    Activate user on email confirmation.
    """
    user = email_address.user
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])


@receiver(user_signed_up)
def on_user_signed_up(request, user, **kwargs):
    """
    Triggered when a user signs up (including Google auto signup).
    1. Triggers celebration modal & confetti experience.
    2. Sends Welcome Email in background thread.
    """
    if request:
        request.session['show_registration_success'] = True

    # Send Welcome email asynchronously
    send_google_welcome_email_background(user)


@receiver(user_logged_in)
def on_user_logged_in(request, user, **kwargs):
    """
    Triggered on every user login (including Google OAuth login).
    Sends a Security Login Alert Email in a background thread.
    """
    if request:
        send_social_login_alert_background(user, request)


def send_google_welcome_email_background(user):
    """Fire-and-forget: sends welcome email in a daemon thread."""
    def _send():
        try:
            name = user.first_name or user.username or 'User'
            subject = "Welcome to DocMed 🎉"
            message = (
                f"Hi {name},\n\n"
                f"Welcome to DocMed.\n\n"
                f"Your Google account has been connected successfully.\n\n"
                f"You can now:\n"
                f"✔ Book appointments\n"
                f"✔ Search doctors\n"
                f"✔ Upload reports\n"
                f"✔ Access AI services\n\n"
                f"Regards,\n"
                f"DocMed Team"
            )
            # Send email with HTML fallback
            try:
                html_content = (
                    f"<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 12px;'>"
                    f"<h2 style='color: #4F46E5;'>Welcome to DocMed 🎉</h2>"
                    f"<p>Hi <strong>{name}</strong>,</p>"
                    f"<p>Welcome to DocMed. Your Google account has been connected successfully.</p>"
                    f"<p>You can now:</p>"
                    f"<ul>"
                    f"<li>✔ Book appointments</li>"
                    f"<li>✔ Search doctors</li>"
                    f"<li>✔ Upload reports</li>"
                    f"<li>✔ Access AI services</li>"
                    f"</ul>"
                    f"<br><p>Regards,<br><strong>DocMed Team</strong></p>"
                    f"</div>"
                )
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
                    to=[user.email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
            except Exception:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
                    recipient_list=[user.email],
                    fail_silently=True
                )
            print(f"[WELCOME EMAIL] Sent welcome email to {user.email}")
        except Exception as e:
            print(f"[WELCOME EMAIL ERROR] {e}")

    t = threading.Thread(target=_send, daemon=True)
    t.start()


def send_social_login_alert_background(user, request):
    """Fire-and-forget: sends login alert email in a daemon thread."""
    def _send():
        try:
            name = user.first_name or user.username or 'User'
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
            ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR', 'Unknown')
            ua = request.META.get('HTTP_USER_AGENT', 'Unknown')
            login_time = timezone.localtime(timezone.now()).strftime('%B %d, %Y at %I:%M %p')

            subject = "New Login Detected 🔐"
            message = (
                f"Hi {name},\n\n"
                f"A new login was detected on your DocMed account.\n\n"
                f"Login Time: {login_time}\n"
                f"IP Address: {ip}\n"
                f"Device/Browser: {ua}\n\n"
                f"If this was not you, please secure your account immediately.\n\n"
                f"Regards,\nDocMed Security Team"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed <noreply@docmed.com>'),
                recipient_list=[user.email],
                fail_silently=True
            )
            print(f"[LOGIN ALERT EMAIL] Sent login alert to {user.email}")
        except Exception as e:
            print(f"[LOGIN ALERT ERROR] {e}")

    t = threading.Thread(target=_send, daemon=True)
    t.start()
