"""
DocMed Background Scheduler (APScheduler-based Fallback).

This module provides an automatic background scheduling alternative to Celery+Redis.
It uses APScheduler's BackgroundScheduler to run appointment reminders every 15 minutes,
starting automatically when the Django server starts.

WHY THIS EXISTS:
  - Celery requires Redis to be running separately.
  - On Render Free tier or simple deployments, Redis may not be available.
  - This scheduler runs inside the Django/Gunicorn process itself,
    requiring ZERO extra infrastructure.

PRECEDENCE LOGIC:
  - If Celery + Redis are configured → Celery Beat handles scheduling.
  - If Redis is unavailable → This APScheduler fallback kicks in.

USAGE:
  This module is imported by appointment/apps.py AppConfig.ready()
  so it auto-starts with every Django server launch.
"""

import logging
import threading
from django.conf import settings

logger = logging.getLogger(__name__)

# Guard to prevent double-start in dev (Django auto-reload spawns 2 processes)
_scheduler_started = False
_scheduler_lock = threading.Lock()


def run_reminder_command():
    """Execute the send_appointment_reminders management command."""
    try:
        from django.core.management import call_command
        logger.info('[SCHEDULER] Running send_appointment_reminders...')
        call_command('send_appointment_reminders')
        logger.info('[SCHEDULER] send_appointment_reminders complete.')
    except Exception as exc:
        logger.error(f'[SCHEDULER] send_appointment_reminders error: {exc}', exc_info=True)


def start_apscheduler():
    """
    Start APScheduler BackgroundScheduler to run appointment reminders every 15 minutes.
    Uses a threading lock to ensure it only starts once per process.
    """
    global _scheduler_started

    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        import atexit

        scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
        scheduler.add_job(
            func=run_reminder_command,
            trigger=IntervalTrigger(minutes=15),
            id='send_appointment_reminders',
            name='DocMed Appointment Reminder Scheduler',
            replace_existing=True,
        )
        scheduler.start()
        logger.info('[SCHEDULER] APScheduler started — appointment reminders every 15 minutes.')

        # Ensure scheduler stops cleanly on server shutdown
        atexit.register(lambda: scheduler.shutdown(wait=False))

    except ImportError:
        logger.warning('[SCHEDULER] apscheduler not installed. Falling back to thread-based scheduling.')
        _start_thread_scheduler()
    except Exception as exc:
        logger.error(f'[SCHEDULER] Failed to start APScheduler: {exc}', exc_info=True)
        _start_thread_scheduler()


def _start_thread_scheduler():
    """
    Ultra-simple fallback: background thread that loops every 15 minutes.
    No external dependencies required.
    """
    import time

    def _loop():
        logger.info('[SCHEDULER] Thread-based fallback scheduler started.')
        while True:
            time.sleep(15 * 60)  # sleep 15 minutes
            run_reminder_command()

    thread = threading.Thread(target=_loop, daemon=True, name='DocMed-ReminderScheduler')
    thread.start()
    logger.info('[SCHEDULER] Thread-based scheduler started — appointment reminders every 15 minutes.')
