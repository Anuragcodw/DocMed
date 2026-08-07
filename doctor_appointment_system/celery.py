"""
Celery Configuration for DocMed Doctor Appointment System.

Configures Celery with Redis broker for background task execution
and Celery Beat periodic scheduling for 24-hour and 2-hour reminders.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctor_appointment_system.settings')

app = Celery('doctor_appointment_system')

# Load task configuration from Django settings using CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all registered Django apps (e.g. appointment/tasks.py)
app.autodiscover_tasks()

# Configure Celery Beat Periodic Schedule
app.conf.beat_schedule = {
    'send-appointment-reminders-every-15-mins': {
        'task': 'appointment.tasks.send_appointment_reminders_task',
        'schedule': crontab(minute='*/15'),  # Runs every 15 minutes
    },
}
