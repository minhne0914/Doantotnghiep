from datetime import timedelta

from django.contrib import admin
from django.db import IntegrityError
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import DoctorProfile, User
from notifications.models import RealtimeNotification
from .admin import AppointmentAdmin, TakeAppointmentAdmin
from .consumers import DirectChatConsumer
from .forms import CreateAppointmentForm
from .models import Appointment, AppointmentChangeLog, DirectMessage, DoctorReview, TakeAppointment


class AppointmentFormTests(TestCase):
    def test_create_form_uses_timezone_aware_comparison(self):
        form = CreateAppointmentForm(data={
            'date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'start_time': '09:00',
            'end_time': '17:00',
            'hospital_name': 'Demo Hospital',
            'location': 'Clinic',
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_database_rejects_shift_with_invalid_time_range(self):
        doctor = User.objects.create_user(
            email='constraint-doctor@example.com',
            password='secret123',
            role='doctor',
        )

        with self.assertRaises(IntegrityError):
            Appointment.objects.create(
                user=doctor,
                full_name='Dr. Constraint',
                location='Clinic',
                qualification_name='MD',
                institute_name='Demo Institute',
                hospital_name='Demo Hospital',
                department='Cardiology',
                date=timezone.localdate() + timedelta(days=1),
                start_time=timezone.datetime.strptime('17:00', '%H:%M').time(),
                end_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            )


class AppointmentAdminTests(TestCase):
    def setUp(self):
        self.model_admin = AppointmentAdmin(Appointment, admin.site)
        self.take_model_admin = TakeAppointmentAdmin(TakeAppointment, admin.site)
        self.doctor = User.objects.create_user(
            email='admin-doctor@example.com',
            password='secret123',
            first_name='Hoang',
            last_name='Minh',
            role='doctor',
        )
        DoctorProfile.objects.create(
            user=self.doctor,
            specialization='Heart Disease',
            qualifications='Specialist Level I',
            biography='Medic hospital doctor',
        )
        self.patient = User.objects.create_user(
            email='admin-patient@example.com',
            password='secret123',
            role='patient',
        )
        self.admin_user = User.objects.create_superuser(
            email='appointment-admin@example.com',
            password='secret123',
        )
        self.appointment = Appointment.objects.create(
            user=self.doctor,
            full_name='Hoang Minh',
            department='Heart Disease',
            qualification_name='Specialist Level I',
            institute_name='Medic hospital doctor',
            hospital_name='Medic Clinic',
            location='Room 101',
            date=timezone.localdate() + timedelta(days=1),
            start_time=timezone.datetime.strptime('08:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('11:00', '%H:%M').time(),
        )
        self.no_slot_doctor = User.objects.create_user(
            email='no-admin-slot-doctor@example.com',
            password='secret123',
            first_name='No',
            last_name='Slot',
            role='doctor',
        )

    def test_appointment_admin_user_field_only_lists_doctors(self):
        user_field = Appointment._meta.get_field('user')

        form_field = self.model_admin.formfield_for_foreignkey(user_field, None)

        self.assertIn(self.doctor, form_field.queryset)
        self.assertNotIn(self.patient, form_field.queryset)
        self.assertEqual(
            form_field.label_from_instance(self.doctor),
            'BS. Hoang Minh — admin-doctor@example.com',
        )

    def test_appointment_admin_auto_fills_doctor_profile_fields_on_save(self):
        appointment = Appointment(
            user=self.doctor,
            hospital_name='Medic Clinic',
            location='Room 101',
            date=timezone.localdate() + timedelta(days=1),
            start_time=timezone.datetime.strptime('08:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('11:00', '%H:%M').time(),
        )

        self.model_admin.save_model(None, appointment, None, False)

        appointment.refresh_from_db()
        self.assertEqual(appointment.full_name, 'Hoang Minh')
        self.assertEqual(appointment.department, 'Heart Disease')
        self.assertEqual(appointment.qualification_name, 'Specialist Level I')
        self.assertEqual(appointment.institute_name, 'Medic hospital doctor')

    def test_appointment_admin_add_form_has_streamlined_actions_and_time_inputs(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin:appoinment_appointment_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quay l&#7841;i')
        self.assertContains(response, 'L&#432;u v&#224; ti&#7871;p t&#7909;c')
        self.assertContains(response, 'type="time"')
        self.assertContains(response, 'Thong tin lich kham')
        self.assertContains(response, '.submit-row')
        self.assertContains(response, '#jazzy-actions')
        self.assertContains(response, 'display: none')
        self.assertNotContains(response, 'Thoi gian kham')
        self.assertNotContains(response, 'Co so kham')
        self.assertNotContains(
            response,
            'Chi hien thi tai khoan bac si. Ten, anh, chuyen khoa va bang cap',
        )

    def test_appointment_admin_rejects_overlapping_or_invalid_shift(self):
        request = RequestFactory().get('/admin/appoinment/appointment/add/')
        request.user = self.admin_user
        form_class = self.model_admin.get_form(request)
        base_data = {
            'user': self.doctor.pk,
            'date': self.appointment.date.isoformat(),
            'hospital_name': 'Medic Clinic',
            'location': 'Room 102',
            'is_active': 'on',
        }

        invalid_range_form = form_class({
            **base_data,
            'start_time': '17:00',
            'end_time': '09:00',
        })
        self.assertFalse(invalid_range_form.is_valid())
        self.assertIn('end_time', invalid_range_form.errors)

        overlapping_form = form_class({
            **base_data,
            'start_time': '10:00',
            'end_time': '12:00',
        })
        self.assertFalse(overlapping_form.is_valid())
        self.assertIn('start_time', overlapping_form.errors)

    def test_take_appointment_admin_user_field_only_lists_patients(self):
        user_field = TakeAppointment._meta.get_field('user')

        form_field = self.take_model_admin.formfield_for_foreignkey(user_field, None)

        self.assertIn(self.patient, form_field.queryset)
        self.assertNotIn(self.doctor, form_field.queryset)
        self.assertEqual(
            form_field.label_from_instance(self.patient),
            'admin-patient@example.com — admin-patient@example.com',
        )

    def test_take_appointment_admin_appointment_field_has_readable_labels(self):
        appointment_field = TakeAppointment._meta.get_field('appointment')

        form_field = self.take_model_admin.formfield_for_foreignkey(appointment_field, None)

        self.assertIn(self.appointment, form_field.queryset)
        label = form_field.label_from_instance(self.appointment)
        self.assertIn('BS. Hoang Minh', label)
        self.assertIn(self.appointment.date.strftime('%d/%m/%Y'), label)
        self.assertIn('08:00-11:00', label)
        self.assertIn('Medic Clinic', label)

    def test_take_appointment_admin_add_form_has_streamlined_actions_and_time_input(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin:appoinment_takeappointment_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quay l&#7841;i')
        self.assertContains(response, 'L&#432;u v&#224; ti&#7871;p t&#7909;c')
        self.assertContains(response, 'type="time"')
        self.assertContains(response, 'Thông tin đặt lịch')
        self.assertContains(response, 'id="id_doctor"')
        self.assertContains(response, f'data-doctor="{self.doctor.pk}"')
        self.assertContains(response, '#jazzy-actions')
        self.assertContains(response, 'display: none')
        self.assertNotContains(response, 'id="id_full_name"')
        self.assertNotContains(response, 'id="id_phone_number"')
        self.assertContains(response, 'data-slots-url=')
        self.assertContains(response, 'fetch(`${slotsUrl}?doctor=')
        self.assertContains(response, "window.addEventListener('load'")
        self.assertContains(response, "select2('destroy')")
        self.assertNotContains(response, 'no-admin-slot-doctor@example.com')
        self.assertNotContains(response, 'Liên kết')
        self.assertNotContains(response, 'Thời gian')

    def test_take_appointment_admin_doctor_slots_endpoint_returns_open_times(self):
        self.client.force_login(self.admin_user)
        TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name=self.patient.full_name,
            phone_number='',
            message='Existing booking',
            date=self.appointment.date,
            time=timezone.datetime.strptime('08:30', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        response = self.client.get(
            reverse('admin:appoinment_takeappointment_doctor_slots'),
            {'doctor': self.doctor.pk},
        )

        self.assertEqual(response.status_code, 200)
        slots = response.json()['slots']
        slot_times = [slot['time'] for slot in slots]
        self.assertIn('08:00', slot_times)
        self.assertNotIn('08:30', slot_times)
        self.assertIn('10:30', slot_times)

    def test_take_appointment_admin_save_auto_fills_patient_and_slot_fields(self):
        booking = TakeAppointment(
            user=self.patient,
            appointment=self.appointment,
            message='Admin booking',
            status=TakeAppointment.STATUS_PENDING,
        )

        self.take_model_admin.save_model(None, booking, None, False)

        booking.refresh_from_db()
        self.assertEqual(booking.full_name, self.patient.full_name)
        self.assertEqual(booking.phone_number, self.patient.phone_number or '')
        self.assertEqual(booking.date, self.appointment.date)
        self.assertEqual(booking.time, self.appointment.start_time)

    def test_take_appointment_admin_form_rejects_duplicate_active_time(self):
        TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name=self.patient.full_name,
            phone_number='',
            message='Existing booking',
            date=self.appointment.date,
            time=timezone.datetime.strptime('08:30', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        form = self.take_model_admin.form(data={
            'user': self.patient.pk,
            'doctor': self.doctor.pk,
            'appointment': self.appointment.pk,
            'message': 'Duplicate booking',
            'time': '08:30',
            'status': TakeAppointment.STATUS_PENDING,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('time', form.errors)


class DirectChatConsumerTests(TestCase):
    def test_decode_attachment_rejects_disallowed_content_type(self):
        attachment, error = DirectChatConsumer._decode_attachment(
            'data:text/html;base64,PGgxPkhlbGxvPC9oMT4=',
            'hello.html',
        )

        self.assertIsNone(attachment)
        self.assertIsNotNone(error)


class DirectMessageAdminPrivacyTests(TestCase):
    def test_admin_cannot_open_direct_message_changelist(self):
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='secret123',
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:appoinment_directmessage_changelist'))

        self.assertEqual(response.status_code, 403)


class DoctorDirectoryTests(TestCase):
    def test_directory_lists_doctors_without_requiring_today_slot(self):
        doctor = User.objects.create_user(
            email='no-slot-doctor@example.com',
            password='secret123',
            first_name='Lan',
            last_name='Nguyen',
            role='doctor',
        )
        DoctorProfile.objects.create(user=doctor, specialization='Heart Disease')

        response = self.client.get(reverse('doctor'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BS. Lan Nguyen')
        self.assertContains(response, 'Chưa mở lịch khám sắp tới')

    def test_directory_filters_by_name_department_and_date(self):
        target_date = timezone.localdate() + timedelta(days=2)
        other_date = timezone.localdate() + timedelta(days=3)

        heart_doctor = User.objects.create_user(
            email='heart@example.com',
            password='secret123',
            first_name='Minh',
            last_name='Heart',
            role='doctor',
        )
        DoctorProfile.objects.create(user=heart_doctor, specialization='Heart Disease')
        eye_doctor = User.objects.create_user(
            email='eye@example.com',
            password='secret123',
            first_name='Khoa',
            last_name='Eye',
            role='doctor',
        )
        DoctorProfile.objects.create(user=eye_doctor, specialization='Eye Care')

        Appointment.objects.create(
            user=heart_doctor,
            full_name='BS. Minh Heart',
            location='Heart Clinic',
            qualification_name='MD',
            institute_name='Medical University',
            hospital_name='Central Hospital',
            department='Heart Disease',
            date=target_date,
            start_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('12:00', '%H:%M').time(),
        )
        Appointment.objects.create(
            user=eye_doctor,
            full_name='BS. Khoa Eye',
            location='Eye Clinic',
            qualification_name='MD',
            institute_name='Medical University',
            hospital_name='Eye Hospital',
            department='Eye Care',
            date=other_date,
            start_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('12:00', '%H:%M').time(),
        )

        response = self.client.get(reverse('doctor'), {
            'search': 'Minh',
            'department': 'Heart Disease',
            'date': target_date.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BS. Minh Heart')
        self.assertNotContains(response, 'BS. Khoa Eye')

    def test_directory_shows_eight_doctors_per_page(self):
        for index in range(9):
            doctor = User.objects.create_user(
                email=f'doctor-page-{index}@example.com',
                password='secret123',
                first_name=f'Doctor{index}',
                last_name='Demo',
                role='doctor',
            )
            DoctorProfile.objects.create(user=doctor, specialization='Heart Disease')

        response = self.client.get(reverse('doctor'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['doctor']), 8)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 2)


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
        self.assertEqual(booking.status, TakeAppointment.STATUS_PENDING)
        self.assertTrue(
            AppointmentChangeLog.objects.filter(
                booking=booking,
                action=AppointmentChangeLog.ACTION_BOOKED,
            ).exists()
        )

    def test_patient_cannot_book_at_shift_end_time(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse('take-appointment', args=[self.appointment.pk]),
            {
                'appointment': self.appointment.pk,
                'full_name': 'Patient One',
                'phone_number': '0123456789',
                'message': 'Need consultation',
                'time': '17:00',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Giờ đã chọn nằm ngoài khung khám của bác sĩ.')
        self.assertFalse(
            TakeAppointment.objects.filter(
                appointment=self.appointment,
                user=self.patient,
            ).exists()
        )

    def test_doctor_can_confirm_pending_booking(self):
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_PENDING,
        )
        self.client.force_login(self.doctor)

        response = self.client.post(reverse('doctor-confirm-booking', args=[booking.pk]))

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, TakeAppointment.STATUS_CONFIRMED)
        self.assertEqual(booking.notification_version, 2)
        self.assertTrue(
            RealtimeNotification.objects.filter(
                user=self.patient,
                title='Lich kham da duoc xac nhan',
                payload__booking_id=booking.id,
            ).exists()
        )
        self.assertTrue(
            RealtimeNotification.objects.filter(
                user=self.doctor,
                title='Ban da xac nhan lich kham',
                payload__booking_id=booking.id,
            ).exists()
        )

    def test_doctor_create_schedule_redirects_to_created_date(self):
        self.client.force_login(self.doctor)
        target_date = timezone.localdate() + timedelta(days=4)

        response = self.client.post(
            reverse('doctor-appointment-create'),
            {
                'date': target_date.isoformat(),
                'start_time': '08:00',
                'end_time': '12:00',
                'hospital_name': 'Demo Clinic',
                'location': 'Room 101',
            },
        )

        created = Appointment.objects.get(user=self.doctor, date=target_date)
        self.assertRedirects(
            response,
            f'{reverse("doctor-appointment")}?date={target_date.isoformat()}&created={created.pk}',
            fetch_redirect_response=False,
        )

    def test_doctor_can_create_schedule_with_ajax_modal(self):
        self.client.force_login(self.doctor)
        target_date = timezone.localdate() + timedelta(days=5)

        response = self.client.post(
            reverse('doctor-appointment-create'),
            {
                'date': target_date.isoformat(),
                'start_time': '13:00',
                'end_time': '17:00',
                'hospital_name': 'Modal Clinic',
                'location': 'Room 202',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['appointment']['date'], target_date.isoformat())
        self.assertEqual(payload['appointment']['start_time'], '13:00')
        self.assertTrue(
            Appointment.objects.filter(
                user=self.doctor,
                date=target_date,
                hospital_name='Modal Clinic',
            ).exists()
        )

    def test_doctor_cannot_create_overlapping_working_schedule(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('doctor-appointment-create'),
            {
                'date': self.appointment.date.isoformat(),
                'start_time': '10:00',
                'end_time': '12:00',
                'hospital_name': 'Overlap Clinic',
                'location': 'Room 303',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload['ok'])
        self.assertIn('start_time', payload['errors'])
        self.assertFalse(
            Appointment.objects.filter(
                user=self.doctor,
                hospital_name='Overlap Clinic',
            ).exists()
        )

    def test_doctor_can_cancel_working_schedule_with_ajax(self):
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('delete-appointment', args=[self.appointment.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['cancelled_bookings'], 1)
        self.appointment.refresh_from_db()
        booking.refresh_from_db()
        self.assertFalse(self.appointment.is_active)
        self.assertEqual(booking.status, TakeAppointment.STATUS_CANCELLED)

    def test_doctor_can_cancel_patient_booking_with_ajax(self):
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('delete-patient', args=[booking.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['booking_id'], booking.pk)
        booking.refresh_from_db()
        self.assertEqual(booking.status, TakeAppointment.STATUS_CANCELLED)
        self.assertTrue(
            AppointmentChangeLog.objects.filter(
                booking=booking,
                action=AppointmentChangeLog.ACTION_CANCELLED,
                changed_by=self.doctor,
            ).exists()
        )
        self.assertTrue(
            RealtimeNotification.objects.filter(
                user=self.patient,
                title='Bác sĩ đã hủy lịch khám',
                payload__booking_id=booking.id,
            ).exists()
        )
        self.assertTrue(
            RealtimeNotification.objects.filter(
                user=self.doctor,
                title='Bạn đã hủy lịch khám',
                payload__booking_id=booking.id,
            ).exists()
        )

    def test_doctor_calendar_events_include_working_schedule_highlight(self):
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse('doctor-calendar-events'),
            {
                'start': self.appointment.date.isoformat(),
                'end': (self.appointment.date + timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        events = response.json()
        shift_bg = next(item for item in events if item['id'] == f'shift_{self.appointment.pk}')
        shift_label = next(item for item in events if item['id'] == f'shift_label_{self.appointment.pk}')
        self.assertEqual(shift_bg['display'], 'background')
        self.assertIn('doctor-shift-bg', shift_bg['classNames'])
        self.assertEqual(shift_label['extendedProps']['event_type'], 'doctor_shift')
        self.assertIn('Working hours', shift_label['title'])
        booking_event = next(item for item in events if item['id'] == f'booking_{booking.pk}')
        self.assertEqual(booking_event['title'], 'Patient One')
        self.assertIn('patient-booking-event', booking_event['classNames'])
        self.assertEqual(booking_event['extendedProps']['event_type'], 'patient_booking')
        self.assertEqual(booking_event['extendedProps']['patient_name'], 'Patient One')

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
        self.assertEqual(booking.status, TakeAppointment.STATUS_PENDING)
        self.assertEqual(booking.notification_version, 2)
        self.assertTrue(
            AppointmentChangeLog.objects.filter(
                booking=booking,
                action=AppointmentChangeLog.ACTION_RESCHEDULED,
                reason='Đổi kế hoạch cá nhân',
            ).exists()
        )

    def test_patient_reschedule_defaults_to_new_slot_start_when_old_time_is_submitted(self):
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
            full_name='Dr. Morning',
            location='Clinic',
            qualification_name='MD',
            institute_name='Demo Institute',
            hospital_name='Demo Hospital',
            department='Cardiology',
            date=target_date,
            start_time=timezone.datetime.strptime('08:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('09:00', '%H:%M').time(),
        )

        response = self.client.post(
            reverse('patient-reschedule-appointment', args=[booking.pk]),
            {
                'appointment': new_appointment.pk,
                'time': '10:00',
                'reason': 'Change plan',
                'message': 'Please move me to the morning slot',
            },
        )

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.appointment_id, new_appointment.id)
        self.assertEqual(
            booking.time,
            timezone.datetime.strptime('08:00', '%H:%M').time(),
        )
        self.assertEqual(booking.status, TakeAppointment.STATUS_PENDING)

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

    def test_doctor_cancel_keeps_patient_history_and_notifies_patient(self):
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
        self.client.force_login(self.doctor)

        response = self.client.post(reverse('delete-patient', args=[booking.pk]))

        self.assertRedirects(response, reverse('patient-list'))
        booking.refresh_from_db()
        self.assertEqual(booking.status, TakeAppointment.STATUS_CANCELLED)
        self.assertTrue(
            AppointmentChangeLog.objects.filter(
                booking=booking,
                action=AppointmentChangeLog.ACTION_CANCELLED,
                changed_by=self.doctor,
            ).exists()
        )
        self.assertTrue(
            RealtimeNotification.objects.filter(
                user=self.patient,
                title='Bác sĩ đã hủy lịch khám',
                category='appointment',
                payload__booking_id=booking.id,
                payload__status=TakeAppointment.STATUS_CANCELLED,
            ).exists()
        )

        self.client.force_login(self.patient)
        patient_response = self.client.get(reverse('patient-my-appointments'))
        visible_ids = [item.id for item in patient_response.context['appointments']]
        self.assertIn(booking.id, visible_ids)

    def test_patient_appointments_are_sorted_by_useful_date_order(self):
        self.client.force_login(self.patient)
        active_today = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Active appointment today',
            date=timezone.localdate(),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_ARRIVED,
        )
        soon_booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Soon appointment',
            date=timezone.localdate() + timedelta(days=1),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        later_booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Later appointment',
            date=timezone.localdate() + timedelta(days=5),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        recent_history = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Recent history',
            date=timezone.localdate() - timedelta(days=1),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_COMPLETED,
        )
        older_history = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Older history',
            date=timezone.localdate() - timedelta(days=10),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CANCELLED,
        )

        response = self.client.get(reverse('patient-my-appointments'))

        self.assertEqual(response.status_code, 200)
        ordered_ids = [booking.id for booking in response.context['appointments']]
        self.assertEqual(
            ordered_ids[:5],
            [
                active_today.id,
                soon_booking.id,
                later_booking.id,
                recent_history.id,
                older_history.id,
            ],
        )

    def test_patient_recent_pending_booking_is_easy_to_find_first(self):
        self.client.force_login(self.patient)
        confirmed_booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Confirmed appointment',
            date=timezone.localdate() + timedelta(days=1),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
            created_at=timezone.now() - timedelta(days=2),
        )
        pending_booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Fresh pending appointment',
            date=timezone.localdate() + timedelta(days=14),
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_PENDING,
            created_at=timezone.now(),
        )

        response = self.client.get(reverse('patient-my-appointments'))

        self.assertEqual(response.status_code, 200)
        ordered_ids = [booking.id for booking in response.context['appointments']]
        self.assertEqual(ordered_ids[:2], [pending_booking.id, confirmed_booking.id])

    def test_patient_can_filter_new_pending_appointments(self):
        self.client.force_login(self.patient)
        pending_booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Fresh pending appointment',
            date=timezone.localdate() + timedelta(days=14),
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_PENDING,
        )
        TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Confirmed appointment',
            date=timezone.localdate() + timedelta(days=1),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        response = self.client.get(reverse('patient-my-appointments'), {'status': 'new'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([booking.id for booking in response.context['appointments']], [pending_booking.id])
        self.assertEqual(response.context['status_filter'], 'new')

    def test_completed_patient_appointment_hides_modify_warning(self):
        self.client.force_login(self.patient)
        TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Completed consultation',
            date=timezone.localdate() - timedelta(days=1),
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_COMPLETED,
        )

        response = self.client.get(reverse('patient-my-appointments'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<div class="appointment-warning-ui">', html=True)

    def test_patient_review_uses_patient_layout_and_returns_to_my_appointments(self):
        self.client.force_login(self.patient)
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Completed consultation',
            date=timezone.localdate() - timedelta(days=1),
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_COMPLETED,
        )

        response = self.client.get(reverse('submit-doctor-review', args=[booking.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('patient-my-appointments'))
        self.assertNotContains(response, 'content-wrapper')

        response = self.client.post(
            reverse('submit-doctor-review', args=[booking.pk]),
            {
                'rating': 5,
                'comment': 'Doctor was professional and helpful.',
            },
        )

        self.assertRedirects(response, reverse('patient-my-appointments'))
        self.assertTrue(
            DoctorReview.objects.filter(
                booking=booking,
                patient=self.patient,
                doctor=self.doctor,
            ).exists()
        )

    def test_patient_chat_room_only_shows_current_booking_messages(self):
        self.client.force_login(self.patient)
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        other_booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Need another consultation',
            date=self.appointment.date,
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        DirectMessage.objects.create(
            booking=booking,
            sender=self.patient,
            content='Message for this booking',
        )
        DirectMessage.objects.create(
            booking=other_booking,
            sender=self.patient,
            content='Message for another booking',
        )

        response = self.client.get(reverse('chat-room', args=[booking.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Message for this booking')
        self.assertNotContains(response, 'Message for another booking')

    def test_completed_booking_chat_is_read_only(self):
        self.client.force_login(self.patient)
        booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Patient One',
            phone_number='0123456789',
            message='Completed consultation',
            date=timezone.localdate() - timedelta(days=1),
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_COMPLETED,
        )

        response = self.client.get(reverse('chat-room', args=[booking.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="chat-input"')

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

    def test_doctor_patient_list_includes_past_completed_and_future_bookings(self):
        past_booking = TakeAppointment.objects.create(
            user=self.patient,
            appointment=self.appointment,
            full_name='Past Completed Patient',
            phone_number='0123456789',
            message='Completed visit',
            date=timezone.localdate() - timedelta(days=30),
            time=timezone.datetime.strptime('09:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_COMPLETED,
        )
        upcoming_booking = TakeAppointment.objects.create(
            user=self.other_patient,
            appointment=self.appointment,
            full_name='Upcoming Patient',
            phone_number='0987654321',
            message='Upcoming visit',
            date=timezone.localdate() + timedelta(days=7),
            time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        TakeAppointment.objects.create(
            user=self.other_patient,
            appointment=self.appointment,
            full_name='Cancelled Patient',
            phone_number='0987654321',
            message='Cancelled visit',
            date=timezone.localdate() + timedelta(days=8),
            time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            status=TakeAppointment.STATUS_CANCELLED,
        )
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('patient-list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, past_booking.full_name)
        self.assertContains(response, upcoming_booking.full_name)
        self.assertNotContains(response, 'Cancelled Patient')
        self.assertContains(response, 'Đã hoàn thành')
        self.assertContains(response, 'Đã xác nhận')
