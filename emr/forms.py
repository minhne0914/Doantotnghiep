from django import forms
from django.forms import inlineformset_factory

from .models import EMRRecord, PrescriptionItem, VitalSign


class EMRRecordForm(forms.ModelForm):
    class Meta:
        model = EMRRecord
        fields = ['symptoms', 'diagnosis', 'clinical_notes', 'follow_up_plan']
        labels = {
            'symptoms': 'Triệu chứng',
            'diagnosis': 'Chẩn đoán',
            'clinical_notes': 'Ghi chú lâm sàng',
            'follow_up_plan': 'Kế hoạch theo dõi',
        }
        widgets = {
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Triệu chứng bệnh nhân mô tả hoặc bác sĩ ghi nhận'}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Chẩn đoán sau khám'}),
            'clinical_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ghi chú lâm sàng, cận lâm sàng, đánh giá thêm'}),
            'follow_up_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dặn dò tái khám, theo dõi thêm nếu cần'}),
        }


class VitalSignForm(forms.ModelForm):
    class Meta:
        model = VitalSign
        fields = [
            'weight_kg',
            'height_cm',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'heart_rate',
            'temperature_c',
        ]
        labels = {
            'weight_kg': 'Cân nặng (kg)',
            'height_cm': 'Chiều cao (cm)',
            'blood_pressure_systolic': 'Huyết áp tâm thu',
            'blood_pressure_diastolic': 'Huyết áp tâm trương',
            'heart_rate': 'Nhịp tim',
            'temperature_c': 'Nhiệt độ (°C)',
        }
        widgets = {
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'blood_pressure_systolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'blood_pressure_diastolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature_c': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }


class PrescriptionItemForm(forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['medicine_name', 'dosage', 'frequency', 'duration', 'instructions', 'order']
        labels = {
            'medicine_name': 'Tên thuốc',
            'dosage': 'Liều lượng',
            'frequency': 'Tần suất dùng',
            'duration': 'Thời gian dùng',
            'instructions': 'Hướng dẫn',
            'order': 'Thứ tự',
        }
        widgets = {
            'medicine_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên thuốc'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Liều lượng'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tần suất dùng'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Thời gian dùng'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Hướng dẫn sử dụng'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


PrescriptionFormSet = inlineformset_factory(
    EMRRecord,
    PrescriptionItem,
    form=PrescriptionItemForm,
    extra=3,
    can_delete=True,
)
