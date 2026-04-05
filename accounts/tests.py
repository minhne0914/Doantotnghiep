from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appoinment.models import Appointment, AppointmentChangeLog, TakeAppointment
from .models import User


class AccountUrlTests(TestCase):
    def test_duplicate_doctor_profile_route_removed(self):
        response = self.client.get(reverse('doctor-profile-update'))
        self.assertEqual(response.status_code, 302)


class RegistrationFormTests(TestCase):
    def test_patient_registration_sets_role(self):
        response = self.client.post(
            reverse('patient-register'),
            {
                'first_name': 'Test',
                'last_name': 'Patient',
                'email': 'patient@example.com',
                'phone_number': '0123456789',
                'password1': 'StrongPass123',
                'password2': 'StrongPass123',
                'gender': 'male',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.get(email='patient@example.com').role, 'patient')


class DoctorDashboardFeedTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@example.com',
            password='secret123',
            role='doctor',
        )
        self.patient = User.objects.create_user(
            email='patient@example.com',
            password='secret123',
            role='patient',
        )
        self.appointment = Appointment.objects.create(
            user=self.doctor,
            full_name='Dr. Demo',
            location='Clinic',
            qualification_name='MD',
            institute_name='Demo Institute',
            hospital_name='Demo Hospital',
            department='Cardiology',
            date=timezone.localdate() + timedelta(days=1),
            start_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('17:00', '%H:%M').time(),
        )
        self.booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Test',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

    def test_dashboard_uses_change_logs_for_latest_notifications(self):
        AppointmentChangeLog.objects.create(
            booking=self.booking,
            action=AppointmentChangeLog.ACTION_BOOKED,
            changed_by=self.patient,
            new_appointment=self.appointment,
            new_date=self.booking.date,
            new_time=self.booking.time,
        )
        AppointmentChangeLog.objects.create(
            booking=self.booking,
            action=AppointmentChangeLog.ACTION_RESCHEDULED,
            changed_by=self.patient,
            old_appointment=self.appointment,
            new_appointment=self.appointment,
            old_date=self.booking.date,
            old_time=self.booking.time,
            new_date=self.booking.date + timedelta(days=1),
            new_time=timezone.datetime.strptime('11:00', '%H:%M').time(),
        )
        AppointmentChangeLog.objects.create(
            booking=self.booking,
            action=AppointmentChangeLog.ACTION_CANCELLED,
            changed_by=self.patient,
            old_appointment=self.appointment,
            old_date=self.booking.date,
            old_time=self.booking.time,
        )

        self.client.force_login(self.doctor)
        response = self.client.get(reverse('doctor-dashboard-data'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        titles = [item['title'] for item in payload['latest_notifications']]
        self.assertIn('Lịch hẹn mới', titles)
        self.assertIn('Lịch hẹn được đổi', titles)
        self.assertIn('Lịch hẹn bị hủy', titles)
