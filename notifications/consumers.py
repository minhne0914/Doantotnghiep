from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import NotificationPreference, RealtimeNotification
from .realtime import serialize_realtime_notification, user_notification_group


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if user is None or user.is_anonymous:
            await self.close()
            return

        enabled = await self._realtime_enabled(user.id)
        if not enabled:
            await self.close()
            return

        self.group_name = user_notification_group(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        recent_items = await self._recent_notifications(user.id)
        await self.send_json({
            'type': 'notification_snapshot',
            'notifications': recent_items,
        })

    async def disconnect(self, close_code):
        group_name = getattr(self, 'group_name', None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get('action')
        if action == 'ping':
            await self.send_json({'type': 'pong'})

    async def notify(self, event):
        await self.send_json({
            'type': 'notification',
            'notification': event['notification'],
        })

    @database_sync_to_async
    def _recent_notifications(self, user_id):
        queryset = RealtimeNotification.objects.filter(user_id=user_id)[:5]
        return [serialize_realtime_notification(item) for item in reversed(list(queryset))]

    @database_sync_to_async
    def _realtime_enabled(self, user_id):
        preference, _ = NotificationPreference.objects.get_or_create(user_id=user_id)
        return preference.realtime_enabled
