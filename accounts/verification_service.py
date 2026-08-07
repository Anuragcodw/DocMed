"""
Doctor Verification Service Module
===================================

Handles atomic Doctor ID generation, NMC Certificate Number assignment,
and post-approval / post-rejection notification email dispatches.

Features:
  • Atomic generation of Doctor ID (e.g. DOC20260001), Registration ID (REG-2026-000001),
    and NMC Certificate Number (NMC-2026-000001).
  • Database transaction on_commit hooks ensuring emails are dispatched ONLY after
    successful database commits.
  • Asynchronous/thread-safe email sending with HTML + Plain text fallback.
  • Full logging and exception safety.
"""

import logging
import threading
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


class DoctorVerificationService:
    """
    Service class managing the doctor verification lifecycle:
    Approve, Reject, ID Generation, and Email Notifications.
    """

    @classmethod
    @transaction.atomic
    def approve_doctor(cls, profile, admin_user=None, remarks=""):
        """
        Approve a doctor's registration:
          1. Atomically locks DoctorProfile row.
          2. Generates unique Doctor ID, Registration ID, and NMC Certificate Number.
          3. Sets status = 'verified' and is_verified = True.
          4. Registers transaction.on_commit callback to send email after DB commit.

        Args:
            profile:    DoctorProfile instance or PK.
            admin_user: User instance of the admin performing approval.
            remarks:    Optional admin remarks string.

        Returns:
            DoctorProfile instance updated and saved.
        """
        from appointment.models import DoctorProfile

        if not isinstance(profile, DoctorProfile):
            profile = DoctorProfile.objects.select_for_update().get(pk=profile)
        else:
            profile = DoctorProfile.objects.select_for_update().get(pk=profile.pk)

        # 1. Generate unique system IDs atomically
        profile.generate_approval_ids()

        # 2. Update status & audit trail
        profile.verification_status = 'verified'
        profile.is_verified = True
        profile.verified_by = admin_user if admin_user and admin_user.is_authenticated else None
        profile.verification_date = timezone.now()
        if remarks:
            profile.verification_remarks = remarks

        profile.save()

        logger.info(
            "Doctor profile ID=%s (User %s) APPROVED by Admin %s. Generated Doctor ID=%s, NMC Cert=%s",
            profile.pk, profile.user.email, admin_user, profile.doctor_id_code, profile.nmc_certificate_number
        )

        # 3. Schedule email notification ONLY after DB transaction is committed
        profile_pk = profile.pk
        transaction.on_commit(lambda: cls.trigger_approval_email_async(profile_pk))

        return profile

    @classmethod
    @transaction.atomic
    def reject_doctor(cls, profile, admin_user=None, remarks=""):
        """
        Reject a doctor's registration:
          1. Updates status = 'rejected' and is_verified = False.
          2. Stores admin remarks explaining the decision.
          3. Registers transaction.on_commit callback to send email after DB commit.

        Args:
            profile:    DoctorProfile instance or PK.
            admin_user: User instance of the admin performing rejection.
            remarks:    Reason/remarks for rejection.

        Returns:
            DoctorProfile instance updated and saved.
        """
        from appointment.models import DoctorProfile

        if not isinstance(profile, DoctorProfile):
            profile = DoctorProfile.objects.select_for_update().get(pk=profile)
        else:
            profile = DoctorProfile.objects.select_for_update().get(pk=profile.pk)

        profile.verification_status = 'rejected'
        profile.is_verified = False
        profile.verified_by = admin_user if admin_user and admin_user.is_authenticated else None
        profile.verification_date = timezone.now()
        if remarks:
            profile.verification_remarks = remarks

        profile.save()

        logger.info(
            "Doctor profile ID=%s (User %s) REJECTED by Admin %s. Remarks: %s",
            profile.pk, profile.user.email, admin_user, remarks
        )

        # Schedule rejection email after DB transaction commit
        profile_pk = profile.pk
        transaction.on_commit(lambda: cls.trigger_rejection_email_async(profile_pk, remarks))

        return profile

    @classmethod
    def trigger_approval_email_async(cls, profile_pk):
        """Spawns a background thread to send the approval email."""
        def _send():
            cls.send_approval_email(profile_pk)

        t = threading.Thread(target=_send, daemon=True)
        t.start()

    @classmethod
    def trigger_rejection_email_async(cls, profile_pk, remarks=""):
        """Spawns a background thread to send the rejection email."""
        def _send():
            cls.send_rejection_email(profile_pk, remarks)

        t = threading.Thread(target=_send, daemon=True)
        t.start()

    @classmethod
    def send_approval_email(cls, profile_pk):
        """
        Sends the registration approval & verification confirmation email to the doctor.
        Reads recipient email, doctor ID, NMC certificate number, and renders templates.
        """
        from appointment.models import DoctorProfile

        try:
            profile = DoctorProfile.objects.select_related('user').get(pk=profile_pk)
            user = profile.user

            if not user.email:
                logger.warning("Cannot send approval email: Doctor profile PK=%s has no email.", profile_pk)
                return

            site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
            login_url = f"{site_url}{reverse('accounts:login')}"

            context = {
                'doctor_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'doctor_id': profile.doctor_id_code or f"DOC{profile.pk:04d}",
                'nmc_certificate_number': profile.nmc_certificate_number or 'N/A',
                'nmc_registration_number': profile.nmc_registration_number or 'N/A',
                'state_medical_council': profile.state_medical_council or 'N/A',
                'login_url': login_url,
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@docmed.in'),
                'system_name': 'DocMed AI Healthcare',
                'recipient_email': user.email,
                'current_year': timezone.now().year,
            }

            subject = f"Registration Approved — Doctor ID: {context['doctor_id']} | DocMed"
            text_content = render_to_string('emails/doctor_approved.txt', context)
            html_content = render_to_string('emails/doctor_approved.html', context)

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed AI Healthcare <noreply@docmed.in>')

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            logger.info("Approval email successfully sent to Dr. %s (%s)", context['doctor_name'], user.email)

        except Exception as e:
            logger.error("Failed to send approval email for doctor profile PK=%s: %s", profile_pk, e, exc_info=True)

    @classmethod
    def send_rejection_email(cls, profile_pk, remarks=""):
        """
        Sends registration rejection notice email to the doctor.
        """
        from appointment.models import DoctorProfile

        try:
            profile = DoctorProfile.objects.select_related('user').get(pk=profile_pk)
            user = profile.user

            if not user.email:
                logger.warning("Cannot send rejection email: Doctor profile PK=%s has no email.", profile_pk)
                return

            context = {
                'doctor_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'remarks': remarks or profile.verification_remarks,
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@docmed.in'),
                'system_name': 'DocMed AI Healthcare',
                'recipient_email': user.email,
                'current_year': timezone.now().year,
            }

            subject = "Doctor Registration Status Update — DocMed AI Healthcare"
            text_content = render_to_string('emails/doctor_rejected.txt', context)
            html_content = render_to_string('emails/doctor_rejected.html', context)

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'DocMed AI Healthcare <noreply@docmed.in>')

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            logger.info("Rejection email successfully sent to Dr. %s (%s)", context['doctor_name'], user.email)

        except Exception as e:
            logger.error("Failed to send rejection email for doctor profile PK=%s: %s", profile_pk, e, exc_info=True)
