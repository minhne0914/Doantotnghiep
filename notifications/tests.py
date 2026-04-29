from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import RealtimeNotification
from .realtime import push_realtime_notification


User = get_user_model()


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class RealtimeNotificationTests(TestCase):
    def test_push_realtime_notification_creates_database_record(self):
        user = User.objects.create_user(
            email='patient@example.com',
            first_name='Test',
            password='pass12345',
            role='patient',
        )

        notification = push_realtime_notification(
            user,
            title='Test notification',
            message='This is a realtime notification.',
            level='info',
            category='appointment',
            link='/history/',
        )

        self.assertIsNotNone(notification)
        self.assertEqual(RealtimeNotification.objects.count(), 1)
        self.assertEqual(RealtimeNotification.objects.first().title, 'Test notification')
