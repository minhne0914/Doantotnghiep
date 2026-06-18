from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import DoctorProfile, User
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
