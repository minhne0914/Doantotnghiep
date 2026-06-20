"""Admin cho appoinment app: lịch khám, booking, review, chat, audit log."""

import datetime

from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from accounts.models import User, UserRole

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
    class BaseAppointmentAdminForm(forms.ModelForm):
        class Meta:
            model = Appointment
            fields = '__all__'
            widgets = {
                'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                'start_time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
                'end_time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            }
            labels = {
                'user': 'Bác sĩ',
                'date': 'Ngày khám',
                'start_time': 'Giờ bắt đầu',
                'end_time': 'Giờ kết thúc',
                'hospital_name': 'Cơ sở khám',
                'location': 'Địa chỉ khám',
                'is_active': 'Cho phép bệnh nhân đặt lịch',
            }

    class AppointmentAdminForm(BaseAppointmentAdminForm):
        def clean(self):
            cleaned_data = super().clean()
            doctor = cleaned_data.get('user')
            date = cleaned_data.get('date')
            start_time = cleaned_data.get('start_time')
            end_time = cleaned_data.get('end_time')

            if start_time and end_time and end_time <= start_time:
                self.add_error('end_time', 'Giờ kết thúc phải sau giờ bắt đầu.')
                return cleaned_data

            if (
                cleaned_data.get('is_active', True)
                and doctor
                and date
                and start_time
                and end_time
            ):
                overlapping_shifts = Appointment.objects.filter(
                    user=doctor,
                    is_active=True,
                    date=date,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                )
                if self.instance.pk:
                    overlapping_shifts = overlapping_shifts.exclude(pk=self.instance.pk)
                if overlapping_shifts.exists():
                    self.add_error(
                        'start_time',
                        'Khung giờ này đang chồng với một ca làm việc đã có của bác sĩ.',
                    )
            return cleaned_data

    form = AppointmentAdminForm
    change_form_template = 'admin/appoinment/appointment/change_form.html'
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
        ('Thong tin lich kham', {
            'fields': (
                'user',
                'date',
                ('start_time', 'end_time'),
                'hospital_name',
                'location',
                'is_active',
            ),
        }),
    )

    actions = ['activate_slots', 'deactivate_slots']

    def get_fieldsets(self, request, obj=None):
        return (
            ('Thong tin lich kham', {
                'fields': (
                    'user',
                    'date',
                    ('start_time', 'end_time'),
                    'hospital_name',
                    'location',
                    'is_active',
                ),
            }),
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = (
                db_field.remote_field.model.objects
                .filter(role=UserRole.DOCTOR)
                .order_by('first_name', 'last_name', 'email')
            )
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

            def doctor_label(user):
                return f'BS. {user.full_name} — {user.email}'

            formfield.label_from_instance = doctor_label
            return formfield
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        doctor = obj.user
        profile = getattr(doctor, 'doctor_profile', None)

        obj.full_name = doctor.full_name
        obj.image = doctor.image
        obj.department = getattr(profile, 'specialization', None) or obj.department or 'Cardiology'
        obj.qualification_name = (
            getattr(profile, 'qualifications', None)
            or obj.qualification_name
            or 'Doctor'
        )[:100]
        obj.institute_name = (
            getattr(profile, 'biography', None)
            or getattr(profile, 'experience', None)
            or obj.institute_name
            or 'Medic'
        )[:100]

        super().save_model(request, obj, form, change)

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

class TakeAppointmentSlotSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, 'instance', None)
        if instance is not None:
            option['attrs']['data-doctor'] = str(instance.user_id)
            option['attrs']['data-date'] = instance.date.isoformat()
            option['attrs']['data-start'] = instance.start_time.strftime('%H:%M')
            option['attrs']['data-end'] = instance.end_time.strftime('%H:%M')
            option['attrs']['data-place'] = instance.hospital_name
        return option


@admin.register(TakeAppointment)
class TakeAppointmentAdmin(admin.ModelAdmin):
    SLOT_STEP_MINUTES = 30

    class TakeAppointmentAdminForm(forms.ModelForm):
        SLOT_STEP_MINUTES = 30

        doctor = forms.ModelChoiceField(
            queryset=User.objects.none(),
            required=True,
            label='Bac si',
        )

        class Meta:
            model = TakeAppointment
            fields = (
                'user',
                'doctor',
                'appointment',
                'message',
                'date',
                'time',
                'status',
                'cancelled_at',
                'notification_version',
            )
            widgets = {
                'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                'time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
                'appointment': TakeAppointmentSlotSelect,
            }
            labels = {
                'user': 'Bệnh nhân',
                'appointment': 'Lịch bác sĩ',
                'full_name': 'Tên bệnh nhân',
                'phone_number': 'Số điện thoại',
                'message': 'Ghi chú',
                'date': 'Ngày khám',
                'time': 'Giờ khám',
                'status': 'Trạng thái',
                'cancelled_at': 'Thời điểm hủy',
                'notification_version': 'Phiên bản thông báo',
            }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            user_model = self.fields['user'].queryset.model
            open_appointments = (
                Appointment.objects
                .filter(is_active=True, date__gte=timezone.localdate())
                .select_related('user')
                .order_by('date', 'start_time')
            )
            doctor_ids_with_slots = open_appointments.values_list('user_id', flat=True).distinct()
            self.fields['doctor'].queryset = (
                user_model.objects
                .filter(role=UserRole.DOCTOR, id__in=doctor_ids_with_slots)
                .order_by('first_name', 'last_name', 'email')
            )
            self.fields['doctor'].label_from_instance = (
                lambda user: f'BS. {user.full_name} - {user.email}'
            )
            self.fields['appointment'].queryset = open_appointments
            self.fields['appointment'].help_text = (
                'Chon bac si truoc de chi hien cac ca lam viec cua bac si do.'
            )
            self.fields['date'].required = False
            self.fields['time'].required = False

            appointment = self.instance.appointment if self.instance and self.instance.pk else None
            if appointment:
                self.fields['appointment'].queryset = (
                    Appointment.objects.filter(pk=appointment.pk)
                    | self.fields['appointment'].queryset
                ).distinct()
                self.fields['doctor'].initial = appointment.user_id
                self.fields['date'].initial = appointment.date
                self.fields['time'].initial = appointment.start_time

        def clean(self):
            cleaned_data = super().clean()
            doctor = cleaned_data.get('doctor')
            appointment = cleaned_data.get('appointment')
            selected_time = cleaned_data.get('time')

            if doctor and appointment and appointment.user_id != doctor.id:
                self.add_error('appointment', 'Khung gio nay khong thuoc bac si da chon.')

            if appointment:
                cleaned_data['date'] = appointment.date
                if not selected_time:
                    selected_time = appointment.start_time
                    cleaned_data['time'] = selected_time

            if appointment and selected_time:
                if not (appointment.start_time <= selected_time < appointment.end_time):
                    self.add_error(
                        'time',
                        'Gio kham phai nam trong khung gio lam viec cua bac si.',
                    )

                active_bookings = TakeAppointment.objects.filter(
                    appointment=appointment,
                    date=appointment.date,
                    status__in=TakeAppointment.ACTIVE_STATUSES,
                )
                if self.instance and self.instance.pk:
                    active_bookings = active_bookings.exclude(pk=self.instance.pk)
                selected_datetime = datetime.datetime.combine(appointment.date, selected_time)
                has_conflict = any(
                    abs((
                        datetime.datetime.combine(existing.date, existing.time)
                        - selected_datetime
                    ).total_seconds()) < self.SLOT_STEP_MINUTES * 60
                    for existing in active_bookings.only('date', 'time')
                )
                if has_conflict:
                    self.add_error(
                        'time',
                        'Khung giờ này đã có bệnh nhân đặt hoặc quá sát với ca khác. Vui lòng chọn giờ khác.',
                    )

            return cleaned_data

    form = TakeAppointmentAdminForm
    change_form_template = 'admin/appoinment/takeappointment/change_form.html'
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
        ('Thông tin đặt lịch', {
            'fields': (
                'user',
                'doctor',
                'appointment',
                'message',
                ('date', 'time'),
                'status',
                'cancelled_at',
                'notification_version',
            ),
        }),
    )

    readonly_fields = ('notification_version', 'cancelled_at', 'created_at')

    actions = [
        'mark_confirmed', 'mark_arrived', 'mark_completed', 'mark_cancelled',
    ]

    def get_fieldsets(self, request, obj=None):
        return self.fieldsets

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'doctor-slots/',
                self.admin_site.admin_view(self.doctor_slots_view),
                name='appoinment_takeappointment_doctor_slots',
            ),
        ]
        return custom_urls + urls

    def doctor_slots_view(self, request):
        doctor_id = request.GET.get('doctor')
        if not doctor_id:
            return JsonResponse({'slots': []})

        today = timezone.localdate()
        end_date = today + timezone.timedelta(days=14)
        appointments = (
            Appointment.objects
            .filter(
                user_id=doctor_id,
                is_active=True,
                date__gte=today,
                date__lte=end_date,
            )
            .select_related('user')
            .order_by('date', 'start_time')
        )
        active_bookings = (
            TakeAppointment.objects
            .filter(
                appointment_id__in=appointments.values_list('id', flat=True),
                status__in=TakeAppointment.ACTIVE_STATUSES,
            )
            .values_list('appointment_id', 'time')
        )
        booked_times_by_appointment = {}
        for appointment_id, booked_time in active_bookings:
            booked_times_by_appointment.setdefault(appointment_id, set()).add(booked_time)

        slots = []
        for appointment in appointments:
            current_dt = timezone.datetime.combine(appointment.date, appointment.start_time)
            end_dt = timezone.datetime.combine(appointment.date, appointment.end_time)
            booked_times = booked_times_by_appointment.get(appointment.id, set())

            while current_dt < end_dt:
                current_time = current_dt.time().replace(second=0, microsecond=0)
                if current_time not in booked_times:
                    slots.append({
                        'id': appointment.id,
                        'doctor_id': appointment.user_id,
                        'date': appointment.date.isoformat(),
                        'date_label': appointment.date.strftime('%d/%m/%Y'),
                        'time': current_time.strftime('%H:%M'),
                        'end': appointment.end_time.strftime('%H:%M'),
                        'place': appointment.hospital_name,
                        'location': appointment.location,
                        'label': (
                            f'{appointment.date:%d/%m/%Y} {current_time:%H:%M} - '
                            f'{appointment.hospital_name}'
                        ),
                    })
                current_dt += timezone.timedelta(minutes=self.SLOT_STEP_MINUTES)

        return JsonResponse({'slots': slots})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = (
                db_field.remote_field.model.objects
                .filter(role=UserRole.PATIENT)
                .order_by('first_name', 'last_name', 'email')
            )
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

            def patient_label(user):
                return f'{user.full_name or user.email} — {user.email}'

            formfield.label_from_instance = patient_label
            return formfield

        if db_field.name == 'appointment':
            kwargs['queryset'] = (
                Appointment.objects
                .select_related('user')
                .order_by('-date', '-start_time')
            )
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

            def appointment_label(appointment):
                return (
                    f'BS. {appointment.full_name or appointment.user.email} — '
                    f'{appointment.date:%d/%m/%Y} '
                    f'{appointment.start_time:%H:%M}-{appointment.end_time:%H:%M} — '
                    f'{appointment.hospital_name}'
                )

            formfield.label_from_instance = appointment_label
            return formfield

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        patient = obj.user
        appointment = obj.appointment

        obj.full_name = patient.full_name
        obj.phone_number = patient.phone_number or ''
        obj.date = appointment.date
        if not obj.time:
            obj.time = appointment.start_time

        super().save_model(request, obj, form, change)

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
    """Hide private doctor-patient chat from Django admin."""

    list_display = ('id', 'sender_email', 'booking_id', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__email', 'booking__full_name')
    list_select_related = ('sender', 'booking')
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = ('booking', 'sender', 'created_at')

    def sender_email(self, obj):
        return obj.sender.email
    sender_email.short_description = 'Người gửi'

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False  # Tin nhắn chỉ được tạo qua chat UI


    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

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
