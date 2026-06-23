"""Administrative supervision screens for electronic medical records."""

from django.contrib import admin
from django.utils.html import format_html

from .models import EMRRecord, PrescriptionItem, VitalSign


class ReadOnlyClinicalInline:
    """Prevent non-clinical staff from changing doctor-authored medical data."""

    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class VitalSignInline(ReadOnlyClinicalInline, admin.StackedInline):
    model = VitalSign
    readonly_fields = (
        'weight_kg', 'height_cm', 'blood_pressure_systolic',
        'blood_pressure_diastolic', 'heart_rate', 'temperature_c',
    )
    fieldsets = (
        ('The trang', {'fields': (('weight_kg', 'height_cm'),)}),
        ('Huyet ap', {'fields': (('blood_pressure_systolic', 'blood_pressure_diastolic'),)}),
        ('Sinh hieu khac', {'fields': (('heart_rate', 'temperature_c'),)}),
    )


class PrescriptionItemInline(ReadOnlyClinicalInline, admin.TabularInline):
    model = PrescriptionItem
    readonly_fields = (
        'order', 'medicine_name', 'dosage', 'frequency', 'duration', 'instructions',
    )
    fields = readonly_fields


class ReadOnlyClinicalAdmin(admin.ModelAdmin):
    """Allow administrators to audit medical data without editing it."""

    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        context = {
            'show_save': False,
            'show_save_and_add_another': False,
            'show_save_and_continue': False,
            'show_delete': False,
        }
        if extra_context:
            context.update(extra_context)
        return super().changeform_view(request, object_id, form_url, context)


@admin.register(EMRRecord)
class EMRRecordAdmin(ReadOnlyClinicalAdmin):
    list_display = (
        'record_code', 'patient_details', 'doctor_details', 'appointment_schedule',
        'short_diagnosis', 'prescription_status', 'created_at',
    )
    list_display_links = ('record_code',)
    list_filter = ('appointment__appointment__department', 'created_at', 'updated_at')
    search_fields = (
        'patient__email', 'patient__first_name', 'patient__last_name',
        'doctor__email', 'doctor__first_name', 'doctor__last_name',
        'diagnosis', 'symptoms',
    )
    search_help_text = 'Tim theo ten, email benh nhan/bac si, trieu chung hoac chan doan.'
    list_select_related = ('patient', 'doctor', 'appointment')
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = (
        'appointment_summary', 'appointment', 'patient', 'doctor', 'symptoms',
        'diagnosis', 'clinical_notes', 'follow_up_plan', 'created_at', 'updated_at',
    )
    fieldsets = (
        ('Thong tin ho so', {
            'fields': ('appointment_summary', 'patient', 'doctor'),
        }),
        ('Noi dung kham lam sang', {
            'fields': ('symptoms', 'diagnosis', 'clinical_notes'),
        }),
        ('Ke hoach theo doi', {'fields': ('follow_up_plan',)}),
        ('Lich su cap nhat', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [VitalSignInline, PrescriptionItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('prescriptions')

    @admin.display(description='Ma EMR', ordering='id')
    def record_code(self, obj):
        return format_html(
            '<strong style="color:#0f766e">{}</strong>',
            f'EMR-{obj.pk:04d}',
        )

    @admin.display(description='Benh nhan', ordering='patient__first_name')
    def patient_details(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.patient.full_name, obj.patient.email,
        )

    @admin.display(description='Bac si phu trach', ordering='doctor__first_name')
    def doctor_details(self, obj):
        return format_html(
            '<strong>BS. {}</strong><br><small>{}</small>',
            obj.doctor.full_name, obj.doctor.email,
        )

    @admin.display(description='Lich kham', ordering='appointment__date')
    def appointment_schedule(self, obj):
        booking = obj.appointment
        department = booking.appointment.department or 'Chua cap nhat chuyen khoa'
        return format_html('{} {}<br><small>{}</small>', booking.date, booking.time, department)

    @admin.display(description='Chan doan')
    def short_diagnosis(self, obj):
        diagnosis = obj.diagnosis or ''
        return (diagnosis[:70] + '...') if len(diagnosis) > 70 else (diagnosis or '-')

    @admin.display(description='Don thuoc', boolean=True)
    def prescription_status(self, obj):
        return bool(obj.prescriptions.all())

    @admin.display(description='Thong tin lich kham')
    def appointment_summary(self, obj):
        booking = obj.appointment
        return format_html(
            '<strong>Ma lich #{}</strong> | {} {} | {}',
            booking.pk, booking.date, booking.time, booking.appointment.department,
        )


@admin.register(VitalSign)
class VitalSignAdmin(ReadOnlyClinicalAdmin):
    list_display = (
        'emr_record_id', 'patient_label', 'weight_kg', 'height_cm',
        'bmi_display', 'bp_display', 'heart_rate', 'temperature_c',
    )
    list_filter = ('emr_record__appointment__appointment__department', 'emr_record__created_at')
    search_fields = (
        'emr_record__patient__email', 'emr_record__patient__first_name',
        'emr_record__patient__last_name',
    )
    list_select_related = ('emr_record__patient',)
    list_per_page = 25
    readonly_fields = (
        'emr_record', 'weight_kg', 'height_cm', 'blood_pressure_systolic',
        'blood_pressure_diastolic', 'heart_rate', 'temperature_c',
    )

    @admin.display(description='Benh nhan', ordering='emr_record__patient__first_name')
    def patient_label(self, obj):
        return obj.emr_record.patient.full_name

    @admin.display(description='BMI')
    def bmi_display(self, obj):
        bmi = obj.bmi
        if bmi is None:
            return '-'
        color = '#3b82f6' if bmi < 18.5 else '#16a34a' if bmi < 25 else '#f59e0b' if bmi < 30 else '#dc2626'
        return format_html('<strong style="color:{}">{}</strong>', color, bmi)

    @admin.display(description='Huyet ap')
    def bp_display(self, obj):
        return f'{obj.blood_pressure_systolic}/{obj.blood_pressure_diastolic}'


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(ReadOnlyClinicalAdmin):
    list_display = (
        'medicine_name', 'dosage', 'frequency', 'duration', 'patient_label', 'emr_record_id',
    )
    list_filter = ('emr_record__appointment__appointment__department', 'emr_record__created_at')
    search_fields = (
        'medicine_name', 'dosage', 'instructions', 'emr_record__patient__email',
        'emr_record__patient__first_name', 'emr_record__patient__last_name',
    )
    list_select_related = ('emr_record__patient',)
    list_per_page = 50
    ordering = ('emr_record', 'order')
    readonly_fields = (
        'emr_record', 'order', 'medicine_name', 'dosage', 'frequency', 'duration', 'instructions',
    )

    @admin.display(description='Benh nhan', ordering='emr_record__patient__first_name')
    def patient_label(self, obj):
        return obj.emr_record.patient.full_name
