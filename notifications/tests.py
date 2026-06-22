from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from appoinment.models import Appointment, TakeAppointment

from .models import AppointmentNotificationLog, RealtimeNotification
from .realtime import push_realtime_notification
from .tasks import send_notification_email_task


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


class ScheduledReminderTaskTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@example.com', password='pass12345', role='doctor'
        )
        self.patient = User.objects.create_user(
            email='patient@example.com', password='pass12345', role='patient'
        )
        self.shift = Appointment.objects.create(
            user=self.doctor,
            full_name='Doctor Example',
            location='Medic Clinic',
            qualification_name='MD',
            institute_name='Medic',
            hospital_name='Medic',
            department='Cardiology',
            date=timezone.localdate() + timedelta(days=3),
            start_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('17:00', '%H:%M').time(),
        )
        self.booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.shift,
            full_name='Patient Example',
            phone_number='0900000000',
            date=self.shift.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

    @patch('notifications.tasks.send_email_message')
    def test_future_reminder_is_not_sent_when_celery_runs_eagerly(self, send_email):
        log = AppointmentNotificationLog.objects.create(
            appointment=self.booking,
            recipient=self.patient,
            channel='email',
            event='reminder_24h',
            scheduled_for=timezone.now() + timedelta(days=2),
            booking_version=self.booking.notification_version,
        )

        send_notification_email_task.run(
            log.id,
            'Reminder',
            'emails/reminder_24h.html',
            {},
            self.patient.email,
        )

        log.refresh_from_db()
        send_email.assert_not_called()
        self.assertEqual(log.status, 'pending')
        self.assertIsNone(log.sent_at)
