"""
Django Management Command: send_appointment_reminders
======================================================
Scans approved appointments and automatically sends multi-channel reminders
(Email, SMS, FCM Push) to both Patients and Doctors:
  - 24 Hours Before Appointment
  - 2 Hours Before Appointment

Usage:
  python manage.py send_appointment_reminders

Can be scheduled via Cron, Windows Task Scheduler, or Celery Beat.
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from appointment.models import TakeAppointment, NotificationLog
from appointment.emails import send_appointment_reminder_email
from appointment.notification_service import notify_appointment_reminder_sms
from appointment.fcm_service import notify_appointment_reminder

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send 24-hour and 2-hour multi-channel appointment reminders to patients and doctors.'

    def handle(self, *args, **options):
        now = timezone.now()

        # ── 1. 24-Hour Reminders (Range: 23h 30m to 24h 30m) ──────────────────
        start_24h = now + timedelta(hours=23, minutes=30)
        end_24h = now + timedelta(hours=24, minutes=30)
        self.process_reminders(start_24h, end_24h, time_window="24 Hours")

        # ── 2. 2-Hour Reminders (Range: 1h 30m to 2h 30m) ─────────────────────
        start_2h = now + timedelta(hours=1, minutes=30)
        end_2h = now + timedelta(hours=2, minutes=30)
        self.process_reminders(start_2h, end_2h, time_window="2 Hours")

        self.stdout.write(self.style.SUCCESS('Successfully processed appointment reminders.'))

    def process_reminders(self, time_start, time_end, time_window="24 Hours"):
        event_key = f"reminder_{time_window.lower().replace(' ', '_')}"
        is_24h = (time_window == "24 Hours")

        # Fetch approved bookings within time window
        filter_kwargs = {
            'status': 'approved',
            'date__range': (time_start, time_end),
        }
        if is_24h:
            filter_kwargs['reminder_24h_sent'] = False
        else:
            filter_kwargs['reminder_2h_sent'] = False

        bookings = TakeAppointment.objects.filter(**filter_kwargs).select_related('user', 'appointment', 'appointment__user')

        for booking in bookings:
            patient_email = booking.user.email
            doctor_email = booking.appointment.user.email

            # Deduplication: Check if reminder already logged for patient
            already_sent = NotificationLog.objects.filter(
                recipient=patient_email,
                event_type=event_key,
                status='sent'
            ).exists()

            if already_sent:
                if is_24h:
                    booking.reminder_24h_sent = True
                else:
                    booking.reminder_2h_sent = True
                booking.save(update_fields=['reminder_24h_sent', 'reminder_2h_sent'])
                logger.info(f"Skipping duplicate {time_window} reminder for Booking #{booking.id}")
                continue

            # 1. Send Patient Email, SMS, FCM Push
            try:
                send_appointment_reminder_email(
                    booking=booking,
                    recipient_name=booking.full_name,
                    recipient_email=patient_email,
                    time_window=time_window,
                    user=booking.user
                )
                notify_appointment_reminder_sms(
                    booking=booking,
                    time_window=time_window,
                    recipient_phone=booking.phone_number or getattr(booking.user, 'phone_number', ''),
                    user=booking.user
                )
                notify_appointment_reminder(booking)
            except Exception as exc:
                logger.error(f"Failed to send patient reminder for Booking #{booking.id}: {exc}")

            # 2. Send Doctor Email & SMS
            try:
                doctor_name = f"Dr. {booking.appointment.full_name}"
                send_appointment_reminder_email(
                    booking=booking,
                    recipient_name=doctor_name,
                    recipient_email=doctor_email,
                    time_window=time_window,
                    user=booking.appointment.user
                )
                doctor_phone = getattr(booking.appointment.user, 'phone_number', '')
                if doctor_phone:
                    notify_appointment_reminder_sms(
                        booking=booking,
                        time_window=time_window,
                        recipient_phone=doctor_phone,
                        user=booking.appointment.user
                    )
            except Exception as exc:
                logger.error(f"Failed to send doctor reminder for Booking #{booking.id}: {exc}")

            if is_24h:
                booking.reminder_24h_sent = True
            else:
                booking.reminder_2h_sent = True
            booking.save(update_fields=['reminder_24h_sent', 'reminder_2h_sent'])

            logger.info(f"Sent {time_window} reminders for Booking #{booking.id}")
