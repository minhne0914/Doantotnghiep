import os
import django

# Setup environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlhospital.settings')
django.setup()

from accounts.models import User
from appoinment.models import Appointment, TakeAppointment
from notifications.orchestrators import schedule_booking_notifications
from django.utils import timezone

from notifications.orchestrators import queue_email, get_context
from notifications.models import NotificationPreference
import datetime

def test_send_mail():
    print("="*60)
    print(" TEST TOÀN DIỆN 5 LOẠI EMAIL THÔNG BÁO ".center(60, "="))
    print("="*60)

    patient_email = "minhpro1201@gmail.com"
    patient, _ = User.objects.get_or_create(
        email=patient_email,
        defaults={'first_name': 'Giáo sư', 'last_name': 'Minh', 'role': 'patient', 'phone_number': '0999999999', 'is_active': True}
    )

    now = timezone.localtime()
    doctor_app = Appointment.objects.filter(is_active=True, date__gte=now.date()).first()
    
    if not doctor_app:
        print("[!] Không có ca làm việc nào để test.")
        return

    # Xóa lịch cũ 
    TakeAppointment.objects.filter(user=patient, appointment=doctor_app).delete()

    booking = TakeAppointment.objects.create(
        user=patient,
        appointment=doctor_app,
        full_name=f"{patient.first_name} {patient.last_name}",
        phone_number=patient.phone_number,
        message="Test gửi các loại Mail",
        date=doctor_app.date,
        time=doctor_app.start_time,
        status=TakeAppointment.STATUS_CONFIRMED,
    )
    
    pref, _ = NotificationPreference.objects.get_or_create(user=patient)
    pref.email_enabled = True
    pref.save()

    context = get_context(booking)
    
    # 1. Email Nhắc Nhở 24h
    print("[*] Đang gửi Mail Nhắc hẹn trước 24 giờ...")
    queue_email(booking, patient, 'reminder_24h', 'Nhắc lịch khám trước 24 giờ', 'emails/reminder_24h.html', context)
    
    # 2. Email Nhắc Nhở 1h (Gần tới hạn)
    print("[*] Đang gửi Mail Nhắc khẩn cấp trước 1 giờ...")
    queue_email(booking, patient, 'reminder_1h', 'GẦN TỚI HẸN: Nhắc lịch khám trước 1 giờ', 'emails/reminder_1h.html', context)
    
    # 3. Email Lịch Khám bị hủy
    print("[*] Đang gửi Mail Hủy Lịch Khám...")
    context['cancelled_by'] = 'patient'
    queue_email(booking, patient, 'booking_cancelled', 'Lịch khám đã bị hủy', 'emails/booking_cancelled_patient.html', context)
    
    # 4. Email Đổi Lịch Khám (Rescheduled)
    print("[*] Đang gửi Mail Đổi Lịch Khám...")
    context['previous_date'] = (doctor_app.date - datetime.timedelta(days=1)).strftime('%d/%m/%Y')
    context['previous_time'] = "08:00"
    queue_email(booking, patient, 'booking_rescheduled', 'Lịch khám đã được thay đổi', 'emails/booking_rescheduled_patient.html', context)

    print("\n[+] HOÀN TẤT: Hệ thống đã bắn 4 Email (Nhắc 24h, Nhắc 1h, Hủy lịch, Đổi lịch) vào hòm thư của bạn!")
    print(f"👉 Hãy vào hộp thư {patient_email} để xem trực tiếp các mẫu thiết kế nhé.")
    print("="*60)

if __name__ == "__main__":
    test_send_mail()
