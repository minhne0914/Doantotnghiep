from django.utils import timezone

from .models import AppointmentNotificationLog, NotificationPreference
from .tasks import send_notification_email_task, send_notification_sms_task
from .utils import humanize_booking_datetime, reminder_schedule


def get_context(booking, previous_date=None, previous_time=None):
    return {
        'booking': {
            'id': booking.id,
            'message': booking.message,
            'appointment': {
                'full_name': booking.appointment.full_name,
                'department': booking.appointment.department,
                'hospital_name': booking.appointment.hospital_name,
                'location': booking.appointment.location,
            },
        },
        'doctor': {
            'id': booking.appointment.user_id,
            'first_name': booking.appointment.user.first_name,
            'last_name': booking.appointment.user.last_name,
            'email': booking.appointment.user.email,
        },
        'patient': {
            'id': booking.user_id,
            'first_name': booking.user.first_name,
            'last_name': booking.user.last_name,
            'email': booking.user.email,
        },
        'appointment_info': humanize_booking_datetime(booking),
        'previous_date': previous_date.strftime('%d/%m/%Y') if previous_date else '',
        'previous_time': previous_time.strftime('%H:%M') if previous_time else '',
    }


def queue_email(booking, recipient, event, subject, template_name, context, eta=None):
    log = AppointmentNotificationLog.objects.create(
        appointment=booking,
        recipient=recipient,
        channel='email',
        event=event,
        scheduled_for=eta,
        booking_version=booking.notification_version,
    )
    send_notification_email_task.apply_async(
        args=[log.id, subject, template_name, context, recipient.email],
        eta=eta,
    )


def queue_sms(booking, recipient, event, message, eta=None):
    if not recipient.phone_number:
        return
    log = AppointmentNotificationLog.objects.create(
        appointment=booking,
        recipient=recipient,
        channel='sms',
        event=event,
        scheduled_for=eta,
        booking_version=booking.notification_version,
    )
    send_notification_sms_task.apply_async(
        args=[log.id, message, recipient.phone_number],
        eta=eta,
    )


def schedule_booking_notifications(booking):
    patient_pref, _ = NotificationPreference.objects.get_or_create(user=booking.user)
    doctor_pref, _ = NotificationPreference.objects.get_or_create(user=booking.appointment.user)
    context = get_context(booking)

    if patient_pref.email_enabled:
        queue_email(
            booking,
            booking.user,
            'booking_confirmed',
            'Xác nhận lịch khám',
            'emails/booking_confirmed.html',
            context,
        )

    if doctor_pref.email_enabled:
        queue_email(
            booking,
            booking.appointment.user,
            'doctor_new_booking',
            'Có bệnh nhân mới đặt lịch',
            'emails/doctor_new_booking.html',
            context,
        )

    schedule_booking_reminders(booking, patient_pref, context)


def schedule_booking_reminders(booking, patient_pref=None, context=None):
    patient_pref = patient_pref or NotificationPreference.objects.get_or_create(user=booking.user)[0]
    context = context or get_context(booking)
    reminder_times = reminder_schedule(booking)
    if patient_pref.email_enabled and patient_pref.reminder_24h_enabled and reminder_times['reminder_24h'] > timezone.now():
        queue_email(
            booking,
            booking.user,
            'reminder_24h',
            'Nhắc lịch khám trước 24 giờ',
            'emails/reminder_24h.html',
            context,
            eta=reminder_times['reminder_24h'],
        )

    if patient_pref.email_enabled and patient_pref.reminder_1h_enabled and reminder_times['reminder_1h'] > timezone.now():
        queue_email(
            booking,
            booking.user,
            'reminder_1h',
            'Nhắc lịch khám trước 1 giờ',
            'emails/reminder_1h.html',
            context,
            eta=reminder_times['reminder_1h'],
        )

    if patient_pref.sms_enabled and patient_pref.reminder_24h_enabled and reminder_times['reminder_24h'] > timezone.now():
        queue_sms(
            booking,
            booking.user,
            'reminder_24h',
            f"Nhac lich kham voi BS {booking.appointment.full_name} vao {context['appointment_info']['time']} ngay {context['appointment_info']['date']}.",
            eta=reminder_times['reminder_24h'],
        )

    if patient_pref.sms_enabled and patient_pref.reminder_1h_enabled and reminder_times['reminder_1h'] > timezone.now():
        queue_sms(
            booking,
            booking.user,
            'reminder_1h',
            f"Nhac lich kham voi BS {booking.appointment.full_name} sau 1 gio nua.",
            eta=reminder_times['reminder_1h'],
        )


def send_cancellation_notifications(booking, cancelled_by='patient'):
    patient_pref, _ = NotificationPreference.objects.get_or_create(user=booking.user)
    doctor_pref, _ = NotificationPreference.objects.get_or_create(user=booking.appointment.user)
    context = get_context(booking)
    context['cancelled_by'] = cancelled_by

    if patient_pref.email_enabled and patient_pref.booking_updates_enabled:
        queue_email(
            booking,
            booking.user,
            'booking_cancelled',
            'Lịch khám đã bị hủy',
            'emails/booking_cancelled_patient.html',
            context,
        )

    if doctor_pref.email_enabled:
        queue_email(
            booking,
            booking.appointment.user,
            'booking_cancelled',
            'Có lịch khám bị hủy',
            'emails/booking_cancelled_doctor.html',
            context,
        )


def send_reschedule_notifications(booking, previous_date, previous_time, previous_appointment=None):
    patient_pref, _ = NotificationPreference.objects.get_or_create(user=booking.user)
    doctor_pref, _ = NotificationPreference.objects.get_or_create(user=booking.appointment.user)
    context = get_context(booking, previous_date=previous_date, previous_time=previous_time)

    if patient_pref.email_enabled and patient_pref.booking_updates_enabled:
        queue_email(
            booking,
            booking.user,
            'booking_rescheduled',
            'Lịch khám đã được đổi',
            'emails/booking_rescheduled_patient.html',
            context,
        )

    if doctor_pref.email_enabled:
        queue_email(
            booking,
            booking.appointment.user,
            'booking_rescheduled',
            'Bệnh nhân đã đổi lịch khám',
            'emails/booking_rescheduled_doctor.html',
            context,
        )

    if previous_appointment and previous_appointment.user_id != booking.appointment.user_id:
        previous_doctor_pref, _ = NotificationPreference.objects.get_or_create(user=previous_appointment.user)
        if previous_doctor_pref.email_enabled:
            queue_email(
                booking,
                previous_appointment.user,
                'booking_rescheduled',
                'Bệnh nhân đã đổi sang lịch khác',
                'emails/booking_rescheduled_doctor.html',
                context,
            )

    schedule_booking_reminders(booking, patient_pref=patient_pref, context=context)
