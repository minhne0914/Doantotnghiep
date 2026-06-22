from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from appoinment.models import Appointment, AppointmentChangeLog, TakeAppointment
from .admin import (
    DoctorProfileAdmin,
    DoctorProfileAdminForm,
    DoctorProfileInline,
    DoctorAccountAdmin,
    PatientAccountAdmin,
    UserAdmin,
)
from .models import DoctorAccount, DoctorProfile, PatientAccount, User, UserRole


class AccountUrlTests(TestCase):
    def test_duplicate_doctor_profile_route_removed(self):
        response = self.client.get(reverse('doctor-profile-update'))
        self.assertEqual(response.status_code, 302)


class RegistrationFormTests(TestCase):
    def test_create_superuser_sets_default_role(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='StrongPass123',
        )

        self.assertEqual(admin.role, 'doctor')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

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

    def test_public_cannot_register_doctor_account(self):
        response = self.client.get(reverse('doctor-register'))

        self.assertEqual(response.status_code, 404)

    def test_staff_doctor_register_route_redirects_to_admin_doctor_add(self):
        admin = User.objects.create_superuser(
            email='admin-create-doctor@example.com',
            password='StrongPass123',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('doctor-register'))

        self.assertRedirects(
            response,
            reverse('admin:accounts_doctoraccount_add'),
            fetch_redirect_response=False,
        )

    def test_public_navbar_only_exposes_patient_registration(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('patient-register'))
        self.assertNotContains(response, reverse('doctor-register'))

    def test_login_rejects_external_next_redirect(self):
        User.objects.create_user(
            email='login@example.com',
            password='StrongPass123',
            role='patient',
        )

        response = self.client.post(
            f"{reverse('login')}?next=https://evil.example/phishing",
            {
                'email': 'login@example.com',
                'password': 'StrongPass123',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_login_wrong_password_shows_credential_error(self):
        User.objects.create_user(
            email='patient@example.com',
            password='StrongPass123',
            role='patient',
        )

        response = self.client.post(
            reverse('login'),
            {
                'email': 'patient@example.com',
                'password': 'WrongPass123',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email or password is incorrect.')
        self.assertNotContains(response, 'User does not exist.')

    def test_password_reset_redirects_to_done_page(self):
        User.objects.create_user(
            email='reset@example.com',
            password='StrongPass123',
            role='patient',
        )

        response = self.client.post(
            reverse('password_reset'),
            {'email': 'reset@example.com'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('password_reset_done'))

    def test_password_reset_confirm_changes_password(self):
        user = User.objects.create_user(
            email='reset-confirm@example.com',
            password='OldStrongPass123',
            role='patient',
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            response['Location'],
            {
                'new_password1': 'NewStrongPass123',
                'new_password2': 'NewStrongPass123',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('password_reset_complete'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewStrongPass123'))


class AdminProfileTests(TestCase):
    def setUp(self):
        self.user_admin = UserAdmin(User, admin.site)
        self.doctor_account_admin = DoctorAccountAdmin(DoctorAccount, admin.site)
        self.patient_account_admin = PatientAccountAdmin(PatientAccount, admin.site)
        self.profile_admin = DoctorProfileAdmin(DoctorProfile, admin.site)
        self.request = RequestFactory().get('/admin/accounts/user/')
        self.staff_user = User.objects.create_superuser(
            email='staff@example.com', password='StrongPass123'
        )
        self.request.user = self.staff_user
        self.doctor = User.objects.create_user(
            email='doctor-profile@example.com',
            password='StrongPass123',
            role=UserRole.DOCTOR,
        )
        self.patient = User.objects.create_user(
            email='patient-profile@example.com',
            password='StrongPass123',
            role=UserRole.PATIENT,
        )

    def test_doctor_account_shows_professional_profile_inline(self):
        inlines = self.user_admin.get_inline_instances(self.request, self.doctor)

        self.assertEqual(len(inlines), 1)
        self.assertIsInstance(inlines[0], DoctorProfileInline)

    def test_patient_account_does_not_show_doctor_profile_inline(self):
        self.assertEqual(
            self.user_admin.get_inline_instances(self.request, self.patient), []
        )

    def test_saving_doctor_account_creates_editable_profile(self):
        self.user_admin.save_model(self.request, self.doctor, None, True)

        self.assertTrue(DoctorProfile.objects.filter(user=self.doctor).exists())

    def test_doctor_profile_admin_only_offers_doctor_accounts(self):
        user_field = DoctorProfile._meta.get_field('user')
        form_field = self.profile_admin.formfield_for_foreignkey(user_field, self.request)

        self.assertIn(self.doctor, form_field.queryset)
        self.assertNotIn(self.patient, form_field.queryset)

    def test_doctor_profile_form_updates_account_and_professional_details(self):
        profile = DoctorProfile.objects.create(user=self.doctor)
        form = DoctorProfileAdminForm(
            data={
                'first_name': 'Hoang',
                'last_name': 'Minh',
                'email': 'hoang.minh@example.com',
                'gender': 'male',
                'phone_number': '0987654321',
                'specialization': 'Cardiology',
                'qualifications': 'Specialist Level I',
                'experience': '8 years',
                'biography': 'Cardiology doctor',
            },
            instance=profile,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.doctor.refresh_from_db()
        profile.refresh_from_db()

        self.assertEqual(self.doctor.full_name, 'Hoang Minh')
        self.assertEqual(self.doctor.email, 'hoang.minh@example.com')
        self.assertEqual(profile.specialization, 'Cardiology')

    def test_existing_doctor_profile_displays_linked_account_instead_of_selector(self):
        profile = DoctorProfile.objects.create(user=self.doctor)

        account_fields = self.profile_admin.get_fieldsets(self.request, profile)[0][1]['fields']
        account_link = self.profile_admin.doctor_account(profile)

        self.assertIn('doctor_account', account_fields)
        self.assertNotIn('user', account_fields)
        self.assertIn(self.doctor.email, account_link)

    def test_existing_doctor_profile_change_page_has_no_tabs_and_renders(self):
        profile = DoctorProfile.objects.create(user=self.doctor)
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('admin:accounts_doctorprofile_change', args=[profile.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="jazzy-tabs"')
        self.assertContains(response, 'id="id_specialization"')
        self.assertContains(response, self.doctor.email)

    def test_role_specific_account_lists_only_return_their_own_role(self):
        doctor_accounts = self.doctor_account_admin.get_queryset(self.request)
        patient_accounts = self.patient_account_admin.get_queryset(self.request)

        self.assertIn(self.doctor, doctor_accounts)
        self.assertNotIn(self.patient, doctor_accounts)
        self.assertIn(self.patient, patient_accounts)
        self.assertNotIn(self.doctor, patient_accounts)

    def test_patient_directory_searches_name_and_email_without_system_filters(self):
        self.assertEqual(self.patient_account_admin.list_filter, ())
        self.assertEqual(
            self.patient_account_admin.search_fields,
            ('first_name', 'last_name', 'email'),
        )

    def test_role_specific_admin_assigns_the_expected_role_on_create(self):
        new_doctor = DoctorAccount(email='created-doctor@example.com')
        new_patient = PatientAccount(email='created-patient@example.com')

        self.doctor_account_admin.save_model(self.request, new_doctor, None, False)
        self.patient_account_admin.save_model(self.request, new_patient, None, False)

        new_doctor.refresh_from_db()
        new_patient.refresh_from_db()
        self.assertEqual(new_doctor.role, UserRole.DOCTOR)
        self.assertEqual(new_patient.role, UserRole.PATIENT)
        self.assertTrue(DoctorProfile.objects.filter(user_id=new_doctor.pk).exists())

    def test_patient_change_page_renders_all_editable_details_without_tabs(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('admin:accounts_patientaccount_change', args=[self.patient.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="jazzy-tabs"')
        self.assertContains(response, 'id="id_first_name"')
        self.assertContains(response, 'id="id_phone_number"')


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
