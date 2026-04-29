from celery import shared_task
from django.utils import timezone

from appoinment.models import TakeAppointment
from notifications.models import AppointmentNotificationLog
from notifications.services import send_email_message, send_sms_message


ACTIVE_NOTIFICATION_STATUSES = (
    TakeAppointment.STATUS_PENDING,
    TakeAppointment.STATUS_CONFIRMED,
    TakeAppointment.STATUS_ARRIVED,
)


def mark_log_failed(log, exc):
    log.status = 'failed'
    log.error_message = str(exc)
    log.save(update_fields=['status', 'error_message'])


def should_skip_notification(booking, log):
    if log.event in ('reminder_24h', 'reminder_1h', 'booking_confirmed', 'doctor_new_booking'):
        if booking.status not in ACTIVE_NOTIFICATION_STATUSES:
            return True, 'Booking is no longer active.'
        if booking.notification_version != log.booking_version:
            return True, 'Booking schedule has changed.'
    elif log.event == 'booking_rescheduled':
        if booking.status not in ACTIVE_NOTIFICATION_STATUSES:
            return True, 'Booking is no longer active.'
        if booking.notification_version != log.booking_version:
            return True, 'Booking schedule has changed.'
    elif log.event == 'booking_cancelled':
        if booking.status != TakeAppointment.STATUS_CANCELLED:
            return True, 'Booking is no longer cancelled.'
    return False, ''


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def send_notification_email_task(self, log_id, subject, template_name, context, recipient_email):
    log = AppointmentNotificationLog.objects.select_related('appointment').get(id=log_id)
    booking = log.appointment
    skip, reason = should_skip_notification(booking, log)
    if skip:
        log.status = 'skipped'
        log.error_message = reason
        log.save(update_fields=['status', 'error_message'])
        return

    try:
        send_email_message(subject, template_name, context, recipient_email)
        log.status = 'sent'
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'sent_at'])
    except Exception as exc:
        mark_log_failed(log, exc)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def send_notification_sms_task(self, log_id, message, phone_number):
    log = AppointmentNotificationLog.objects.select_related('appointment').get(id=log_id)
    booking = log.appointment
    skip, reason = should_skip_notification(booking, log)
    if skip:
        log.status = 'skipped'
        log.error_message = reason
        log.save(update_fields=['status', 'error_message'])
        return

    try:
        provider_message_id = send_sms_message(message, phone_number)
        log.status = 'sent'
        log.provider_message_id = provider_message_id
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'provider_message_id', 'sent_at'])
    except Exception as exc:
        mark_log_failed(log, exc)
        raise
