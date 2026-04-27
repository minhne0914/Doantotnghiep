from django.contrib import admin
from .models import Appointment, TakeAppointment, AppointmentChangeLog, DoctorReview, DirectMessage

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'department', 'date', 'start_time', 'end_time', 'hospital_name', 'is_active')
    list_filter = ('department', 'date', 'is_active')
    search_fields = ('full_name', 'department', 'hospital_name')
    ordering = ('-date', '-start_time')

@admin.register(TakeAppointment)
class TakeAppointmentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'doctor_name', 'date', 'time', 'status')
    list_filter = ('status', 'date')
    search_fields = ('full_name', 'phone_number', 'appointment__full_name')
    ordering = ('-date', '-time')
    
    def doctor_name(self, obj):
        return obj.appointment.full_name
    doctor_name.short_description = 'Bác sĩ'

@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = ('doctor_name', 'patient_name', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('doctor__first_name', 'patient__first_name', 'comment')
    
    def doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}"
    doctor_name.short_description = 'Bác sĩ'
    
    def patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    patient_name.short_description = 'Bệnh nhân'

@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ('sender_name', 'booking_id', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__email', 'content')
    
    def sender_name(self, obj):
        return obj.sender.email
    sender_name.short_description = 'Người gửi'

@admin.register(AppointmentChangeLog)
class AppointmentChangeLogAdmin(admin.ModelAdmin):
    list_display = ('booking', 'action', 'changed_by', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('booking__full_name', 'reason')