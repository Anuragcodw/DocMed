"""
Django Management Command: send_appointment_reminders
======================================================
Scans approved appointments and automatically sends multi-channel reminders
(Email, SMS, FCM Push) to both Patients and Doctors:
  - 24 Hours Before Appointment
  - 16 Hours Before Appointment
  - 8 Hours Before Appointment
  - 4 Hours Before Appointment
  - 2 Hours Before Appointment
  - 30 Minutes Before Appointment

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

# Map time_window string to model field name
REMINDER_FLAG_MAP = {
    "24 Hours": "reminder_24h_sent",
    "16 Hours": "reminder_16h_sent",
    "8 Hours": "reminder_8h_sent",
    "4 Hours": "reminder_4h_sent",
    "2 Hours": "reminder_2h_sent",
    "30 Minutes": "reminder_30m_sent",
}


class Command(BaseCommand):
    help = 'Send 24h, 16h, 8h, 4h, 2h, and 30-minute multi-channel appointment reminders to patients and doctors.'

    def handle(self, *args, **options):
        now = timezone.now()

        # ── 1. 24-Hour Reminders (Range: 23h 30m to 24h 30m) ──────────────────
        self.process_reminders(
            now + timedelta(hours=23, minutes=30),
            now + timedelta(hours=24, minutes=30),
            time_window="24 Hours"
        )

        # ── 2. 16-Hour Reminders (Range: 15h 30m to 16h 30m) ──────────────────
        self.process_reminders(
            now + timedelta(hours=15, minutes=30),
            now + timedelta(hours=16, minutes=30),
            time_window="16 Hours"
        )

        # ── 3. 8-Hour Reminders (Range: 7h 30m to 8h 30m) ───────────────────
        self.process_reminders(
            now + timedelta(hours=7, minutes=30),
            now + timedelta(hours=8, minutes=30),
            time_window="8 Hours"
        )

        # ── 4. 4-Hour Reminders (Range: 3h 30m to 4h 30m) ───────────────────
        self.process_reminders(
            now + timedelta(hours=3, minutes=30),
            now + timedelta(hours=4, minutes=30),
            time_window="4 Hours"
        )

        # ── 5. 2-Hour Reminders (Range: 1h 30m to 2h 30m) ───────────────────
        self.process_reminders(
            now + timedelta(hours=1, minutes=30),
            now + timedelta(hours=2, minutes=30),
            time_window="2 Hours"
        )

        # ── 6. 30-Minute Reminders (Range: 15m to 45m) ──────────────────────
        self.process_reminders(
            now + timedelta(minutes=15),
            now + timedelta(minutes=45),
            time_window="30 Minutes"
        )

        self.stdout.write(self.style.SUCCESS('Successfully processed all appointment reminders (24h, 16h, 8h, 4h, 2h, 30m).'))

    def process_reminders(self, time_start, time_end, time_window="24 Hours"):
        event_key = f"reminder_{time_window.lower().replace(' ', '_')}"
        flag_field = REMINDER_FLAG_MAP.get(time_window, "reminder_24h_sent")

        # Fetch approved bookings within time window
        filter_kwargs = {
            'status': 'approved',
            'date__range': (time_start, time_end),
            flag_field: False,
        }

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
                setattr(booking, flag_field, True)
                booking.save(update_fields=[flag_field])
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

            setattr(booking, flag_field, True)
            booking.save(update_fields=[flag_field])

            logger.info(f"Sent {time_window} reminders for Booking #{booking.id}")

