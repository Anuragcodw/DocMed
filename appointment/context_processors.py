"""
Context processors for the appointment application.

Injects in-app notifications and unread count into template context
for all logged-in users.
"""

def user_notifications(request):
    """
    Returns unread in-app notifications and count for the authenticated user.
    """
    if not request.user.is_authenticated:
        return {
            'user_unread_notifications_count': 0,
            'user_recent_notifications': [],
        }

    try:
        from .models import InAppNotification
        notifications_qs = InAppNotification.objects.filter(user=request.user)
        unread_count = notifications_qs.filter(is_read=False).count()
        recent_notifications = notifications_qs.order_by('-created_at')[:5]
        return {
            'user_unread_notifications_count': unread_count,
            'user_recent_notifications': recent_notifications,
        }
    except Exception:
        return {
            'user_unread_notifications_count': 0,
            'user_recent_notifications': [],
        }
