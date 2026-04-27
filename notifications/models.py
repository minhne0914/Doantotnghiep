from django.conf import settings
from django.db import models

from appoinment.models import TakeAppointment


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preference')
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    realtime_enabled = models.BooleanField(default=True)
    reminder_24h_enabled = models.BooleanField(default=True)
    reminder_1h_enabled = models.BooleanField(default=True)
    booking_updates_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification preference for {self.user.email}"


class AppointmentNotificationLog(models.Model):
    CHANNEL_CHOICES = (
        ('email', 'Email'),
        ('sms', 'SMS'),
    )
    EVENT_CHOICES = (
        ('booking_confirmed', 'Booking Confirmed'),
        ('doctor_new_booking', 'Doctor New Booking'),
        ('reminder_24h', 'Reminder 24 Hours'),
        ('reminder_1h', 'Reminder 1 Hour'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_rescheduled', 'Booking Rescheduled'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    )

    appointment = models.ForeignKey(TakeAppointment, on_delete=models.CASCADE, related_name='notification_logs')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_logs')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    event = models.CharField(max_length=50, choices=EVENT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_version = models.PositiveIntegerField(default=1)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event} via {self.channel} to {self.recipient.email}"


class RealtimeNotification(models.Model):
    LEVEL_INFO = 'info'
    LEVEL_SUCCESS = 'success'
    LEVEL_WARNING = 'warning'
    LEVEL_DANGER = 'danger'

    LEVEL_CHOICES = (
        (LEVEL_INFO, 'Info'),
        (LEVEL_SUCCESS, 'Success'),
        (LEVEL_WARNING, 'Warning'),
        (LEVEL_DANGER, 'Danger'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='realtime_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    category = models.CharField(max_length=50, default='general')
    link = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}: {self.title}"
