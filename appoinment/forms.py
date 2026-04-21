from django import forms
from django.utils import timezone

from .models import Appointment, TakeAppointment


class CreateAppointmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].label = "Ngày khám"
        self.fields['start_time'].label = "Giờ bắt đầu"
        self.fields['end_time'].label = "Giờ kết thúc"

        self.fields['date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.fields['start_time'].widget = forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'})
        self.fields['end_time'].widget = forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'})
        self.fields['start_time'].widget.attrs.update({'placeholder': 'Ví dụ: 09:00'})
        self.fields['end_time'].widget.attrs.update({'placeholder': 'Ví dụ: 17:00'})

    class Meta:
        model = Appointment
        fields = ['date', 'start_time', 'end_time']

    def clean_date(self):
        appointment_date = self.cleaned_data['date']
        if appointment_date < timezone.localdate():
            raise forms.ValidationError("Ngày khám không được ở trong quá khứ.")
        return appointment_date

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', "Giờ kết thúc phải sau giờ bắt đầu.")
            
        if date and start_time:
            import datetime
            dt = datetime.datetime.combine(date, start_time)
            now = timezone.localtime()
            if dt < now + datetime.timedelta(hours=1):
                self.add_error('start_time', "Giờ bắt đầu quá gần. Phải tạo ca khám cho tương lai cách hiện tại ít nhất 1 tiếng đồng hồ.")

        return cleaned_data


class TakeAppointmentForm(forms.ModelForm):
    appointment = forms.ModelChoiceField(
        queryset=Appointment.objects.none(),
        empty_label="Chọn bác sĩ",
        label="Bác sĩ",
        widget=forms.Select(attrs={'class': 'form-control', 'readonly': 'readonly', 'hidden': 'hidden'}),
    )

    class Meta:
        model = TakeAppointment
        fields = ['appointment', 'full_name', 'phone_number', 'message', 'time']
        widgets = {
            'time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RescheduleAppointmentForm(forms.Form):
    appointment = forms.ModelChoiceField(
        queryset=Appointment.objects.none(),
        label='Bác sĩ / ca khám mới',
        empty_label='Chọn lịch mới',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    time = forms.TimeField(
        label='Giờ khám mới',
        widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
    )
    reason = forms.CharField(
        label='Lý do đổi lịch',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ví dụ: bận việc đột xuất, muốn đổi bác sĩ hoặc giờ khám'}),
    )
    message = forms.CharField(
        label='Ghi chú cho bác sĩ',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Cập nhật ghi chú nếu cần'}),
    )

    def __init__(self, *args, **kwargs):
        current_booking = kwargs.pop('current_booking', None)
        kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        queryset = Appointment.objects.filter(is_active=True, date__gte=timezone.localdate()).select_related('user').order_by('date', 'start_time', 'full_name')
        self.fields['appointment'].queryset = queryset
        self.fields['appointment'].label_from_instance = self.appointment_label
        self.current_booking = current_booking
        if current_booking is not None:
            self.fields['appointment'].initial = current_booking.appointment_id
            self.fields['time'].initial = current_booking.time
            self.fields['message'].initial = current_booking.message

    def clean(self):
        cleaned_data = super().clean()
        appointment = cleaned_data.get('appointment')
        selected_time = cleaned_data.get('time')
        if appointment and selected_time:
            if appointment.date < timezone.localdate():
                self.add_error('appointment', 'Chỉ có thể đổi sang lịch khám trong tương lai.')
            if appointment.date == timezone.localdate() and selected_time <= timezone.localtime().time():
                self.add_error('time', 'Giờ mới phải lớn hơn thời điểm hiện tại.')
            if not (appointment.start_time <= selected_time <= appointment.end_time):
                self.add_error('time', 'Giờ mới phải nằm trong khung khám của bác sĩ.')
        return cleaned_data

    def appointment_label(self, appointment):
        return f"{appointment.full_name} - {appointment.department} - {appointment.date.strftime('%d/%m/%Y')} ({appointment.start_time.strftime('%H:%M')} - {appointment.end_time.strftime('%H:%M')})"


class CancellationAppointmentForm(forms.Form):
    reason = forms.CharField(
        label='Lý do hủy lịch',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ví dụ: thay đổi kế hoạch cá nhân, đã khám ở nơi khác'}),
    )


class DoctorReviewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].label = "Đánh giá sao"
        self.fields['rating'].widget.attrs.update({'class': 'form-control'})
        self.fields['comment'].label = "Nhận xét của bạn"
        self.fields['comment'].widget.attrs.update({'class': 'form-control', 'rows': 4, 'placeholder': 'Viết trải nghiệm của bạn với bác sĩ...'})

    class Meta:
        from .models import DoctorReview
        model = DoctorReview
        fields = ['rating', 'comment']
