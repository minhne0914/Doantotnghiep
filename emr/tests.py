import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from appoinment.models import Appointment, TakeAppointment
from .models import EMRRecord


class EMRFlowTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor-emr@example.com',
            password='secret123',
            role='doctor',
        )
        self.patient = User.objects.create_user(
            email='patient-emr@example.com',
            password='secret123',
            role='patient',
        )
        self.appointment = Appointment.objects.create(
            user=self.doctor,
            full_name='Dr. EMR',
            location='Clinic',
            qualification_name='MD',
            institute_name='Demo Institute',
            hospital_name='Demo Hospital',
            department='Cardiology',
            date=timezone.localdate() + timedelta(days=1),
            start_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('17:00', '%H:%M').time(),
        )

    def test_doctor_cannot_create_emr_for_future_confirmed_booking(self):
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient EMR',
            phone_number='0123456789',
            message='Future booking',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('doctor-emr-form', args=[booking.pk]))

        self.assertEqual(response.status_code, 403)

    def test_doctor_can_create_emr_when_booking_arrived(self):
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient EMR',
            phone_number='0123456789',
            message='Arrived booking',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_ARRIVED,
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('emr-record-create-api', args=[booking.pk]),
            data=json.dumps({
                'symptoms': 'Ho và sốt',
                'diagnosis': 'Theo dõi viêm hô hấp',
                'clinical_notes': 'Cần nghỉ ngơi',
                'follow_up_plan': 'Tái khám sau 3 ngày',
                'vital_sign': {
                    'weight_kg': 55,
                    'height_cm': 165,
                    'blood_pressure_systolic': 120,
                    'blood_pressure_diastolic': 80,
                    'heart_rate': 78,
                    'temperature_c': 37.2,
                },
                'prescriptions': [
                    {
                        'medicine_name': 'Paracetamol',
                        'dosage': '500mg',
                        'frequency': '2 lần/ngày',
                        'duration': '3 ngày',
                        'instructions': 'Sau ăn',
                    }
                ],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        booking.refresh_from_db()
        self.assertEqual(booking.status, TakeAppointment.STATUS_COMPLETED)
        self.assertTrue(EMRRecord.objects.filter(appointment=booking).exists())

    def test_delete_emr_returns_booking_to_arrived(self):
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient EMR',
            phone_number='0123456789',
            message='Arrived booking',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_COMPLETED,
        )
        record = EMRRecord.objects.create(
            appointment=booking,
            patient=self.patient,
            doctor=self.doctor,
            symptoms='Ho',
            diagnosis='Theo dõi',
        )
        self.client.force_login(self.doctor)

        response = self.client.generic('DELETE', reverse('emr-record-delete-api', args=[record.pk]))

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, TakeAppointment.STATUS_ARRIVED)
