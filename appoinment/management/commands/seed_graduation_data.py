import datetime
import random
import shutil
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
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
from notifications.models import (
    AppointmentNotificationLog,
    NotificationPreference,
    RealtimeNotification,
)


PASSWORD = 'Medic@2026'
ADMIN_EMAIL = 'admin@medic.test'
SAMPLE_DOCTOR_EMAIL = 'nguyenhoangminh120104@gmail.com'
SAMPLE_PATIENT_EMAIL = 'minhpro1201@gmail.com'
RANDOM_SEED = 20260627


DOCTOR_ROWS = [
    {
        'email': SAMPLE_DOCTOR_EMAIL,
        'first_name': 'Hoang Minh',
        'last_name': 'Nguyen',
        'gender': 'male',
        'phone': '0901000001',
        'specialization': 'Cardiology',
        'qualification': 'MSc Cardiology, University Medical Center',
        'experience_years': 11,
        'biography': 'Specialist in hypertension, chest pain, and coronary artery disease.',
    },
    {
        'email': 'doctor.heart01@medic.test',
        'first_name': 'Anh Khoa',
        'last_name': 'Tran',
        'gender': 'male',
        'phone': '0901000002',
        'specialization': 'Heart Disease',
        'qualification': 'Specialist Level II in Internal Medicine',
        'experience_years': 14,
        'biography': 'Focused on cardiovascular prevention, ECG analysis, and follow-up care.',
    },
    {
        'email': 'doctor.diabetes01@medic.test',
        'first_name': 'Thu Ha',
        'last_name': 'Le',
        'gender': 'female',
        'phone': '0901000003',
        'specialization': 'Diabetes Disease',
        'qualification': 'Endocrinology Specialist',
        'experience_years': 10,
        'biography': 'Experienced in diabetes management and metabolic risk counseling.',
    },
    {
        'email': 'doctor.oncology01@medic.test',
        'first_name': 'Minh Chau',
        'last_name': 'Pham',
        'gender': 'female',
        'phone': '0901000004',
        'specialization': 'Breast Cancer',
        'qualification': 'PhD Oncology',
        'experience_years': 13,
        'biography': 'Provides breast cancer screening, risk assessment, and follow-up plans.',
    },
    {
        'email': 'doctor.dental01@medic.test',
        'first_name': 'Quang Huy',
        'last_name': 'Vo',
        'gender': 'male',
        'phone': '0901000005',
        'specialization': 'Dentistry',
        'qualification': 'DDS, Dental Surgery',
        'experience_years': 9,
        'biography': 'General dentistry, dental restoration, and preventive oral care.',
    },
    {
        'email': 'doctor.ent01@medic.test',
        'first_name': 'Bao Ngoc',
        'last_name': 'Hoang',
        'gender': 'female',
        'phone': '0901000006',
        'specialization': 'ENT Specialists',
        'qualification': 'ENT Specialist Level I',
        'experience_years': 8,
        'biography': 'Treats sinusitis, throat inflammation, allergy, and voice disorders.',
    },
    {
        'email': 'doctor.eye01@medic.test',
        'first_name': 'Thanh Lam',
        'last_name': 'Bui',
        'gender': 'male',
        'phone': '0901000007',
        'specialization': 'Eye Care',
        'qualification': 'Ophthalmology Specialist',
        'experience_years': 7,
        'biography': 'Eye examination, dry eye care, refraction, and retinal follow-up.',
    },
    {
        'email': 'doctor.physio01@medic.test',
        'first_name': 'Gia Bao',
        'last_name': 'Dang',
        'gender': 'male',
        'phone': '0901000008',
        'specialization': 'Physical Therapy',
        'qualification': 'Rehabilitation Medicine Specialist',
        'experience_years': 12,
        'biography': 'Rehabilitation programs for sports injury and chronic joint pain.',
    },
    {
        'email': 'doctor.neuro01@medic.test',
        'first_name': 'Khanh Linh',
        'last_name': 'Do',
        'gender': 'female',
        'phone': '0901000009',
        'specialization': 'Neuroanatomy',
        'qualification': 'Neurology Specialist',
        'experience_years': 15,
        'biography': 'Neurological examination, headache care, and nerve function assessment.',
    },
    {
        'email': 'doctor.blood01@medic.test',
        'first_name': 'Duc Anh',
        'last_name': 'Ngo',
        'gender': 'male',
        'phone': '0901000010',
        'specialization': 'Blood Screening',
        'qualification': 'Hematology and Laboratory Medicine',
        'experience_years': 9,
        'biography': 'Blood test interpretation, anemia screening, and preventive checkups.',
    },
    {
        'email': 'doctor.cardio02@medic.test',
        'first_name': 'Thi Mai',
        'last_name': 'Phan',
        'gender': 'female',
        'phone': '0901000011',
        'specialization': 'Cardiology',
        'qualification': 'Cardiology Specialist',
        'experience_years': 16,
        'biography': 'Long-term care for heart failure, arrhythmia, and high blood pressure.',
    },
    {
        'email': 'doctor.diabetes02@medic.test',
        'first_name': 'Van Long',
        'last_name': 'Huynh',
        'gender': 'male',
        'phone': '0901000012',
        'specialization': 'Diabetes Disease',
        'qualification': 'MSc Endocrinology',
        'experience_years': 6,
        'biography': 'Lifestyle counseling, medication review, and diabetes complication screening.',
    },
    {
        'email': 'doctor.dental02@medic.test',
        'first_name': 'Nhat Nam',
        'last_name': 'Ly',
        'gender': 'male',
        'phone': '0901000013',
        'specialization': 'Dentistry',
        'qualification': 'Dental Implant and Aesthetic Dentistry',
        'experience_years': 10,
        'biography': 'Dental implants, cosmetic restoration, and oral disease prevention.',
    },
    {
        'email': 'doctor.eye02@medic.test',
        'first_name': 'Tra My',
        'last_name': 'Duong',
        'gender': 'female',
        'phone': '0901000014',
        'specialization': 'Eye Care',
        'qualification': 'Ophthalmologist',
        'experience_years': 8,
        'biography': 'Pediatric eye care, refractive errors, and digital eye strain.',
    },
    {
        'email': 'doctor.ent02@medic.test',
        'first_name': 'Minh Quan',
        'last_name': 'Tran',
        'gender': 'male',
        'phone': '0901000015',
        'specialization': 'ENT Specialists',
        'qualification': 'ENT Specialist Level II',
        'experience_years': 17,
        'biography': 'Advanced ENT consultation and chronic sinus treatment planning.',
    },
    {
        'email': 'doctor.oncology02@medic.test',
        'first_name': 'Phuong Anh',
        'last_name': 'Nguyen',
        'gender': 'female',
        'phone': '0901000016',
        'specialization': 'Breast Cancer',
        'qualification': 'Oncology Screening Specialist',
        'experience_years': 7,
        'biography': 'Breast health consultation, screening education, and risk monitoring.',
    },
]


MALE_FIRST_NAMES = [
    'An', 'Binh', 'Cuong', 'Duc', 'Hieu', 'Huy', 'Khoa', 'Long', 'Minh',
    'Nam', 'Phong', 'Quan', 'Son', 'Thang', 'Tuan', 'Viet',
]
FEMALE_FIRST_NAMES = [
    'An', 'Chau', 'Ha', 'Huong', 'Linh', 'Mai', 'Ngan', 'Ngoc', 'Nhi',
    'Phuong', 'Quyen', 'Thao', 'Trang', 'Uyen', 'Vy', 'Yen',
]
LAST_NAMES = [
    'Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Huynh', 'Phan', 'Vu',
    'Vo', 'Dang', 'Bui', 'Do', 'Ho', 'Ngo', 'Duong', 'Ly',
]
TIME_SLOTS = [
    datetime.time(8, 0), datetime.time(8, 30), datetime.time(9, 0),
    datetime.time(9, 30), datetime.time(10, 0), datetime.time(10, 30),
    datetime.time(13, 30), datetime.time(14, 0), datetime.time(14, 30),
    datetime.time(15, 0), datetime.time(15, 30), datetime.time(16, 0),
]
SYMPTOMS = [
    'I have mild chest discomfort when walking fast.',
    'I need a follow-up check after my previous test result.',
    'I feel tired and want a general health consultation.',
    'I have had symptoms for several days and need medical advice.',
    'I want to review my screening result with a specialist.',
    'I need advice about medication and lifestyle changes.',
]
DIAGNOSES = [
    'Stable condition, continue monitoring and lifestyle adjustment.',
    'No emergency sign recorded during this visit.',
    'Further monitoring is recommended based on the patient history.',
    'Symptoms improved after consultation and basic treatment.',
]
AI_DISEASE_TYPES = [
    'Heart Disease',
    'Diabetes Disease',
    'Breast Cancer',
    'Skin Cancer',
    'Pneumonia',
]


class Command(BaseCommand):
    help = 'Create graduation demo data: 1 admin, 16 doctors, 100 patients, and 1+ year of activity.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete current local demo data before creating the graduation dataset.',
        )

    def handle(self, *args, **options):
        random.seed(RANDOM_SEED)
        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=420)
        end_date = today + datetime.timedelta(days=45)

        if not options['reset'] and User.objects.exists():
            raise CommandError(
                'Users already exist. Re-run with --reset to replace local demo data.'
            )

        with transaction.atomic():
            if options['reset']:
                self._reset_database()

            doctor_images = self._prepare_doctor_images()
            admin = self._create_admin(start_date)
            doctors = self._create_doctors(doctor_images, start_date)
            patients = self._create_patients(start_date)
            appointments = self._create_appointments(doctors, start_date, end_date)
            bookings = self._create_bookings(patients, appointments, today)
            self._create_emr_reviews_and_messages(bookings)
            self._create_ai_history_and_chat(patients, start_date, today)
            self._create_notifications(admin, doctors, patients, bookings)

        self.stdout.write(self.style.SUCCESS('Graduation demo data created successfully.'))
        self.stdout.write('')
        self.stdout.write('Login accounts:')
        self.stdout.write(f'  Admin:   {ADMIN_EMAIL} / {PASSWORD}')
        self.stdout.write(f'  Doctor:  {SAMPLE_DOCTOR_EMAIL} / {PASSWORD}')
        self.stdout.write(f'  Patient: {SAMPLE_PATIENT_EMAIL} / {PASSWORD}')
        self.stdout.write('')
        self.stdout.write('Created data:')
        self.stdout.write('  Admin:        1')
        self.stdout.write(f'  Doctors:      {len(doctors)}')
        self.stdout.write(f'  Patients:     {len(patients)}')
        self.stdout.write(f'  Appointments: {len(appointments)}')
        self.stdout.write(f'  Bookings:     {len(bookings)}')
        self.stdout.write(f'  Date range:   {start_date.isoformat()} -> {end_date.isoformat()}')

    def _reset_database(self):
        AppointmentNotificationLog.objects.all().delete()
        RealtimeNotification.objects.all().delete()
        NotificationPreference.objects.all().delete()
        DirectMessage.objects.all().delete()
        DoctorReview.objects.all().delete()
        AppointmentChangeLog.objects.all().delete()
        PrescriptionItem.objects.all().delete()
        VitalSign.objects.all().delete()
        EMRRecord.objects.all().delete()
        MedicalHistory.objects.all().delete()
        ChatMessage.objects.all().delete()
        TakeAppointment.objects.all().delete()
        Appointment.objects.all().delete()
        DoctorProfile.objects.all().delete()
        User.objects.all().delete()

    def _aware_at(self, date_value, time_value=None):
        time_value = time_value or datetime.time(9, 0)
        naive = datetime.datetime.combine(date_value, time_value)
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def _prepare_doctor_images(self):
        source_dir = Path(settings.BASE_DIR) / 'PNG'
        if not source_dir.exists():
            raise CommandError(f'PNG folder was not found: {source_dir}')

        image_files = sorted([
            item for item in source_dir.iterdir()
            if item.is_file() and item.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}
        ])
        if len(image_files) < len(DOCTOR_ROWS):
            raise CommandError(
                f'Need at least {len(DOCTOR_ROWS)} doctor images in PNG folder, found {len(image_files)}.'
            )

        avatar_dir = Path(settings.MEDIA_ROOT) / 'avatars' / 'demo_doctors'
        avatar_dir.mkdir(parents=True, exist_ok=True)

        relative_paths = []
        for index, source in enumerate(image_files[:len(DOCTOR_ROWS)], start=1):
            suffix = ''.join(source.suffixes) or source.suffix
            target_name = f'doctor-{index:02d}{suffix.lower()}'
            target = avatar_dir / target_name
            shutil.copy2(source, target)
            relative_paths.append(f'avatars/demo_doctors/{target_name}')
        return relative_paths

    def _create_admin(self, start_date):
        admin = User.objects.create_superuser(
            email=ADMIN_EMAIL,
            password=PASSWORD,
            first_name='System',
            last_name='Admin',
            role=UserRole.DOCTOR,
        )
        joined_at = self._aware_at(start_date - datetime.timedelta(days=20))
        User.objects.filter(pk=admin.pk).update(date_joined=joined_at)
        NotificationPreference.objects.get_or_create(user=admin)
        return admin

    def _create_doctors(self, doctor_images, start_date):
        doctors = []
        for index, row in enumerate(DOCTOR_ROWS):
            joined_date = start_date + datetime.timedelta(days=random.randint(0, 60))
            user = User.objects.create_user(
                email=row['email'],
                password=PASSWORD,
                role=UserRole.DOCTOR,
                first_name=row['first_name'],
                last_name=row['last_name'],
                gender=row['gender'],
                phone_number=row['phone'],
                image=doctor_images[index],
            )
            User.objects.filter(pk=user.pk).update(date_joined=self._aware_at(joined_date))
            DoctorProfile.objects.create(
                user=user,
                specialization=row['specialization'],
                qualifications=row['qualification'],
                experience=f"{row['experience_years']} years of clinical experience",
                biography=row['biography'],
            )
            NotificationPreference.objects.get_or_create(user=user)
            doctors.append(user)
        return doctors

    def _create_patients(self, start_date):
        patients = []
        sample = User.objects.create_user(
            email=SAMPLE_PATIENT_EMAIL,
            password=PASSWORD,
            role=UserRole.PATIENT,
            first_name='Minh',
            last_name='Nguyen',
            gender='male',
            phone_number='0912000001',
        )
        User.objects.filter(pk=sample.pk).update(
            date_joined=self._aware_at(start_date + datetime.timedelta(days=3))
        )
        NotificationPreference.objects.get_or_create(user=sample)
        patients.append(sample)

        for index in range(2, 101):
            gender = random.choice(['male', 'female'])
            first_name = random.choice(MALE_FIRST_NAMES if gender == 'male' else FEMALE_FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            user = User.objects.create_user(
                email=f'patient{index:03d}@medic.test',
                password=PASSWORD,
                role=UserRole.PATIENT,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                phone_number=f'0912{index:06d}',
            )
            joined_date = start_date + datetime.timedelta(days=random.randint(0, 300))
            User.objects.filter(pk=user.pk).update(date_joined=self._aware_at(joined_date))
            NotificationPreference.objects.get_or_create(user=user)
            patients.append(user)
        return patients

    def _create_appointments(self, doctors, start_date, end_date):
        appointments = []
        current = start_date
        hospital_locations = [
            'Medic Center - Floor 2, Room 201',
            'Medic Center - Floor 3, Room 305',
            'Medic Clinic - Floor 4, Room 402',
            'Medic Specialist Center - Room A12',
        ]
        while current <= end_date:
            if current.weekday() != 6:
                for doctor in doctors:
                    profile = doctor.doctor_profile
                    start_time = datetime.time(8, 0)
                    appointment = Appointment.objects.create(
                        user=doctor,
                        full_name=f'Dr. {doctor.first_name} {doctor.last_name}',
                        image=doctor.image.name,
                        location=random.choice(hospital_locations),
                        qualification_name=profile.qualifications[:100],
                        institute_name='Medic Healthcare Institute',
                        hospital_name='Medic Hospital',
                        department=profile.specialization,
                        start_time=start_time,
                        end_time=datetime.time(17, 0),
                        date=current,
                        is_active=True,
                        created_at=self._aware_at(
                            min(current, timezone.localdate()) - datetime.timedelta(days=random.randint(3, 21)),
                            datetime.time(8, 0),
                        ),
                    )
                    appointments.append(appointment)
            current += datetime.timedelta(days=1)
        return appointments

    def _choose_status(self, appointment_date, today):
        if appointment_date < today:
            return random.choices(
                [TakeAppointment.STATUS_COMPLETED, TakeAppointment.STATUS_CANCELLED],
                weights=[84, 16],
                k=1,
            )[0]
        if appointment_date == today:
            return random.choices(
                [
                    TakeAppointment.STATUS_PENDING,
                    TakeAppointment.STATUS_CONFIRMED,
                    TakeAppointment.STATUS_ARRIVED,
                    TakeAppointment.STATUS_COMPLETED,
                    TakeAppointment.STATUS_CANCELLED,
                ],
                weights=[15, 40, 25, 15, 5],
                k=1,
            )[0]
        return random.choices(
            [
                TakeAppointment.STATUS_PENDING,
                TakeAppointment.STATUS_CONFIRMED,
                TakeAppointment.STATUS_CANCELLED,
            ],
            weights=[42, 48, 10],
            k=1,
        )[0]

    def _create_bookings(self, patients, appointments, today):
        past_appointments = [item for item in appointments if item.date < today]
        future_appointments = [item for item in appointments if item.date >= today]
        used_slots = set()
        bookings = []

        def create_one(
            patient,
            appointment,
            *,
            status_override=None,
            forced_time=None,
            message=None,
        ):
            for _attempt in range(60):
                selected_time = forced_time if _attempt == 0 and forced_time else random.choice(TIME_SLOTS)
                slot_key = (appointment.pk, selected_time)
                if slot_key not in used_slots:
                    used_slots.add(slot_key)
                    break
            else:
                return None

            status = status_override or self._choose_status(appointment.date, today)
            created_date = min(
                appointment.date - datetime.timedelta(days=random.randint(1, 20)),
                today,
            )
            created_at = self._aware_at(created_date, datetime.time(random.randint(7, 20), 0))
            cancelled_at = None
            if status == TakeAppointment.STATUS_CANCELLED:
                cancelled_at = created_at + datetime.timedelta(days=random.randint(1, 4))

            booking = TakeAppointment.objects.create(
                user=patient,
                appointment=appointment,
                full_name=f'{patient.first_name} {patient.last_name}',
                phone_number=patient.phone_number or '0900000000',
                message=message or random.choice(SYMPTOMS),
                date=appointment.date,
                time=selected_time,
                status=status,
                cancelled_at=cancelled_at,
                created_at=created_at,
            )
            log = AppointmentChangeLog.objects.create(
                booking=booking,
                action=AppointmentChangeLog.ACTION_BOOKED,
                changed_by=patient,
                new_appointment=appointment,
                new_date=appointment.date,
                new_time=selected_time,
                reason='Initial booking in graduation demo dataset.',
            )
            AppointmentChangeLog.objects.filter(pk=log.pk).update(created_at=created_at)

            if status == TakeAppointment.STATUS_CANCELLED:
                cancel_log = AppointmentChangeLog.objects.create(
                    booking=booking,
                    action=AppointmentChangeLog.ACTION_CANCELLED,
                    changed_by=patient,
                    old_appointment=appointment,
                    old_date=appointment.date,
                    old_time=selected_time,
                    reason='Patient cancelled this demo appointment.',
                )
                AppointmentChangeLog.objects.filter(pk=cancel_log.pk).update(
                    created_at=cancelled_at or created_at
                )
            bookings.append(booking)
            return booking

        for patient in patients:
            for _ in range(5):
                create_one(patient, random.choice(past_appointments))

        sample_doctor_slots = [
            item for item in appointments
            if item.user.email == SAMPLE_DOCTOR_EMAIL
        ]
        slots_by_date = {item.date: item for item in sample_doctor_slots}
        focus_plan = [
            (
                patients[0],
                slots_by_date.get(today),
                TakeAppointment.STATUS_ARRIVED,
                datetime.time(9, 0),
                'Demo focus: patient has arrived for the defense presentation.',
            ),
            (
                patients[1],
                slots_by_date.get(today),
                TakeAppointment.STATUS_CONFIRMED,
                datetime.time(10, 0),
                'Demo focus: confirmed appointment for today.',
            ),
            (
                patients[0],
                next((item for item in sample_doctor_slots if item.date > today), None),
                TakeAppointment.STATUS_CONFIRMED,
                datetime.time(14, 0),
                'Demo focus: upcoming appointment for the sample patient.',
            ),
            (
                patients[2],
                next((item for item in reversed(sample_doctor_slots) if item.date < today), None),
                TakeAppointment.STATUS_COMPLETED,
                datetime.time(15, 0),
                'Demo focus: completed historical appointment with EMR.',
            ),
        ]
        for patient, appointment, status, selected_time, message in focus_plan:
            if appointment is None:
                continue
            create_one(
                patient,
                appointment,
                status_override=status,
                forced_time=selected_time,
                message=message,
            )

        target_total = 1400
        all_pool = past_appointments + future_appointments
        while len(bookings) < target_total:
            patient = random.choice(patients)
            if random.random() < 0.9:
                appointment = random.choice(past_appointments)
            else:
                appointment = random.choice(future_appointments)
            create_one(patient, appointment)
        return bookings

    def _create_emr_reviews_and_messages(self, bookings):
        completed = [item for item in bookings if item.status == TakeAppointment.STATUS_COMPLETED]
        active = [
            item for item in bookings
            if item.status in (TakeAppointment.STATUS_PENDING, TakeAppointment.STATUS_CONFIRMED)
        ]

        for index, booking in enumerate(completed):
            if random.random() < 0.65:
                created_at = self._aware_at(booking.date, datetime.time(booking.time.hour, 20))
                record = EMRRecord.objects.create(
                    appointment=booking,
                    patient=booking.user,
                    doctor=booking.appointment.user,
                    symptoms=booking.message,
                    diagnosis=random.choice(DIAGNOSES),
                    clinical_notes='Demo record generated for graduation presentation.',
                    follow_up_plan='Follow up in 2 to 4 weeks if symptoms continue.',
                )
                EMRRecord.objects.filter(pk=record.pk).update(
                    created_at=created_at,
                    updated_at=created_at + datetime.timedelta(minutes=8),
                )
                VitalSign.objects.create(
                    emr_record=record,
                    weight_kg=Decimal(str(random.randint(48, 88))) + Decimal('0.50'),
                    height_cm=Decimal(str(random.randint(150, 185))) + Decimal('0.00'),
                    blood_pressure_systolic=random.randint(105, 145),
                    blood_pressure_diastolic=random.randint(65, 95),
                    heart_rate=random.randint(62, 98),
                    temperature_c=Decimal(str(random.choice(['36.4', '36.6', '36.8', '37.0']))),
                )
                PrescriptionItem.objects.create(
                    emr_record=record,
                    medicine_name=random.choice(['Paracetamol 500mg', 'Vitamin B Complex', 'Oral Rehydration Salt']),
                    dosage='1 tablet',
                    frequency='After meals when needed',
                    duration='3 to 5 days',
                    instructions='Follow doctor instructions and return if symptoms get worse.',
                    order=1,
                )

            if random.random() < 0.35:
                review = DoctorReview.objects.create(
                    doctor=booking.appointment.user,
                    patient=booking.user,
                    booking=booking,
                    rating=random.choices([4, 5], weights=[35, 65], k=1)[0],
                    comment=random.choice([
                        'The doctor explained clearly and the booking process was convenient.',
                        'Good consultation experience and friendly staff.',
                        'The system helped me track my appointment easily.',
                    ]),
                )
                DoctorReview.objects.filter(pk=review.pk).update(
                    created_at=self._aware_at(booking.date, datetime.time(18, 0))
                )

        for booking in active[:220]:
            created_at = booking.created_at + datetime.timedelta(hours=2)
            msg1 = DirectMessage.objects.create(
                booking=booking,
                sender=booking.user,
                content='Doctor, should I bring my previous test results?',
                is_read=True,
            )
            msg2 = DirectMessage.objects.create(
                booking=booking,
                sender=booking.appointment.user,
                content='Yes, please bring old prescriptions and test results if available.',
                is_read=random.choice([True, False]),
            )
            DirectMessage.objects.filter(pk=msg1.pk).update(created_at=created_at)
            DirectMessage.objects.filter(pk=msg2.pk).update(
                created_at=created_at + datetime.timedelta(minutes=14)
            )

    def _create_ai_history_and_chat(self, patients, start_date, today):
        for patient in patients:
            for _ in range(3):
                created_date = start_date + datetime.timedelta(
                    days=random.randint(0, max((today - start_date).days, 1))
                )
                history = MedicalHistory.objects.create(
                    user=patient,
                    disease_type=random.choice(AI_DISEASE_TYPES),
                    prediction_result=random.choice([
                        'Low risk',
                        'Medium risk - follow up recommended',
                        'High risk - please consult a doctor',
                        'No abnormal sign detected',
                    ]),
                    input_data={
                        'age': random.randint(18, 78),
                        'heart_rate': random.randint(60, 105),
                        'bmi': round(random.uniform(18.5, 31.5), 1),
                    },
                )
                MedicalHistory.objects.filter(pk=history.pk).update(
                    created_at=self._aware_at(created_date, datetime.time(random.randint(8, 21), 0))
                )

            chat_date = start_date + datetime.timedelta(days=random.randint(20, 380))
            user_msg = ChatMessage.objects.create(
                user=patient,
                sender=ChatMessage.SENDER_USER,
                message='Can Medic AI help me understand my recent screening result?',
            )
            bot_msg = ChatMessage.objects.create(
                user=patient,
                sender=ChatMessage.SENDER_BOT,
                message='Medic AI can provide preliminary guidance, but you should confirm results with a doctor.',
            )
            ChatMessage.objects.filter(pk=user_msg.pk).update(
                created_at=self._aware_at(chat_date, datetime.time(20, 5))
            )
            ChatMessage.objects.filter(pk=bot_msg.pk).update(
                created_at=self._aware_at(chat_date, datetime.time(20, 6))
            )

    def _create_notifications(self, admin, doctors, patients, bookings):
        for booking in bookings[:60]:
            event = (
                'booking_cancelled'
                if booking.status == TakeAppointment.STATUS_CANCELLED
                else 'booking_confirmed'
            )
            log = AppointmentNotificationLog.objects.create(
                appointment=booking,
                recipient=booking.user,
                channel='email',
                event=event,
                status='sent',
                booking_version=booking.notification_version,
                sent_at=booking.created_at + datetime.timedelta(minutes=2),
                created_at=booking.created_at,
            )
            AppointmentNotificationLog.objects.filter(pk=log.pk).update(
                created_at=booking.created_at
            )
