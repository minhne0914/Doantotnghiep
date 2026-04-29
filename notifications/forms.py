from django import forms

from .models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled',
            'sms_enabled',
            'realtime_enabled',
            'reminder_24h_enabled',
            'reminder_1h_enabled',
            'booking_updates_enabled',
        ]
        labels = {
            'email_enabled': 'Nhận email',
            'sms_enabled': 'Nhận SMS',
            'realtime_enabled': 'Nhận thông báo trực tuyến',
            'reminder_24h_enabled': 'Nhắc lịch trước 24 giờ',
            'reminder_1h_enabled': 'Nhắc lịch trước 1 giờ',
            'booking_updates_enabled': 'Nhận thông báo khi lịch bị hủy hoặc đổi',
        }
