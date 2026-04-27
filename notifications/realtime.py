from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import NotificationPreference, RealtimeNotification


def user_notification_group(user_id):
    return f'user_{user_id}_notifications'


def serialize_realtime_notification(notification):
    return {
        'id': notification.id,
        'title': notification.title,
        'message': notification.message,
        'level': notification.level,
        'category': notification.category,
        'link': notification.link,
        'payload': notification.payload or {},
        'created_at': timezone.localtime(notification.created_at).strftime('%d/%m/%Y %H:%M'),
    }


def push_realtime_notification(user, title, message, level='info', category='general', link='', payload=None):
    if user is None or not getattr(user, 'is_authenticated', True):
        return None

    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    if not preference.realtime_enabled:
        return None

    notification = RealtimeNotification.objects.create(
        user=user,
        title=title,
        message=message,
        level=level,
        category=category,
        link=link or '',
        payload=payload or {},
    )

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return notification

    try:
        async_to_sync(channel_layer.group_send)(
            user_notification_group(user.id),
            {
                'type': 'notify',
                'notification': serialize_realtime_notification(notification),
            },
        )
    except Exception:
        return notification
    return notification
