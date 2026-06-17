from django import template
from django.utils import timezone

register = template.Library()


@register.simple_tag
def admin_dashboard_metrics():
    """Return lightweight admin dashboard metrics from the local database."""
    try:
        from accounts.models import User, UserRole
        from appoinment.models import DirectMessage, TakeAppointment
        from emr.models import EMRRecord
        from home.models import MedicalHistory
        from notifications.models import RealtimeNotification
    except Exception:
        return _empty_metrics()

    today = timezone.localdate()

    try:
        total_bookings = TakeAppointment.objects.count()
        status_items = []
        for status, label, tone in (
            (TakeAppointment.STATUS_PENDING, 'Chờ xác nhận', 'warning'),
            (TakeAppointment.STATUS_CONFIRMED, 'Đã xác nhận', 'info'),
            (TakeAppointment.STATUS_ARRIVED, 'Đang khám', 'primary'),
            (TakeAppointment.STATUS_COMPLETED, 'Hoàn thành', 'success'),
            (TakeAppointment.STATUS_CANCELLED, 'Đã hủy', 'secondary'),
        ):
            count = TakeAppointment.objects.filter(status=status).count()
            status_items.append({
                'label': label,
                'count': count,
                'tone': tone,
                'percent': round((count / total_bookings) * 100) if total_bookings else 0,
            })

        doctors = User.objects.filter(role=UserRole.DOCTOR).count()
        patients = User.objects.filter(role=UserRole.PATIENT).count()
        today_bookings = TakeAppointment.objects.filter(date=today).count()
        open_bookings = TakeAppointment.objects.filter(
            status__in=[
                TakeAppointment.STATUS_PENDING,
                TakeAppointment.STATUS_CONFIRMED,
                TakeAppointment.STATUS_ARRIVED,
            ]
        ).count()

        return {
            'stats': [
                {
                    'label': 'Người dùng',
                    'value': User.objects.count(),
                    'caption': f'{doctors} bác sĩ / {patients} bệnh nhân',
                    'icon': 'fas fa-users',
                    'tone': 'blue',
                },
                {
                    'label': 'Lịch hẹn hôm nay',
                    'value': today_bookings,
                    'caption': f'{open_bookings} lịch đang cần theo dõi',
                    'icon': 'fas fa-calendar-day',
                    'tone': 'teal',
                },
                {
                    'label': 'Hồ sơ bệnh án',
                    'value': EMRRecord.objects.count(),
                    'caption': f'{MedicalHistory.objects.count()} lượt sàng lọc AI',
                    'icon': 'fas fa-file-medical',
                    'tone': 'green',
                },
                {
                    'label': 'Tin nhắn chưa đọc',
                    'value': DirectMessage.objects.filter(is_read=False).count(),
                    'caption': f'{RealtimeNotification.objects.count()} thông báo realtime',
                    'icon': 'fas fa-comments',
                    'tone': 'amber',
                },
            ],
            'status_items': status_items,
            'summary': {
                'doctors': doctors,
                'patients': patients,
                'total_bookings': total_bookings,
                'completed': TakeAppointment.objects.filter(
                    status=TakeAppointment.STATUS_COMPLETED
                ).count(),
            },
        }
    except Exception:
        return _empty_metrics()


def _empty_metrics():
    return {
        'stats': [],
        'status_items': [],
        'summary': {
            'doctors': 0,
            'patients': 0,
            'total_bookings': 0,
            'completed': 0,
        },
    }
