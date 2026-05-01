"""Admin cho EMR app: bệnh án, dấu hiệu sinh tồn, đơn thuốc.

VitalSign và PrescriptionItem được hiển thị inline trong EMRRecord
để bác sĩ có thể nhập 1 trang duy nhất.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import EMRRecord, VitalSign, PrescriptionItem


# =============================================================================
# Inline forms
# =============================================================================

class VitalSignInline(admin.StackedInline):
    """Hiển thị VitalSign INLINE trong EMRRecord (1-1)."""
    model = VitalSign
    extra = 0
    can_delete = False
    fieldsets = (
        ('Thể trạng', {'fields': (('weight_kg', 'height_cm'),)}),
        ('Huyết áp', {'fields': (('blood_pressure_systolic', 'blood_pressure_diastolic'),)}),
        ('Sinh hiệu khác', {'fields': (('heart_rate', 'temperature_c'),)}),
    )


class PrescriptionItemInline(admin.TabularInline):
    """Hiển thị danh sách thuốc INLINE (1-N)."""
    model = PrescriptionItem
    extra = 1
    fields = ('order', 'medicine_name', 'dosage', 'frequency', 'duration', 'instructions')


# =============================================================================
# Standalone admin
# =============================================================================

@admin.register(EMRRecord)
class EMRRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'patient_name', 'doctor_name', 'short_diagnosis',
        'has_prescription', 'created_at',
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = (
        'patient__email', 'patient__first_name', 'patient__last_name',
        'doctor__email', 'doctor__first_name', 'doctor__last_name',
        'diagnosis', 'symptoms',
    )
    list_select_related = ('patient', 'doctor', 'appointment')
    list_per_page = 25
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Liên kết lịch khám', {'fields': ('appointment', 'patient', 'doctor')}),
        ('Khám lâm sàng', {'fields': ('symptoms', 'diagnosis', 'clinical_notes')}),
        ('Theo dõi', {'fields': ('follow_up_plan',)}),
        ('Audit', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    inlines = [VitalSignInline, PrescriptionItemInline]

    def patient_name(self, obj):
        return f'{obj.patient.first_name} {obj.patient.last_name}'.strip() or obj.patient.email
    patient_name.short_description = 'Bệnh nhân'

    def doctor_name(self, obj):
        return f'BS. {obj.doctor.first_name} {obj.doctor.last_name}'.strip()
    doctor_name.short_description = 'Bác sĩ phụ trách'

    def short_diagnosis(self, obj):
        diag = obj.diagnosis or ''
        return (diag[:60] + '...') if len(diag) > 60 else (diag or '—')
    short_diagnosis.short_description = 'Chẩn đoán'

    def has_prescription(self, obj):
        return obj.prescriptions.exists()
    has_prescription.short_description = 'Có đơn thuốc?'
    has_prescription.boolean = True


@admin.register(VitalSign)
class VitalSignAdmin(admin.ModelAdmin):
    """Standalone view cho thống kê / báo cáo - vẫn dùng được dù đã có inline."""
    list_display = (
        'emr_record_id', 'patient_label', 'weight_kg', 'height_cm',
        'bmi_display', 'bp_display', 'heart_rate', 'temperature_c',
    )
    list_filter = ('emr_record__created_at',)
    search_fields = (
        'emr_record__patient__email',
        'emr_record__patient__first_name',
        'emr_record__patient__last_name',
    )
    list_select_related = ('emr_record__patient',)
    list_per_page = 25

    def patient_label(self, obj):
        p = obj.emr_record.patient
        return f'{p.first_name} {p.last_name}'.strip() or p.email
    patient_label.short_description = 'Bệnh nhân'

    def bmi_display(self, obj):
        bmi = obj.bmi
        if bmi is None:
            return '—'
        # Color theo phân loại WHO
        if bmi < 18.5:
            color = '#3b82f6'  # underweight - blue
        elif bmi < 25:
            color = '#16a34a'  # normal - green
        elif bmi < 30:
            color = '#f59e0b'  # overweight - amber
        else:
            color = '#dc2626'  # obese - red
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color, bmi,
        )
    bmi_display.short_description = 'BMI'

    def bp_display(self, obj):
        return f'{obj.blood_pressure_systolic}/{obj.blood_pressure_diastolic}'
    bp_display.short_description = 'Huyết áp'


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'medicine_name', 'dosage', 'frequency', 'duration', 'emr_record_id')
    list_filter = ('emr_record__created_at',)
    search_fields = ('medicine_name', 'dosage', 'instructions')
    list_select_related = ('emr_record',)
    list_per_page = 50
    ordering = ('emr_record', 'order')
