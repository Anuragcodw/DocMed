"""
AppConfig for the appointment app.

Starts the background scheduler automatically when the Django server initialises,
ensuring 24-hour and 2-hour appointment reminders run reliably without any
manual cron setup or external infrastructure.
"""

import os
import sys
from django.apps import AppConfig


class AppointmentConfig(AppConfig):
    name = 'appointment'
    verbose_name = 'DocMed Appointments'

    def ready(self):
        """
        Called once when the Django application registry is fully populated.

        - Skips scheduler startup during management commands like makemigrations, migrate,
          collectstatic, etc. to avoid database access before tables exist.
        - Skips during test runs (pytest / unittest).
        - In production (gunicorn/uvicorn) the scheduler starts automatically.
        """
        # Skip during management commands that don't need the scheduler
        skip_commands = {
            'makemigrations', 'migrate', 'collectstatic', 'shell',
            'createsuperuser', 'dbshell', 'test', 'check',
            'send_appointment_reminders',
        }
        argv = sys.argv
        if len(argv) > 1 and argv[1] in skip_commands:
            return

        # Skip during pytest test collection
        if 'pytest' in sys.modules or 'unittest' in sys.modules:
            return

        # Skip if DISABLE_SCHEDULER env variable is set to True
        if os.environ.get('DISABLE_SCHEDULER', '').lower() in ('true', '1', 'yes'):
            return

        # Start the background reminder scheduler
        try:
            from .scheduler import start_apscheduler
            start_apscheduler()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                f'Background scheduler failed to start: {exc}'
            )
