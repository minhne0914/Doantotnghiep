"""
Seed data LỚN cho project Medic.
Tạo: 1 admin, 50 bác sĩ, 500 bệnh nhân, khung khám trong 14 ngày tới + 2000 booking.
Chạy: python manage.py shell < seed_large_data.py
"""
import datetime
import random
import sys
import io

# Fix Windows terminal encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from django.utils import timezone
from django.db import transaction

from accounts.models import DoctorProfile, User, UserRole
from appoinment.models import Appointment, DEPARTMENT_CHOICES, TakeAppointment
from notifications.models import NotificationPreference

print("=" * 60)
print("SEEDING LARGE DATABASE...")
print("=" * 60)

PASSWORD = "Medic@2026"
today = timezone.localdate()

# ================================================================
# 0. CLEANUP - xóa data seed cũ (nếu có)
# ================================================================
print("[*] Dọn dẹp data cũ...")
TakeAppointment.objects.all().delete()
Appointment.objects.all().delete()
DoctorProfile.objects.all().delete()
NotificationPreference.objects.all().delete()
User.objects.all().delete()
print("[*] Đã xóa sạch.")

# ================================================================
# 1. ADMIN
# ================================================================
admin = User.objects.create_superuser(
    email="admin@medic.vn",
    password=PASSWORD,
    first_name="Admin",
    last_name="Medic",
)
admin._bypass_role_check = True
admin.role = UserRole.DOCTOR
admin.save()
print(f"[+] Admin: {admin.email}")

# Dữ liệu random
FIRST_NAMES_MALE = ["Anh", "Bình", "Cường", "Dũng", "Đức", "Hoàng", "Huy", "Khoa", "Long", "Minh", "Nam", "Phúc", "Quân", "Sơn", "Thắng", "Tuấn", "Việt"]
FIRST_NAMES_FEMALE = ["An", "Châu", "Diệp", "Hà", "Hương", "Linh", "Mai", "Ngân", "Ngọc", "Nhung", "Oanh", "Phương", "Quyên", "Thảo", "Trang", "Uyên", "Yến"]
LAST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
DEPARTMENTS = ["Cardiology", "Dermatology", "Neurology", "Orthopedics", "Pediatrics", "Psychiatry", "Radiology", "Urology", "Dentistry", "Eye Care"]

# ================================================================
# 2. BÁC SĨ (50)
# ================================================================
print("[*] Đang tạo 50 Bác sĩ...")
doctors = []
with transaction.atomic():
    for i in range(1, 51):
        gender = random.choice(["male", "female"])
        first_name = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        email = f"doctor{i}_{first_name.lower()}@medic.vn"
        phone = f"090{random.randint(1000000, 9999999)}"
        spec = random.choice(DEPARTMENTS)

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            gender=gender,
            role=UserRole.DOCTOR,
        )
        user.set_password(PASSWORD)
        user._bypass_role_check = True
        user.save()

        DoctorProfile.objects.create(
            user=user,
            specialization=spec,
            qualifications=f"Bác sĩ chuyên khoa {spec}",
            experience=f"{random.randint(5, 25)} năm kinh nghiệm",
            biography=f"BS. {first_name} {last_name} có nhiều năm kinh nghiệm trong lĩnh vực {spec}.",
        )
        NotificationPreference.objects.get_or_create(user=user)
        doctors.append((user, spec))

print(f"[+] Tạo thành công {len(doctors)} bác sĩ.")

# ================================================================
# 3. BỆNH NHÂN (500)
# ================================================================
print("[*] Đang tạo 500 Bệnh nhân...")
patients = []
with transaction.atomic():
    for i in range(1, 501):
        gender = random.choice(["male", "female"])
        first_name = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        email = f"patient{i}_{first_name.lower()}@medic.vn"
        phone = f"091{random.randint(1000000, 9999999)}"

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            gender=gender,
            role=UserRole.PATIENT,
        )
        user.set_password(PASSWORD)
        user._bypass_role_check = True
        user.save()
        NotificationPreference.objects.get_or_create(user=user)
        patients.append(user)

print(f"[+] Tạo thành công {len(patients)} bệnh nhân.")

# ================================================================
# 4. KHUNG KHÁM (Appointment) - mỗi bác sĩ 14 ngày tới
# ================================================================
print("[*] Đang tạo Khung khám (mỗi bác sĩ 14 ngày tới)...")
appointments = []
with transaction.atomic():
    for doc_user, spec in doctors:
        for day_offset in range(14):
            apt_date = today + datetime.timedelta(days=day_offset)
            # Skip Sunday
            if apt_date.weekday() == 6:
                continue

            apt = Appointment.objects.create(
                user=doc_user,
                full_name=f"BS. {doc_user.first_name} {doc_user.last_name}",
                location="Medic Hospital",
                qualification_name=f"Chuyên khoa {spec}",
                institute_name="Medic Hospital",
                hospital_name="Medic Hospital",
                department=spec,
                start_time=datetime.time(8, 0),
                end_time=datetime.time(17, 0),
                date=apt_date,
                is_active=True,
            )
            appointments.append(apt)

print(f"[+] Tạo thành công {len(appointments)} khung khám.")

# ================================================================
# 5. BOOKING (2000)
# ================================================================
print("[*] Đang tạo 2000 Bookings...")
TIME_SLOTS = [
    datetime.time(8, 0), datetime.time(8, 30), datetime.time(9, 0), datetime.time(9, 30),
    datetime.time(10, 0), datetime.time(10, 30), datetime.time(11, 0),
    datetime.time(13, 0), datetime.time(13, 30), datetime.time(14, 0), datetime.time(14, 30),
    datetime.time(15, 0), datetime.time(15, 30), datetime.time(16, 0), datetime.time(16, 30),
]

STATUSES = [
    TakeAppointment.STATUS_CONFIRMED,
    TakeAppointment.STATUS_CONFIRMED,
    TakeAppointment.STATUS_PENDING,
    TakeAppointment.STATUS_ARRIVED,
    TakeAppointment.STATUS_PENDING,
]

booking_count = 0
with transaction.atomic():
    for _ in range(2000):
        patient = random.choice(patients)
        apt = random.choice(appointments)
        slot_time = random.choice(TIME_SLOTS)
        status = random.choices(STATUSES, weights=[50, 50, 20, 10, 5])[0]

        TakeAppointment.objects.create(
            user=patient,
            appointment=apt,
            full_name=f"{patient.first_name} {patient.last_name}",
            phone_number=patient.phone_number or "0900000000",
            message=f"Tôi muốn khám {apt.department}. Triệu chứng đau nhức.",
            date=apt.date,
            time=slot_time,
            status=status,
        )
        booking_count += 1

print(f"[+] Tạo thành công {booking_count} bookings.")

# ================================================================
# SUMMARY
# ================================================================
print("\n" + "=" * 60)
print("SEED HOÀN TẤT!")
print("=" * 60)
print(f"  Admin:       1  (admin@medic.vn)")
print(f"  Bác sĩ:      {len(doctors)}")
print(f"  Bệnh nhân:   {len(patients)}")
print(f"  Khung khám:  {len(appointments)}")
print(f"  Booking:     {booking_count}")
print(f"  Mật khẩu chung: {PASSWORD}")
print("=" * 60)
