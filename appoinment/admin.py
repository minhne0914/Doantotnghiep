"""Admin cho appoinment app: lịch khám, booking, review, chat, audit log."""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Appointment,
    TakeAppointment,
    AppointmentChangeLog,
    DoctorReview,
    DirectMessage,
)


# =============================================================================
# Appointment (slot khám của bác sĩ)
# =============================================================================

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'doctor_name', 'department_label', 'date', 'time_range',
        'hospital_name', 'is_active_badge',
    )
    list_filter = ('department', 'date', 'is_active', 'created_at')
    search_fields = ('full_name', 'department', 'hospital_name', 'location', 'user__email')
    list_select_related = ('user',)
    list_per_page = 25
    date_hierarchy = 'date'
    ordering = ('-date', '-start_time')

    fieldsets = (
        ('Bác sĩ', {'fields': ('user', 'full_name', 'qualification_name', 'image')}),
        ('Chuyên khoa & cơ sở', {'fields': ('department', 'institute_name', 'hospital_name', 'location')}),
        ('Thời gian', {'fields': ('date', ('start_time', 'end_time'))}),
        ('Trạng thái', {'fields': ('is_active',)}),
    )

    actions = ['activate_slots', 'deactivate_slots']

    def doctor_name(self, obj):
        return obj.full_name or obj.user.email
    doctor_name.short_description = 'Bác sĩ'

    def department_label(self, obj):
        return obj.department or '—'
    department_label.short_description = 'Khoa'

    def time_range(self, obj):
        return f'{obj.start_time.strftime("%H:%M")} - {obj.end_time.strftime("%H:%M")}'
    time_range.short_description = 'Khung giờ'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#16a34a;color:#fff;padding:2px 8px;'
                'border-radius:6px;font-size:11px">Hoạt động</span>'
            )
        return format_html(
            '<span style="background:#9ca3af;color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px">Đã ẩn</span>'
        )
    is_active_badge.short_description = 'Trạng thái'

    @admin.action(description='Kích hoạt slot đã chọn')
    def activate_slots(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f'Đã kích hoạt {n} slot.')

    @admin.action(description='Vô hiệu hóa slot đã chọn')
    def deactivate_slots(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f'Đã ẩn {n} slot.')


# =============================================================================
# TakeAppointment (booking của bệnh nhân)
# =============================================================================

@admin.register(TakeAppointment)
class TakeAppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'patient_name', 'doctor_name', 'date', 'time',
        'status_badge', 'phone_number', 'has_emr',
    )
    list_filter = ('status', 'date', 'created_at')
    search_fields = (
        'full_name', 'phone_number', 'message',
        'appointment__full_name', 'user__email',
    )
    list_select_related = ('appointment', 'appointment__user', 'user')
    list_per_page = 25
    date_hierarchy = 'date'
    ordering = ('-date', '-time')

    fieldsets = (
        ('Liên kết', {'fields': ('user', 'appointment')}),
        ('Bệnh nhân', {'fields': ('full_name', 'phone_number', 'message')}),
        ('Thời gian', {'fields': (('date', 'time'),)}),
        ('Trạng thái', {'fields': ('status', 'cancelled_at', 'notification_version')}),
    )

    readonly_fields = ('notification_version', 'cancelled_at', 'created_at')

    actions = [
        'mark_confirmed', 'mark_arrived', 'mark_completed', 'mark_cancelled',
    ]

    def patient_name(self, obj):
        return obj.full_name
    patient_name.short_description = 'Bệnh nhân'

    def doctor_name(self, obj):
        return obj.appointment.full_name
    doctor_name.short_description = 'Bác sĩ'

    def status_badge(self, obj):
        colors = {
            'pending':   ('#f59e0b', 'Chờ xác nhận'),
            'confirmed': ('#16a34a', 'Đã xác nhận'),
            'arrived':   ('#3b82f6', 'Đang khám'),
            'completed': ('#6366f1', 'Hoàn thành'),
            'cancelled': ('#9ca3af', 'Đã hủy'),
        }
        color, label = colors.get(obj.status, ('#6b7280', obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:bold">{}</span>',
            color, label,
        )
    status_badge.short_description = 'Trạng thái'

    def has_emr(self, obj):
        return hasattr(obj, 'emr_record')
    has_emr.short_description = 'Có EMR?'
    has_emr.boolean = True

    @admin.action(description='Xác nhận booking đã chọn (→ Confirmed)')
    def mark_confirmed(self, request, queryset):
        n = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'Đã xác nhận {n} booking.')

    @admin.action(description='Đánh dấu đã đến (→ Arrived)')
    def mark_arrived(self, request, queryset):
        n = queryset.filter(status__in=('pending', 'confirmed')).update(status='arrived')
        self.message_user(request, f'Đã đánh dấu {n} booking là đã đến.')

    @admin.action(description='Đánh dấu hoàn thành (→ Completed)')
    def mark_completed(self, request, queryset):
        n = queryset.exclude(status='cancelled').update(status='completed')
        self.message_user(request, f'Đã hoàn thành {n} booking.')

    @admin.action(description='Hủy booking đã chọn (→ Cancelled)')
    def mark_cancelled(self, request, queryset):
        from django.utils import timezone
        n = queryset.exclude(status='cancelled').update(
            status='cancelled', cancelled_at=timezone.now(),
        )
        self.message_user(request, f'Đã hủy {n} booking.')


# =============================================================================
# DoctorReview (đánh giá)
# =============================================================================

@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor_label', 'patient_label', 'rating_stars', 'short_comment', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = (
        'doctor__email', 'doctor__first_name', 'doctor__last_name',
        'patient__email', 'patient__first_name', 'patient__last_name',
        'comment',
    )
    list_select_related = ('doctor', 'patient', 'booking')
    list_per_page = 25
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

    def doctor_label(self, obj):
        return f'BS. {obj.doctor.first_name} {obj.doctor.last_name}'.strip() or obj.doctor.email
    doctor_label.short_description = 'Bác sĩ'

    def patient_label(self, obj):
        return f'{obj.patient.first_name} {obj.patient.last_name}'.strip() or obj.patient.email
    patient_label.short_description = 'Bệnh nhân'

    def rating_stars(self, obj):
        full = '★' * obj.rating
        empty = '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color:#f59e0b;font-size:14px">{}{}</span>',
            full, empty,
        )
    rating_stars.short_description = 'Đánh giá'

    def short_comment(self, obj):
        if not obj.comment:
            return '—'
        return (obj.comment[:60] + '...') if len(obj.comment) > 60 else obj.comment
    short_comment.short_description = 'Nhận xét'


# =============================================================================
# DirectMessage (chat) - read-only audit
# =============================================================================

@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender_email', 'booking_id', 'short_content', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__email', 'content', 'booking__full_name')
    list_select_related = ('sender', 'booking')
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = ('booking', 'sender', 'content', 'attachments', 'created_at')

    def sender_email(self, obj):
        return obj.sender.email
    sender_email.short_description = 'Người gửi'

    def short_content(self, obj):
        return (obj.content[:60] + '...') if len(obj.content) > 60 else obj.content
    short_content.short_description = 'Nội dung'

    def has_add_permission(self, request):
        return False  # Tin nhắn chỉ được tạo qua chat UI


# =============================================================================
# AppointmentChangeLog (audit) - hoàn toàn read-only
# =============================================================================

@admin.register(AppointmentChangeLog)
class AppointmentChangeLogAdmin(admin.ModelAdmin):
    """Audit trail - cấm sửa, cấm xóa, chỉ xem."""

    list_display = ('id', 'booking', 'action_badge', 'changed_by_email', 'old_slot', 'new_slot', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('booking__full_name', 'reason', 'changed_by__email')
    list_select_related = ('booking', 'changed_by', 'old_appointment', 'new_appointment')
    list_per_page = 50
    date_hierarchy = 'created_at'

    readonly_fields = (
        'booking', 'action', 'changed_by',
        'old_appointment', 'new_appointment',
        'old_date', 'old_time', 'new_date', 'new_time',
        'reason', 'created_at',
    )

    def action_badge(self, obj):
        colors = {
            'booked':      ('#16a34a', 'Đặt mới'),
            'rescheduled': ('#3b82f6', 'Đổi lịch'),
            'cancelled':   ('#dc2626', 'Hủy'),
        }
        color, label = colors.get(obj.action, ('#6b7280', obj.action))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px">{}</span>',
            color, label,
        )
    action_badge.short_description = 'Hành động'

    def changed_by_email(self, obj):
        return obj.changed_by.email if obj.changed_by else '—'
    changed_by_email.short_description = 'Người thực hiện'

    def old_slot(self, obj):
        if obj.old_date and obj.old_time:
            return f'{obj.old_time.strftime("%H:%M")} {obj.old_date.strftime("%d/%m/%Y")}'
        return '—'
    old_slot.short_description = 'Slot cũ'

    def new_slot(self, obj):
        if obj.new_date and obj.new_time:
            return f'{obj.new_time.strftime("%H:%M")} {obj.new_date.strftime("%d/%m/%Y")}'
        return '—'
    new_slot.short_description = 'Slot mới'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
