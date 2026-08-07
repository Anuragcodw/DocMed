"""
doctor_appointment_system package init.
Ensures Celery app is imported when Django starts.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
