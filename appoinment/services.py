"""Business logic cho appoinment app.

Tách khỏi views để:
- views.py chỉ làm validation form + render response
- nghiệp vụ (slot conflict, change log, notification) ở 1 chỗ duy nhất
- dễ test/unit-test (gọi trực tiếp service không cần Request)
"""

import datetime
import logging
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from notifications.orchestrators import (
    schedule_booking_notifications,
    send_cancellation_notifications,
    send_reschedule_notifications,
)
from notifications.realtime import push_realtime_notification

from .models import Appointment, AppointmentChangeLog, TakeAppointment


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

APPOINTMENT_CHANGE_DEADLINE_HOURS = getattr(settings, 'APPOINTMENT_CHANGE_DEADLINE_HOURS', 4)
SLOT_GAP_SECONDS = 1800  # 30 phút giữa hai lịch khám


# =============================================================================
# Helpers - thời gian
# =============================================================================

def booking_datetime(booking):
    """Ghép date + time của booking thành datetime aware ở timezone hiện tại."""
    naive = datetime.datetime.combine(booking.date, booking.time)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def booking_can_be_modified(booking):
    """Kiểm tra booking có thể đổi/hủy không.

    Trả về (can_modify: bool, error_message: str)
    """
    if booking.status not in TakeAppointment.MODIFIABLE_STATUSES:
        return False, 'Chỉ có thể thay đổi lịch đang ở trạng thái chờ xác nhận hoặc đã xác nhận.'

    appointment_dt = booking_datetime(booking)
    now = timezone.localtime()
    if appointment_dt <= now:
        return False, 'Không thể thay đổi lịch đã diễn ra hoặc đã quá giờ khám.'

    deadline = appointment_dt - datetime.timedelta(hours=APPOINTMENT_CHANGE_DEADLINE_HOURS)
    if now >= deadline:
        return False, f'Bạn chỉ có thể đổi hoặc hủy lịch trước tối thiểu {APPOINTMENT_CHANGE_DEADLINE_HOURS} giờ.'
    return True, ''


def has_slot_conflict(slot, target_date, target_time, exclude_booking_id=None):
    """Có booking nào khác trong slot/ngày trùng (cách dưới 30 phút)?

    Phải gọi trong transaction.atomic() và đã select_for_update() slot trước.
    """
    target_dt = datetime.datetime.combine(target_date, target_time)
    qs = TakeAppointment.objects.select_for_update().filter(
        appointment=slot,
        date=target_date,
        status__in=TakeAppointment.ACTIVE_STATUSES,
    )
    if exclude_booking_id is not None:
        qs = qs.exclude(pk=exclude_booking_id)

    for other in qs:
        other_dt = datetime.datetime.combine(other.date, other.time)
        if abs((other_dt - target_dt).total_seconds()) < SLOT_GAP_SECONDS:
            return True
    return False


def status_badge(status):
    """Map status -> (bootstrap class, vietnamese label)."""
    mapping = {
        TakeAppointment.STATUS_PENDING: ('warning', 'Chờ xác nhận'),
        TakeAppointment.STATUS_CONFIRMED: ('success', 'Đã xác nhận'),
        TakeAppointment.STATUS_ARRIVED: ('info', 'Đã đến khám'),
        TakeAppointment.STATUS_CANCELLED: ('secondary', 'Đã hủy'),
        TakeAppointment.STATUS_COMPLETED: ('primary', 'Đã hoàn thành'),
    }
    return mapping.get(status, ('secondary', status))


# =============================================================================
# Change log
# =============================================================================

def create_change_log(
    booking,
    action,
    *,
    changed_by,
    reason='',
    old_appointment=None,
    old_date=None,
    old_time=None,
):
    return AppointmentChangeLog.objects.create(
        booking=booking,
        action=action,
        changed_by=changed_by,
        old_appointment=old_appointment,
        new_appointment=booking.appointment,
        old_date=old_date,
        old_time=old_time,
        new_date=booking.date,
        new_time=booking.time,
        reason=reason or '',
    )


# =============================================================================
# Notifications (an toàn - không bao giờ chặn request chính)
# =============================================================================

def _safe_push(target_user, **kwargs):
    """Wrap push_realtime_notification, log lỗi mà không raise."""
    try:
        push_realtime_notification(target_user, **kwargs)
    except Exception:
        logger.exception(
            'Failed to push notification to user %s', getattr(target_user, 'id', None)
        )


def notify_patient(booking, *, title, message, level='info', link_name='patient-my-appointments'):
    _safe_push(
        booking.user,
        title=title,
        message=message,
        level=level,
        category='appointment',
        link=reverse(link_name),
        payload={'booking_id': booking.id, 'status': booking.status},
    )


def notify_doctor(booking, *, title, message, level='info'):
    _safe_push(
        booking.appointment.user,
        title=title,
        message=message,
        level=level,
        category='appointment',
        link=reverse('doctor-dashboard'),
        payload={'booking_id': booking.id, 'status': booking.status},
    )


def _fmt_dt(d, t):
    return f'{t.strftime("%H:%M")} ngày {d.strftime("%d/%m/%Y")}'


# =============================================================================
# Service layer - các use-case chính
# =============================================================================

@dataclass
class BookingResult:
    booking: TakeAppointment
    error: Optional[str] = None


class BookingService:
    """Toàn bộ nghiệp vụ tạo/sửa/hủy lịch khám."""

    # --- Tạo mới ---
    @staticmethod
    def create_booking(*, user, appointment, full_name, phone_number, message, selected_time):
        """Tạo lịch khám mới với khóa transaction để tránh double-booking.

        Raises ValueError nếu slot không hợp lệ; trả về BookingResult.
        """
        with transaction.atomic():
            locked_slot = Appointment.objects.select_for_update().get(pk=appointment.pk)

            if has_slot_conflict(locked_slot, locked_slot.date, selected_time):
                return BookingResult(booking=None, error=(
                    'Khung giờ này đã có người đặt hoặc quá sát với ca khác. '
                    'Vui lòng chọn giờ cách ít nhất 30 phút.'
                ))

            booking = TakeAppointment.objects.create(
                user=user,
                appointment=locked_slot,
                full_name=full_name,
                phone_number=phone_number,
                message=message,
                date=locked_slot.date,
                time=selected_time,
                status=TakeAppointment.STATUS_CONFIRMED,
            )
            create_change_log(
                booking,
                AppointmentChangeLog.ACTION_BOOKED,
                changed_by=user,
                reason='Bệnh nhân tạo lịch hẹn mới.',
            )

        # Side-effects sau khi commit (nằm ngoài atomic để tránh rollback notification)
        try:
            schedule_booking_notifications(booking)
        except Exception:
            logger.exception('schedule_booking_notifications failed for booking %s', booking.id)

        notify_doctor(
            booking,
            title='Có lịch hẹn mới',
            message=f'{booking.full_name} vừa đặt lịch lúc {_fmt_dt(booking.date, booking.time)}.',
            level='success',
        )
        return BookingResult(booking=booking)

    # --- Đổi lịch ---
    @staticmethod
    def reschedule_booking(*, booking, new_appointment, new_time, reason='', new_message='', changed_by):
        """Đổi sang slot mới. Trả về (booking, error_dict)."""
        # Pre-check (kiểm tra deadline lần nữa trong service)
        can_modify, message = booking_can_be_modified(booking)
        if not can_modify:
            return None, {'__all__': message}

        old_appointment = booking.appointment
        old_date = booking.date
        old_time = booking.time

        with transaction.atomic():
            locked_booking = (
                TakeAppointment.objects.select_for_update()
                .select_related('appointment', 'appointment__user', 'user')
                .get(pk=booking.pk)
            )
            current_slot = Appointment.objects.select_for_update().get(pk=locked_booking.appointment_id)
            new_slot = Appointment.objects.select_for_update().get(pk=new_appointment.pk)

            if not new_slot.is_active or new_slot.date < timezone.localdate():
                return None, {'appointment': 'Lịch mới không còn khả dụng.'}
            if new_slot.date == timezone.localdate() and new_time <= timezone.localtime().time():
                return None, {'time': 'Giờ mới phải lớn hơn thời điểm hiện tại.'}
            if not (new_slot.start_time <= new_time <= new_slot.end_time):
                return None, {'time': 'Giờ mới phải nằm trong khung khám của bác sĩ.'}

            if has_slot_conflict(new_slot, new_slot.date, new_time, exclude_booking_id=locked_booking.pk):
                return None, {'time': (
                    'Khung giờ mới đã có người đặt hoặc quá sát với ca khác. '
                    'Vui lòng chọn giờ cách ít nhất 30 phút.'
                )}

            locked_booking.appointment = new_slot
            locked_booking.date = new_slot.date
            locked_booking.time = new_time
            locked_booking.message = new_message or locked_booking.message
            locked_booking.status = TakeAppointment.STATUS_CONFIRMED
            locked_booking.notification_version += 1
            locked_booking.save(update_fields=[
                'appointment', 'date', 'time', 'message', 'status', 'notification_version',
            ])

            create_change_log(
                locked_booking,
                AppointmentChangeLog.ACTION_RESCHEDULED,
                changed_by=changed_by,
                reason=reason,
                old_appointment=current_slot if current_slot.pk != new_slot.pk else old_appointment,
                old_date=old_date,
                old_time=old_time,
            )

        # Side-effects sau commit
        try:
            send_reschedule_notifications(
                locked_booking, old_date, old_time, previous_appointment=old_appointment
            )
        except Exception:
            logger.exception('send_reschedule_notifications failed for booking %s', locked_booking.id)

        notify_doctor(
            locked_booking,
            title='Bệnh nhân vừa đổi lịch',
            message=f'{locked_booking.full_name} đã đổi sang {_fmt_dt(locked_booking.date, locked_booking.time)}.',
            level='warning',
        )

        # Nếu chuyển sang bác sĩ khác -> báo cho bác sĩ cũ
        if old_appointment.user_id != locked_booking.appointment.user_id:
            _safe_push(
                old_appointment.user,
                title='Bệnh nhân đã chuyển sang lịch khác',
                message=(
                    f'{locked_booking.full_name} không còn ở lịch khám của bạn '
                    f'lúc {_fmt_dt(old_date, old_time)}.'
                ),
                level='warning',
                category='appointment',
                link=reverse('doctor-dashboard'),
                payload={'booking_id': locked_booking.id, 'status': locked_booking.status},
            )

        notify_patient(
            locked_booking,
            title='Đổi lịch thành công',
            message=f'Lịch khám của bạn đã chuyển sang {_fmt_dt(locked_booking.date, locked_booking.time)}.',
            level='success',
        )
        return locked_booking, None

    # --- Hủy lịch (do bệnh nhân) ---
    @staticmethod
    def cancel_by_patient(*, booking, reason, changed_by):
        return BookingService._cancel(
            booking=booking,
            reason=reason,
            changed_by=changed_by,
            cancelled_by='patient',
            patient_notification={
                'title': 'Bạn đã hủy lịch khám',
                'message_tpl': 'Lịch khám {dt} đã được hủy.',
                'level': 'info',
            },
            doctor_notification={
                'title': 'Bệnh nhân vừa hủy lịch',
                'message_tpl': '{name} đã hủy lịch khám {dt}.',
                'level': 'warning',
            },
        )

    # --- Hủy lịch (do bác sĩ - thao tác trên 1 booking) ---
    @staticmethod
    def cancel_by_doctor(*, booking, reason, changed_by):
        return BookingService._cancel(
            booking=booking,
            reason=reason,
            changed_by=changed_by,
            cancelled_by='doctor',
            patient_notification={
                'title': 'Bác sĩ đã hủy lịch khám',
                'message_tpl': (
                    'Lịch khám {dt} đã bị bác sĩ hủy. Vui lòng đặt lịch mới.'
                ),
                'level': 'danger',
            },
            doctor_notification=None,
        )

    @staticmethod
    def _cancel(*, booking, reason, changed_by, cancelled_by, patient_notification, doctor_notification):
        with transaction.atomic():
            locked = (
                TakeAppointment.objects.select_for_update()
                .select_related('appointment', 'appointment__user')
                .get(pk=booking.pk)
            )
            if cancelled_by == 'patient':
                can_modify, msg = booking_can_be_modified(locked)
                if not can_modify:
                    return None, msg
            locked.status = TakeAppointment.STATUS_CANCELLED
            locked.cancelled_at = timezone.now()
            locked.notification_version += 1
            locked.save(update_fields=['status', 'cancelled_at', 'notification_version'])

            create_change_log(
                locked,
                AppointmentChangeLog.ACTION_CANCELLED,
                changed_by=changed_by,
                reason=reason,
                old_appointment=locked.appointment,
                old_date=locked.date,
                old_time=locked.time,
            )

        try:
            send_cancellation_notifications(locked, cancelled_by=cancelled_by)
        except Exception:
            logger.exception('send_cancellation_notifications failed for booking %s', locked.id)

        dt = _fmt_dt(locked.date, locked.time)
        if doctor_notification:
            notify_doctor(
                locked,
                title=doctor_notification['title'],
                message=doctor_notification['message_tpl'].format(name=locked.full_name, dt=dt),
                level=doctor_notification['level'],
            )
        if patient_notification:
            notify_patient(
                locked,
                title=patient_notification['title'],
                message=patient_notification['message_tpl'].format(dt=dt),
                level=patient_notification['level'],
            )
        return locked, None

    # --- Hủy nhiều booking khi xóa cả khung giờ khám của bác sĩ ---
    @staticmethod
    def cancel_all_for_appointment(*, appointment, changed_by):
        """Hủy hàng loạt khi bác sĩ xóa cả khung giờ khám đã đăng."""
        with transaction.atomic():
            active_bookings = list(
                TakeAppointment.objects.select_for_update()
                .filter(appointment=appointment, status__in=TakeAppointment.ACTIVE_STATUSES)
                .select_related('appointment', 'appointment__user')
            )
            for booking in active_bookings:
                booking.status = TakeAppointment.STATUS_CANCELLED
                booking.cancelled_at = timezone.now()
                booking.notification_version += 1
                booking.save(update_fields=['status', 'cancelled_at', 'notification_version'])
                create_change_log(
                    booking,
                    AppointmentChangeLog.ACTION_CANCELLED,
                    changed_by=changed_by,
                    reason='Bác sĩ xóa ca khám đã đăng.',
                    old_appointment=booking.appointment,
                    old_date=booking.date,
                    old_time=booking.time,
                )
            appointment.is_active = False
            appointment.save(update_fields=['is_active'])

        for booking in active_bookings:
            try:
                send_cancellation_notifications(booking, cancelled_by='doctor')
            except Exception:
                logger.exception(
                    'send_cancellation_notifications failed for booking %s', booking.id
                )
            notify_patient(
                booking,
                title='Ca khám đã bị hủy',
                message=(
                    f'Lịch với bác sĩ {booking.appointment.full_name} '
                    f'{_fmt_dt(booking.date, booking.time)} đã bị hủy.'
                ),
                level='danger',
            )
        return active_bookings
