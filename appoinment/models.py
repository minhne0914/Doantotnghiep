from django.db import models
from django.utils import timezone

from accounts.models import User

department = (
    ('Heart Disease', "Heart Disease"),
    ('Diabetes Disease', "Diabetes Disease"),
    ('Breast Cancer', "Breast Cancer"),
    ('Dentistry', "Dentistry"),
    ('Cardiology', "Cardiology"),
    ('ENT Specialists', "ENT Specialists"),
    ('Astrology', 'Astrology'),
    ('Neuroanatomy', 'Neuroanatomy'),
    ('Blood Screening', 'Blood Screening'),
    ('Eye Care', 'Eye Care'),
    ('Physical Therapy', 'Physical Therapy'),
)


class Appointment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    image = models.ImageField(null=True, blank=True, default='avatar.png', upload_to='avatars/')
    location = models.CharField(max_length=100)
    qualification_name = models.CharField(max_length=100)
    institute_name = models.CharField(max_length=100)
    hospital_name = models.CharField(max_length=100)
    department = models.CharField(choices=department, max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    date = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.full_name


class TakeAppointment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_ARRIVED = 'arrived'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_ARRIVED, 'Arrived'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    )

    ACTIVE_STATUSES = (STATUS_PENDING, STATUS_CONFIRMED, STATUS_ARRIVED)
    MODIFIABLE_STATUSES = (STATUS_PENDING, STATUS_CONFIRMED)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    message = models.TextField()
    phone_number = models.CharField(max_length=120)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    notification_version = models.PositiveIntegerField(default=1)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.full_name


class AppointmentChangeLog(models.Model):
    ACTION_BOOKED = 'booked'
    ACTION_RESCHEDULED = 'rescheduled'
    ACTION_CANCELLED = 'cancelled'

    ACTION_CHOICES = (
        (ACTION_BOOKED, 'Booked'),
        (ACTION_RESCHEDULED, 'Rescheduled'),
        (ACTION_CANCELLED, 'Cancelled'),
    )

    booking = models.ForeignKey(TakeAppointment, on_delete=models.CASCADE, related_name='change_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointment_change_logs')
    old_appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='old_change_logs')
    new_appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_change_logs')
    old_date = models.DateField(null=True, blank=True)
    old_time = models.TimeField(null=True, blank=True)
    new_date = models.DateField(null=True, blank=True)
    new_time = models.TimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - booking #{self.booking_id}"
