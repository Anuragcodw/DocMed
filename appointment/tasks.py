"""
Celery Tasks for DocMed Doctor Appointment System.

Defines shared tasks that are executed by Celery workers.
Scheduled by Celery Beat running every 15 minutes.
"""

import logging
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_appointment_reminders_task(self):
    """
    Celery task: Send 24-hour and 2-hour appointment reminders.
    Runs every 15 minutes via Celery Beat.
    Retries up to 3 times on failure with 60-second delay.
    """
    try:
        logger.info('[CELERY] Running send_appointment_reminders task...')
        call_command('send_appointment_reminders')
        logger.info('[CELERY] send_appointment_reminders task completed successfully.')
    except Exception as exc:
        logger.error(f'[CELERY] send_appointment_reminders task failed: {exc}', exc_info=True)
        raise self.retry(exc=exc)
