import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import DoctorProfile, User, UserRole
from appoinment.models import (
    Appointment,
    AppointmentChangeLog,
    DirectMessage,
    DoctorReview,
    TakeAppointment,
)
from emr.models import EMRRecord, PrescriptionItem, VitalSign
from home.models import ChatMessage, MedicalHistory
from notifications.models import NotificationPreference, RealtimeNotification


PASSWORD = 'Demo@2026'
DEMO_DOMAIN = 'medic.test'


DOCTORS = [
    {
        'email': 'doctor.tim@medic.test',
        'first_name': 'An',
        'last_name': 'Nguyen',
        'phone_number': '0902000001',
        'gender': 'male',
        'specialization': 'Heart Disease',
        'qualifications': 'Thac si Tim mach, Dai hoc Y Duoc TP.HCM',
        'experience': '12 nam kinh nghiem dieu tri benh ly tim mach.',
        'biography': 'Chuyen sau tang huyet ap, dau nguc va benh mach vanh.',
        'hospital_name': 'Medic Heart Center',
        'location': 'Tang 2, khu A, 123 Nguyen Trai, TP.HCM',
    },
    {
        'email': 'doctor.noitiet@medic.test',
        'first_name': 'Binh',
        'last_name': 'Tran',
        'phone_number': '0902000002',
        'gender': 'female',
        'specialization': 'Diabetes Disease',
        'qualifications': 'Bac si CKI Noi tiet',
        'experience': '10 nam theo doi va dieu tri dai thao duong.',
        'biography': 'Tu van kiem soat duong huyet, bien chung than kinh va than.',
        'hospital_name': 'Medic Endocrine Clinic',
        'location': 'Tang 3, khu B, 45 Le Loi, TP.HCM',
    },
    {
        'email': 'doctor.ungbuou@medic.test',
        'first_name': 'Chi',
        'last_name': 'Le',
        'phone_number': '0902000003',
        'gender': 'female',
        'specialization': 'Breast Cancer',
        'qualifications': 'Tien si Ung buou',
        'experience': '15 nam sang loc va tu van ung thu vu.',
        'biography': 'Chuyen doc ket qua sieu am, nhan dinh nguy co va theo doi sau dieu tri.',
        'hospital_name': 'Medic Oncology Center',
        'location': 'Phong 401, 88 Cach Mang Thang Tam, TP.HCM',
    },
    {
        'email': 'doctor.nhakhoa@medic.test',
        'first_name': 'Dung',
        'last_name': 'Pham',
        'phone_number': '0902000004',
        'gender': 'male',
        'specialization': 'Dentistry',
        'qualifications': 'Bac si Rang Ham Mat',
        'experience': '9 nam dieu tri nha khoa tong quat va tham my.',
        'biography': 'Chuyen ve sau rang, nieng rang va cham soc rang mieng du phong.',
        'hospital_name': 'Medic Dental',
        'location': 'Phong 203, 12 Dien Bien Phu, TP.HCM',
    },
    {
        'email': 'doctor.tmh@medic.test',
        'first_name': 'Ha',
        'last_name': 'Vo',
        'phone_number': '0902000005',
        'gender': 'female',
        'specialization': 'ENT Specialists',
        'qualifications': 'Bac si CKII Tai Mui Hong',
        'experience': '11 nam dieu tri viem xoang, viem hong va roi loan giong noi.',
        'biography': 'Tap trung dieu tri benh ly tai mui hong man tinh.',
        'hospital_name': 'Medic ENT Clinic',
        'location': 'Tang 5, 50 Pasteur, TP.HCM',
    },
    {
        'email': 'doctor.mat@medic.test',
        'first_name': 'Khoa',
        'last_name': 'Hoang',
        'phone_number': '0902000006',
        'gender': 'male',
        'specialization': 'Eye Care',
        'qualifications': 'Bac si Nhan khoa',
        'experience': '8 nam kham va dieu tri benh ly mat.',
        'biography': 'Chuyen kham mat, can thi, kho mat va theo doi vong mac.',
        'hospital_name': 'Medic Eye Center',
        'location': 'Phong 305, 280 Dien Bien Phu, TP.HCM',
    },
]


PATIENTS = [
    ('patient.minh@medic.test', 'Minh', 'Nguyen', '0912000001', 'male'),
    ('patient.huong@medic.test', 'Huong', 'Tran', '0912000002', 'female'),
    ('patient.long@medic.test', 'Long', 'Pham', '0912000003', 'male'),
    ('patient.thao@medic.test', 'Thao', 'Le', '0912000004', 'female'),
    ('patient.duc@medic.test', 'Duc', 'Vo', '0912000005', 'male'),
    ('patient.linh@medic.test', 'Linh', 'Hoang', '0912000006', 'female'),
    ('patient.tuan@medic.test', 'Tuan', 'Dang', '0912000007', 'male'),
    ('patient.ngoc@medic.test', 'Ngoc', 'Bui', '0912000008', 'female'),
]


class Command(BaseCommand):
    help = 'Create safe demo doctors, patients, appointments, EMR, chat, and health history.'

    def handle(self, *args, **options):
        today = timezone.localdate()

        with transaction.atomic():
            self._cleanup_demo_users()
            admin = self._create_admin()
            doctors = self._create_doctors()
            patients = self._create_patients()
            appointments = self._create_appointments(doctors, today)
            bookings = self._create_bookings(patients, appointments, today)
            self._create_health_history(patients)
            self._create_direct_messages(bookings)
            self._create_reviews(bookings)
            self._create_emr_records(bookings)
            self._create_realtime_notifications(admin, doctors, patients, bookings)

        self.stdout.write(self.style.SUCCESS('Demo data created successfully.'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Login accounts:'))
        self.stdout.write(f'  Admin:   admin.demo@{DEMO_DOMAIN} / {PASSWORD}')
        self.stdout.write(f'  Doctor:  {DOCTORS[0]["email"]} / {PASSWORD}')
        self.stdout.write(f'  Doctor:  {DOCTORS[1]["email"]} / {PASSWORD}')
        self.stdout.write(f'  Patient: {PATIENTS[0][0]} / {PASSWORD}')
        self.stdout.write(f'  Patient: {PATIENTS[1][0]} / {PASSWORD}')
        self.stdout.write('')
        self.stdout.write('Created:')
        self.stdout.write(f'  Doctors:      {len(doctors)}')
        self.stdout.write(f'  Patients:     {len(patients)}')
        self.stdout.write(f'  Appointments: {len(appointments)}')
        self.stdout.write(f'  Bookings:     {len(bookings)}')

    def _cleanup_demo_users(self):
        demo_users = User.objects.filter(email__endswith=f'@{DEMO_DOMAIN}')
        count = demo_users.count()
        demo_users.delete()
        self.stdout.write(f'Removed old demo users: {count}')

    def _create_admin(self):
        admin = User.objects.create_superuser(
            email=f'admin.demo@{DEMO_DOMAIN}',
            password=PASSWORD,
            first_name='Admin',
            last_name='Demo',
        )
        NotificationPreference.objects.get_or_create(user=admin)
        return admin

    def _create_doctors(self):
        doctors = []
        for item in DOCTORS:
            user = User.objects.create_user(
                email=item['email'],
                password=PASSWORD,
                role=UserRole.DOCTOR,
                first_name=item['first_name'],
                last_name=item['last_name'],
                phone_number=item['phone_number'],
                gender=item['gender'],
            )
            DoctorProfile.objects.create(
                user=user,
                specialization=item['specialization'],
                qualifications=item['qualifications'],
                experience=item['experience'],
                biography=item['biography'],
            )
            NotificationPreference.objects.get_or_create(user=user)
            doctors.append(user)
        return doctors

    def _create_patients(self):
        patients = []
        for email, first_name, last_name, phone_number, gender in PATIENTS:
            user = User.objects.create_user(
                email=email,
                password=PASSWORD,
                role=UserRole.PATIENT,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                gender=gender,
            )
            NotificationPreference.objects.get_or_create(user=user)
            patients.append(user)
        return patients

    def _create_appointments(self, doctors, today):
        appointments = []
        for idx, doctor in enumerate(doctors):
            meta = DOCTORS[idx]
            for day_offset in (-2, 0, 1, 2, 5, 8):
                appointment_date = today + datetime.timedelta(days=day_offset)
                appointment = Appointment.objects.create(
                    user=doctor,
                    full_name=f'BS. {doctor.first_name} {doctor.last_name}',
                    location=meta['location'],
                    qualification_name=meta['qualifications'][:100],
                    institute_name=meta['hospital_name'],
                    hospital_name=meta['hospital_name'],
                    department=meta['specialization'],
                    start_time=datetime.time(8, 0),
                    end_time=datetime.time(17, 0),
                    date=appointment_date,
                    is_active=True,
                )
                appointments.append(appointment)
        return appointments

    def _create_booking(self, *, patient, appointment, selected_time, status, message):
        booking = TakeAppointment.objects.create(
            user=patient,
            appointment=appointment,
            full_name=f'{patient.first_name} {patient.last_name}',
            phone_number=patient.phone_number or '0900000000',
            message=message,
            date=appointment.date,
            time=selected_time,
            status=status,
        )
        AppointmentChangeLog.objects.create(
            booking=booking,
            action=AppointmentChangeLog.ACTION_BOOKED,
            changed_by=patient,
            new_appointment=appointment,
            new_date=booking.date,
            new_time=booking.time,
            reason='Demo booking created by seed_demo_data.',
        )
        return booking

    def _create_bookings(self, patients, appointments, today):
        by_doctor_date = {
            (a.user.email, a.date): a
            for a in appointments
        }
        bookings = []
        specs = [d['email'] for d in DOCTORS]

        future_date = today + datetime.timedelta(days=5)
        near_future_date = today + datetime.timedelta(days=1)
        past_date = today + datetime.timedelta(days=-2)

        plan = [
            (patients[0], specs[0], future_date, datetime.time(9, 0), TakeAppointment.STATUS_CONFIRMED, 'Toi hay dau nguc nhe khi van dong.'),
            (patients[0], specs[1], near_future_date, datetime.time(10, 0), TakeAppointment.STATUS_PENDING, 'Toi muon kiem tra duong huyet va HbA1c.'),
            (patients[1], specs[0], today, datetime.time(8, 30), TakeAppointment.STATUS_ARRIVED, 'Da den kham, can tao EMR demo.'),
            (patients[1], specs[2], past_date, datetime.time(14, 0), TakeAppointment.STATUS_COMPLETED, 'Da kham xong, co benh an va danh gia.'),
            (patients[2], specs[3], future_date, datetime.time(13, 30), TakeAppointment.STATUS_CONFIRMED, 'Toi dau rang khi an do lanh.'),
            (patients[3], specs[4], near_future_date, datetime.time(15, 0), TakeAppointment.STATUS_CONFIRMED, 'Toi bi viem mui di ung keo dai.'),
            (patients[4], specs[5], future_date, datetime.time(8, 30), TakeAppointment.STATUS_PENDING, 'Toi muon kham kho mat.'),
            (patients[5], specs[1], past_date, datetime.time(9, 30), TakeAppointment.STATUS_COMPLETED, 'Da kham noi tiet xong.'),
            (patients[6], specs[2], future_date, datetime.time(11, 0), TakeAppointment.STATUS_CANCELLED, 'Demo lich da huy.'),
            (patients[7], specs[0], near_future_date, datetime.time(16, 0), TakeAppointment.STATUS_CONFIRMED, 'Toi muon tai kham tim mach.'),
        ]

        for patient, doctor_email, date, selected_time, status, message in plan:
            appointment = by_doctor_date[(doctor_email, date)]
            bookings.append(self._create_booking(
                patient=patient,
                appointment=appointment,
                selected_time=selected_time,
                status=status,
                message=message,
            ))
        return bookings

    def _create_health_history(self, patients):
        history_rows = [
            ('Heart Disease', 'Nguy co thap', {'age': 32, 'trestbps': 122, 'chol': 185}),
            ('Diabetes Disease', 'Can theo doi them', {'glucose': 148, 'bmi': 28.4, 'age': 45}),
            ('Breast Cancer', 'Khong phat hien nguy co cao', {'radius_mean': 13.2, 'texture_mean': 18.4}),
            ('Kidney Disease', 'Nguy co trung binh', {'bp': 135, 'sg': 1.015, 'al': 1}),
        ]
        for idx, patient in enumerate(patients):
            disease, result, input_data = history_rows[idx % len(history_rows)]
            MedicalHistory.objects.create(
                user=patient,
                disease_type=disease,
                prediction_result=result,
                input_data=input_data,
            )
            ChatMessage.objects.create(
                user=patient,
                sender=ChatMessage.SENDER_USER,
                message='Toi muon hoi ve ket qua sang loc gan day cua toi.',
            )
            ChatMessage.objects.create(
                user=patient,
                sender=ChatMessage.SENDER_BOT,
                message='Medic AI da ghi nhan ket qua sang loc va khuyen ban theo doi them voi bac si phu hop.',
            )

    def _create_direct_messages(self, bookings):
        for booking in bookings:
            if booking.status not in (TakeAppointment.STATUS_PENDING, TakeAppointment.STATUS_CONFIRMED):
                continue
            DirectMessage.objects.create(
                booking=booking,
                sender=booking.user,
                content='Chao bac si, toi can chuan bi gi truoc khi den kham?',
                is_read=True,
            )
            DirectMessage.objects.create(
                booking=booking,
                sender=booking.appointment.user,
                content='Ban vui long mang theo ket qua xet nghiem cu va den som 10 phut.',
                is_read=False,
            )

    def _create_reviews(self, bookings):
        for booking in bookings:
            if booking.status != TakeAppointment.STATUS_COMPLETED:
                continue
            DoctorReview.objects.create(
                doctor=booking.appointment.user,
                patient=booking.user,
                booking=booking,
                rating=5,
                comment='Bac si tu van ky, giao dien demo hien thi tot.',
            )

    def _create_emr_records(self, bookings):
        completed = [b for b in bookings if b.status == TakeAppointment.STATUS_COMPLETED]
        for idx, booking in enumerate(completed):
            record = EMRRecord.objects.create(
                appointment=booking,
                patient=booking.user,
                doctor=booking.appointment.user,
                symptoms='Met moi, dau nhe va can theo doi chi so suc khoe.',
                diagnosis='Tinh trang on dinh, can tiep tuc theo doi va tai kham neu co dau hieu bat thuong.',
                clinical_notes='Demo EMR: khong ghi nhan dau hieu cap cuu.',
                follow_up_plan='Tai kham sau 2-4 tuan hoac som hon neu trieu chung tang.',
            )
            VitalSign.objects.create(
                emr_record=record,
                weight_kg=Decimal('62.50') + idx,
                height_cm=Decimal('168.00'),
                blood_pressure_systolic=120 + idx,
                blood_pressure_diastolic=78,
                heart_rate=76,
                temperature_c=Decimal('36.8'),
            )
            PrescriptionItem.objects.create(
                emr_record=record,
                medicine_name='Paracetamol 500mg',
                dosage='1 vien',
                frequency='Khi dau hoac sot',
                duration='Toi da 3 ngay',
                instructions='Khong dung qua lieu, doc ky huong dan su dung.',
                order=1,
            )
            PrescriptionItem.objects.create(
                emr_record=record,
                medicine_name='Vitamin tong hop',
                dosage='1 vien',
                frequency='Moi ngay sau an sang',
                duration='14 ngay',
                instructions='Uong voi nhieu nuoc.',
                order=2,
            )

    def _create_realtime_notifications(self, admin, doctors, patients, bookings):
        for user in [admin, *doctors[:2], *patients[:2]]:
            RealtimeNotification.objects.create(
                user=user,
                title='Du lieu demo da san sang',
                message='Tai khoan nay co du lieu mau de test cac chuc nang Medic.',
                level=RealtimeNotification.LEVEL_INFO,
                category='demo',
                link='/',
                payload={'source': 'seed_demo_data'},
            )
        for booking in bookings[:4]:
            RealtimeNotification.objects.create(
                user=booking.appointment.user,
                title='Lich hen demo',
                message=f'{booking.full_name} co lich hen mau luc {booking.time.strftime("%H:%M")} ngay {booking.date.strftime("%d/%m/%Y")}.',
                level=RealtimeNotification.LEVEL_SUCCESS,
                category='appointment',
                link='/account/doctor/dashboard/',
                payload={'booking_id': booking.id},
            )
