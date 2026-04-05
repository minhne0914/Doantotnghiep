from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import Appointment, AppointmentChangeLog, TakeAppointment


class AppointmentFlowTests(TestCase):
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
        self.other_patient = User.objects.create_user(
            email='other@example.com',
            password='secret123',
            role='patient',
        )
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.appointment = Appointment.objects.create(
            user=self.doctor,
            full_name='Dr. Demo',
            location='Clinic',
            qualification_name='MD',
            institute_name='Demo Institute',
            hospital_name='Demo Hospital',
            department='Cardiology',
            date=tomorrow,
            start_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('17:00', '%H:%M').time(),
        )

    def test_patient_can_book_valid_slot(self):
        self.client.force_login(self.patient)
        response = self.client.post(
            reverse('take-appointment', args=[self.appointment.pk]),
            {
                'appointment': self.appointment.pk,
                'full_name': 'Patient One',
                'phone_number': '0123456789',
                'message': 'Need consultation',
                'time': '10:00',
            },
        )

        self.assertEqual(response.status_code, 302)
        booking = TakeAppointment.objects.get(appointment=self.appointment, user=self.patient)
        self.assertEqual(booking.status, TakeAppointment.STATUS_CONFIRMED)
        self.assertTrue(
            AppointmentChangeLog.objects.filter(
                booking=booking,
                action=AppointmentChangeLog.ACTION_BOOKED,
            ).exists()
        )

    def test_patient_cannot_book_same_slot_twice(self):
        TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        self.client.force_login(self.other_patient)
        response = self.client.post(
            reverse('take-appointment', args=[self.appointment.pk]),
            {
                'appointment': self.appointment.pk,
                'full_name': 'Patient Two',
                'phone_number': '0987654321',
                'message': 'Need consultation',
                'time': '10:00',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            TakeAppointment.objects.filter(
                appointment=self.appointment,
                date=self.appointment.date,
                time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            ).count(),
            1,
        )

    def test_patient_can_reschedule_to_another_open_slot(self):
        self.client.force_login(self.patient)
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Old note',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        target_date = timezone.localdate() + timedelta(days=2)
        new_appointment = Appointment.objects.create(
            user=self.doctor,
            full_name='Dr. Demo',
            location='Clinic',
            qualification_name='MD',
            institute_name='Demo Institute',
            hospital_name='Demo Hospital',
            department='Cardiology',
            date=target_date,
            start_time=timezone.datetime.strptime('08:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('12:00', '%H:%M').time(),
        )

        response = self.client.post(
            reverse('patient-reschedule-appointment', args=[booking.pk]),
            {
                'appointment': new_appointment.pk,
                'time': '09:30',
                'reason': 'Đổi kế hoạch cá nhân',
                'message': 'Xin đổi sang buổi sáng',
            },
        )

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.appointment_id, new_appointment.id)
        self.assertEqual(booking.status, TakeAppointment.STATUS_CONFIRMED)
        self.assertEqual(booking.notification_version, 2)
        self.assertTrue(
            AppointmentChangeLog.objects.filter(
                booking=booking,
                action=AppointmentChangeLog.ACTION_RESCHEDULED,
                reason='Đổi kế hoạch cá nhân',
            ).exists()
        )

    def test_patient_can_cancel_future_booking(self):
        self.client.force_login(self.patient)
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        response = self.client.post(
            reverse('patient-cancel-appointment', args=[booking.pk]),
            {'reason': 'Không còn sắp xếp được thời gian'},
        )

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, TakeAppointment.STATUS_CANCELLED)
        self.assertTrue(
            AppointmentChangeLog.objects.filter(
                booking=booking,
                action=AppointmentChangeLog.ACTION_CANCELLED,
                reason='Không còn sắp xếp được thời gian',
            ).exists()
        )

    def test_patient_cannot_cancel_inside_deadline(self):
        self.client.force_login(self.patient)
        soon_dt = timezone.localtime() + timedelta(hours=2)
        soon_appointment = Appointment.objects.create(
            user=self.doctor,
            full_name='Dr. Soon',
            location='Clinic',
            qualification_name='MD',
            institute_name='Demo Institute',
            hospital_name='Demo Hospital',
            department='Cardiology',
            date=soon_dt.date(),
            start_time=timezone.datetime.strptime('00:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('23:59', '%H:%M').time(),
        )
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=soon_appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=soon_dt.date(),
            time=soon_dt.time().replace(second=0, microsecond=0),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        response = self.client.get(reverse('patient-cancel-appointment', args=[booking.pk]))

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, TakeAppointment.STATUS_CONFIRMED)

    def test_doctor_only_sees_owned_patients(self):
        other_doctor = User.objects.create_user(
            email='doctor2@example.com',
            password='secret123',
            role='doctor',
        )
        other_appointment = Appointment.objects.create(
            user=other_doctor,
            full_name='Dr. Other',
            location='Clinic',
            qualification_name='MD',
            institute_name='Other Institute',
            hospital_name='Other Hospital',
            department='Cardiology',
            date=timezone.localdate() + timedelta(days=1),
            start_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('17:00', '%H:%M').time(),
        )
        TakeAppointment.objects.create(
            user=self.patient,
            appointment=other_appointment,
            full_name='Hidden Patient',
            phone_number='0123456789',
            message='Hidden',
            date=other_appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        self.client.force_login(self.doctor)
        response = self.client.get(reverse('patient-list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Hidden Patient')
