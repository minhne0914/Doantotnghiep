"""Admin cho notifications app: log gửi email/SMS, preference, realtime."""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AppointmentNotificationLog,
    NotificationPreference,
    RealtimeNotification,
)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user_email', 'email_enabled', 'sms_enabled', 'realtime_enabled',
        'reminder_24h_enabled', 'reminder_1h_enabled', 'booking_updates_enabled',
    )
    list_filter = (
        'email_enabled', 'sms_enabled', 'realtime_enabled',
        'reminder_24h_enabled', 'booking_updates_enabled',
    )
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    list_select_related = ('user',)
    list_per_page = 25

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Người dùng'


@admin.register(AppointmentNotificationLog)
class AppointmentNotificationLogAdmin(admin.ModelAdmin):
    """Log gửi email/SMS cho từng booking - đây là audit data, KHÔNG nên sửa."""

    list_display = (
        'id', 'event_label', 'channel_badge', 'recipient_email',
        'status_badge', 'scheduled_for', 'sent_at',
    )
    list_filter = ('event', 'channel', 'status', 'created_at')
    search_fields = (
        'recipient__email', 'appointment__full_name',
        'provider_message_id', 'error_message',
    )
    list_select_related = ('recipient', 'appointment')
    list_per_page = 50
    date_hierarchy = 'created_at'

    # Audit data - readonly tất cả
    readonly_fields = (
        'appointment', 'recipient', 'channel', 'event', 'status',
        'booking_version', 'provider_message_id', 'error_message',
        'scheduled_for', 'sent_at', 'created_at',
    )

    actions = ['mark_skipped']

    def event_label(self, obj):
        return obj.get_event_display()
    event_label.short_description = 'Sự kiện'

    def channel_badge(self, obj):
        colors = {'email': '#3b82f6', 'sms': '#8b5cf6'}
        color = colors.get(obj.channel, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px">{}</span>',
            color, obj.channel.upper(),
        )
    channel_badge.short_description = 'Kênh'

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'sent': '#16a34a',
            'failed': '#dc2626',
            'skipped': '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = 'Trạng thái'

    def recipient_email(self, obj):
        return obj.recipient.email
    recipient_email.short_description = 'Người nhận'

    def has_add_permission(self, request):
        # Audit log không nên thêm thủ công
        return False

    def has_delete_permission(self, request, obj=None):
        # Audit log không nên xóa
        return False

    @admin.action(description='Đánh dấu là đã bỏ qua')
    def mark_skipped(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='skipped')
        self.message_user(request, f'Đã bỏ qua {updated} thông báo.')


@admin.register(RealtimeNotification)
class RealtimeNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'level_badge', 'category', 'short_title', 'created_at',
    )
    list_filter = ('level', 'category', 'created_at')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'title', 'message', 'category',
    )
    list_select_related = ('user',)
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Người nhận'

    def short_title(self, obj):
        return (obj.title[:50] + '...') if len(obj.title) > 50 else obj.title
    short_title.short_description = 'Tiêu đề'

    def level_badge(self, obj):
        colors = {
            'info': '#3b82f6',
            'success': '#16a34a',
            'warning': '#f59e0b',
            'danger': '#dc2626',
        }
        color = colors.get(obj.level, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px">{}</span>',
            color, obj.get_level_display(),
        )
    level_badge.short_description = 'Mức độ'
