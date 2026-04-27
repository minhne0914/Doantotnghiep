from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from appoinment.models import TakeAppointment


class EMRRecord(models.Model):
    appointment = models.OneToOneField(TakeAppointment, on_delete=models.CASCADE, related_name='emr_record')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_emr_records')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_emr_records')
    symptoms = models.TextField()
    diagnosis = models.TextField()
    clinical_notes = models.TextField(blank=True)
    follow_up_plan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"EMR #{self.pk} - {self.patient.email}"


class VitalSign(models.Model):
    emr_record = models.OneToOneField(EMRRecord, on_delete=models.CASCADE, related_name='vital_sign')
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    blood_pressure_systolic = models.PositiveIntegerField(validators=[MinValueValidator(40), MaxValueValidator(300)])
    blood_pressure_diastolic = models.PositiveIntegerField(validators=[MinValueValidator(30), MaxValueValidator(200)])
    heart_rate = models.PositiveIntegerField(validators=[MinValueValidator(20), MaxValueValidator(250)])
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, validators=[MinValueValidator(30), MaxValueValidator(45)])

    @property
    def bmi(self):
        if not self.height_cm:
            return None
        height_m = float(self.height_cm) / 100
        if height_m <= 0:
            return None
        return round(float(self.weight_kg) / (height_m * height_m), 2)

    def __str__(self):
        return f"Vital signs for EMR #{self.emr_record_id}"


class PrescriptionItem(models.Model):
    emr_record = models.ForeignKey(EMRRecord, on_delete=models.CASCADE, related_name='prescriptions')
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255)
    frequency = models.CharField(max_length=255)
    duration = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.medicine_name
