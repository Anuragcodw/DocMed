"""
Context processors for the appointment application.

Injects in-app notifications and unread count into template context
for all logged-in users.
"""

def user_notifications(request):
    """
    Returns unread in-app notifications, count, and Firebase settings for template rendering.
    """
    from django.conf import settings

    context = {
        'user_unread_notifications_count': 0,
        'user_recent_notifications': [],
        'FIREBASE_API_KEY': getattr(settings, 'FIREBASE_API_KEY', ''),
        'FIREBASE_AUTH_DOMAIN': getattr(settings, 'FIREBASE_AUTH_DOMAIN', ''),
        'FIREBASE_PROJECT_ID': getattr(settings, 'FIREBASE_PROJECT_ID', ''),
        'FIREBASE_STORAGE_BUCKET': getattr(settings, 'FIREBASE_STORAGE_BUCKET', ''),
        'FIREBASE_MESSAGING_SENDER_ID': getattr(settings, 'FIREBASE_MESSAGING_SENDER_ID', ''),
        'FIREBASE_APP_ID': getattr(settings, 'FIREBASE_APP_ID', ''),
        'FIREBASE_VAPID_PUBLIC_KEY': getattr(settings, 'FIREBASE_VAPID_PUBLIC_KEY', ''),
        'FCM_ENABLED': getattr(settings, 'FCM_ENABLED', False),
    }

    if not request.user.is_authenticated:
        return context

    try:
        from .models import InAppNotification
        notifications_qs = InAppNotification.objects.filter(user=request.user)
        context['user_unread_notifications_count'] = notifications_qs.filter(is_read=False).count()
        context['user_recent_notifications'] = notifications_qs.order_by('-created_at')[:5]
        return context
    except Exception:
        return context
