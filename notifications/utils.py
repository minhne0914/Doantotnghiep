from datetime import datetime, timedelta

from django.utils import timezone


def appointment_datetime(booking):
    naive_datetime = datetime.combine(booking.date, booking.time)
    if timezone.is_naive(naive_datetime):
        return timezone.make_aware(naive_datetime, timezone.get_current_timezone())
    return naive_datetime


def reminder_schedule(booking):
    appointment_dt = appointment_datetime(booking)
    return {
        'reminder_24h': appointment_dt - timedelta(hours=24),
        'reminder_1h': appointment_dt - timedelta(hours=1),
    }


def humanize_booking_datetime(booking):
    return {
        'date': booking.date.strftime('%d/%m/%Y') if booking.date else '',
        'time': booking.time.strftime('%H:%M') if booking.time else '',
    }
