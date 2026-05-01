"""
Seed data cho project Medic.
Tạo: 1 admin, 5 bác sĩ, 10 bệnh nhân, khung khám + 20 booking.
Chạy: python manage.py shell < seed_data.py
"""
import datetime
import random
import sys
import io

# Fix Windows terminal encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from django.utils import timezone

from accounts.models import DoctorProfile, User, UserRole
from appoinment.models import Appointment, DEPARTMENT_CHOICES, TakeAppointment
from notifications.models import NotificationPreference

print("=" * 60)
print("SEEDING DATABASE...")
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

# ================================================================
# 2. BÁC SĨ (5)
# ================================================================
DOCTORS_DATA = [
    {
        "email": "bs.nguyen.van.a@medic.vn",
        "first_name": "Văn A",
        "last_name": "Nguyễn",
        "phone": "0901000001",
        "gender": "male",
        "specialization": "Heart Disease",
        "qualifications": "Tiến sĩ Y khoa, ĐH Y Dược TP.HCM",
        "experience": "15 năm kinh nghiệm Tim mạch can thiệp",
        "hospital": "Bệnh viện Chợ Rẫy",
        "location": "201B Nguyễn Chí Thanh, Q.5, TP.HCM",
    },
    {
        "email": "bs.tran.thi.b@medic.vn",
        "first_name": "Thị B",
        "last_name": "Trần",
        "phone": "0901000002",
        "gender": "female",
        "specialization": "Diabetes Disease",
        "qualifications": "Thạc sĩ Nội tiết, ĐH Y Hà Nội",
        "experience": "10 năm kinh nghiệm Nội tiết - Đái tháo đường",
        "hospital": "Bệnh viện Bạch Mai",
        "location": "78 Giải Phóng, Đống Đa, Hà Nội",
    },
    {
        "email": "bs.le.van.c@medic.vn",
        "first_name": "Văn C",
        "last_name": "Lê",
        "phone": "0901000003",
        "gender": "male",
        "specialization": "Breast Cancer",
        "qualifications": "Phó Giáo sư, Tiến sĩ Ung bướu",
        "experience": "20 năm kinh nghiệm Ung thư vú",
        "hospital": "Bệnh viện Ung Bướu TP.HCM",
        "location": "3 Nơ Trang Long, Bình Thạnh, TP.HCM",
    },
    {
        "email": "bs.pham.thi.d@medic.vn",
        "first_name": "Thị D",
        "last_name": "Phạm",
        "phone": "0901000004",
        "gender": "female",
        "specialization": "Dentistry",
        "qualifications": "Bác sĩ CKI Răng Hàm Mặt",
        "experience": "8 năm kinh nghiệm Nha khoa thẩm mỹ",
        "hospital": "Nha khoa Sài Gòn",
        "location": "123 Lê Lợi, Q.1, TP.HCM",
    },
    {
        "email": "bs.hoang.van.e@medic.vn",
        "first_name": "Văn E",
        "last_name": "Hoàng",
        "phone": "0901000005",
        "gender": "male",
        "specialization": "Eye Care",
        "qualifications": "Tiến sĩ Nhãn khoa, ĐH Y Dược Huế",
        "experience": "12 năm kinh nghiệm phẫu thuật Mắt",
        "hospital": "Bệnh viện Mắt TP.HCM",
        "location": "280 Điện Biên Phủ, Q.3, TP.HCM",
    },
]

doctors = []
for d in DOCTORS_DATA:
    user = User(
        email=d["email"],
        first_name=d["first_name"],
        last_name=d["last_name"],
        phone_number=d["phone"],
        gender=d["gender"],
        role=UserRole.DOCTOR,
    )
    user.set_password(PASSWORD)
    user._bypass_role_check = True
    user.save()

    DoctorProfile.objects.create(
        user=user,
        specialization=d["specialization"],
        qualifications=d["qualifications"],
        experience=d["experience"],
        biography=f"BS. {d['first_name']} {d['last_name']} - chuyên khoa {d['specialization']}",
    )
    NotificationPreference.objects.get_or_create(user=user)
    doctors.append((user, d))
    print(f"[+] Bác sĩ: {user.email} ({d['specialization']})")

# ================================================================
# 3. BỆNH NHÂN (10)
# ================================================================
PATIENTS_DATA = [
    {"email": "bn.minh@medic.vn", "first_name": "Minh", "last_name": "Nguyễn", "phone": "0911000001", "gender": "male"},
    {"email": "bn.huong@medic.vn", "first_name": "Hương", "last_name": "Trần", "phone": "0911000002", "gender": "female"},
    {"email": "bn.long@medic.vn", "first_name": "Long", "last_name": "Phạm", "phone": "0911000003", "gender": "male"},
    {"email": "bn.thao@medic.vn", "first_name": "Thảo", "last_name": "Lê", "phone": "0911000004", "gender": "female"},
    {"email": "bn.duc@medic.vn", "first_name": "Đức", "last_name": "Võ", "phone": "0911000005", "gender": "male"},
    {"email": "bn.linh@medic.vn", "first_name": "Linh", "last_name": "Hoàng", "phone": "0911000006", "gender": "female"},
    {"email": "bn.tuan@medic.vn", "first_name": "Tuấn", "last_name": "Đặng", "phone": "0911000007", "gender": "male"},
    {"email": "bn.ngoc@medic.vn", "first_name": "Ngọc", "last_name": "Bùi", "phone": "0911000008", "gender": "female"},
    {"email": "bn.khoa@medic.vn", "first_name": "Khoa", "last_name": "Huỳnh", "phone": "0911000009", "gender": "male"},
    {"email": "bn.mai@medic.vn", "first_name": "Mai", "last_name": "Đỗ", "phone": "0911000010", "gender": "female"},
]

patients = []
for p in PATIENTS_DATA:
    user = User(
        email=p["email"],
        first_name=p["first_name"],
        last_name=p["last_name"],
        phone_number=p["phone"],
        gender=p["gender"],
        role=UserRole.PATIENT,
    )
    user.set_password(PASSWORD)
    user._bypass_role_check = True
    user.save()
    NotificationPreference.objects.get_or_create(user=user)
    patients.append(user)
    print(f"[+] Bệnh nhân: {user.email}")

# ================================================================
# 4. KHUNG KHÁM (Appointment) - mỗi bác sĩ 3 ngày tới
# ================================================================
appointments = []
for doc_user, doc_data in doctors:
    for day_offset in range(3):  # hôm nay, mai, mốt
        apt_date = today + datetime.timedelta(days=day_offset)
        apt = Appointment.objects.create(
            user=doc_user,
            full_name=f"BS. {doc_data['first_name']} {doc_data['last_name']}",
            location=doc_data["location"],
            qualification_name=doc_data["qualifications"][:100],
            institute_name=doc_data["hospital"],
            hospital_name=doc_data["hospital"],
            department=doc_data["specialization"],
            start_time=datetime.time(8, 0),
            end_time=datetime.time(17, 0),
            date=apt_date,
            is_active=True,
        )
        appointments.append(apt)
    print(f"[+] Tạo 3 khung khám cho BS. {doc_data['last_name']}")

# ================================================================
# 5. BOOKING (20) - phân bổ cho bệnh nhân
# ================================================================
TIME_SLOTS = [
    datetime.time(8, 0),
    datetime.time(8, 30),
    datetime.time(9, 0),
    datetime.time(9, 30),
    datetime.time(10, 0),
    datetime.time(10, 30),
    datetime.time(11, 0),
    datetime.time(13, 0),
    datetime.time(13, 30),
    datetime.time(14, 0),
    datetime.time(14, 30),
    datetime.time(15, 0),
    datetime.time(15, 30),
    datetime.time(16, 0),
    datetime.time(16, 30),
]

STATUSES = [
    TakeAppointment.STATUS_CONFIRMED,
    TakeAppointment.STATUS_CONFIRMED,
    TakeAppointment.STATUS_CONFIRMED,
    TakeAppointment.STATUS_PENDING,
    TakeAppointment.STATUS_ARRIVED,
]

booking_count = 0
used_slots = {}  # (appointment_id, time) -> True

for i in range(20):
    patient = patients[i % len(patients)]
    apt = appointments[i % len(appointments)]

    # Tìm slot trống
    available = [t for t in TIME_SLOTS if (apt.id, t) not in used_slots]
    if not available:
        continue
    slot_time = available[0]
    used_slots[(apt.id, slot_time)] = True

    status = STATUSES[i % len(STATUSES)]

    booking = TakeAppointment.objects.create(
        user=patient,
        appointment=apt,
        full_name=f"{patient.first_name} {patient.last_name}",
        phone_number=patient.phone_number or "0900000000",
        message=f"Tôi muốn khám {apt.department}. Xin hẹn bác sĩ.",
        date=apt.date,
        time=slot_time,
        status=status,
    )
    booking_count += 1
    print(f"[+] Booking #{booking.id}: {patient.first_name} -> BS.{apt.user.last_name} ({apt.date} {slot_time}) [{status}]")

# ================================================================
# SUMMARY
# ================================================================
print("\n" + "=" * 60)
print("SEED HOÀN TẤT!")
print("=" * 60)
print(f"  Admin:      1  (admin@medic.vn)")
print(f"  Bác sĩ:     {len(doctors)}")
print(f"  Bệnh nhân:  {len(patients)}")
print(f"  Khung khám:  {len(appointments)}")
print(f"  Booking:     {booking_count}")
print(f"  Mật khẩu:    {PASSWORD}")
print("=" * 60)
