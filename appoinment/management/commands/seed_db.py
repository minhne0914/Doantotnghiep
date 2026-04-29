from django.core.management.base import BaseCommand
from accounts.models import User, DoctorProfile
from appoinment.models import Appointment, TakeAppointment, DirectMessage, DoctorReview
from home.models import MedicalHistory, ChatMessage
from django.utils import timezone
import datetime
import random

class Command(BaseCommand):
    help = 'Tự động tạo Dữ liệu Mẫu (Seed Data) cho hệ thống Quản Lý Bệnh Viện'

    def handle(self, *args, **kwargs):
        self.stdout.write("Đang tiến hành dọn dẹp cơ sở dữ liệu...")
        
        # Xóa Dữ liệu cũ để làm sạch rác (ngoại trừ admin cứng nếu muốn, ở đây ta xóa luôn các user thường)
        TakeAppointment.objects.all().delete()
        Appointment.objects.all().delete()
        DirectMessage.objects.all().delete()
        DoctorReview.objects.all().delete()
        MedicalHistory.objects.all().delete()
        ChatMessage.objects.all().delete()
        # Không xóa superuser để giữ tài khoản admin
        User.objects.filter(is_superuser=False).delete()

        # 0. TẠO SUPERUSER (NẾU CHƯA CÓ)
        if not User.objects.filter(email='admin@gmail.com').exists():
            User.objects.create_superuser(
                email='admin@gmail.com', 
                password='1', 
                first_name='Giám Đốc', 
                last_name='Điều Hành'
            )
            self.stdout.write(self.style.SUCCESS("Đã tạo Superuser: admin@gmail.com / Pass: 1"))

        # 1. TẠO 5 BÁC SĨ (KÈM DOCTOR PROFILE)
        self.stdout.write("Đang tạo 5 Bác Sĩ...")
        doctor_data = [
            ("Tim Mạch", "Cardiology", "Trần Trái Tim", "Tốt nghiệp Y Dược TPHCM, Y khoa Harvard. Chuyên gia 15 năm kinh nghiệm mổ tim."),
            ("Đái tháo đường", "Diabetes Disease", "Nguyễn Tiểu Đường", "Bác sĩ nội tiết 10 năm kinh nghiệm."),
            ("Nha Khoa", "Dentistry", "Lê Răng Sứ", "Bác sĩ chuyên khoa Răng Hàm Mặt, tu nghiệp tại Mỹ."),
            ("Tai Mũi Họng", "ENT Specialists", "Phạm Khịt Khịt", "Trưởng khoa Tai Mũi Họng BV Chợ Rẫy."),
            ("Xương Khớp", "Physical Therapy", "Hoàng Cột Sống", "Chuyên gia vật lý trị liệu, chấn thương chỉnh hình.")
        ]
        
        doctors = []
        for i, doc in enumerate(doctor_data):
            spec_vn, spec_en, name, bio = doc
            user = User.objects.create_user(
                email=f'doctor{i+1}@gmail.com',
                password='1',
                first_name='Bác sĩ',
                last_name=name,
                role='doctor',
                phone_number=f'090100000{i}',
            )
            # Khởi tạo thông tin cá nhân bác sĩ
            DoctorProfile.objects.create(
                user=user,
                specialization=spec_en,
                qualifications='Tiến sĩ Y Khoa',
                experience=f'Hơn 10 năm kinh nghiệm trong khoa {spec_vn}',
                biography=bio
            )
            doctors.append(user)
        
        # 2. TẠO 10 BỆNH NHÂN
        self.stdout.write("Đang tạo 10 Bệnh Nhân...")
        patients = []
        for i in range(1, 11):
            user = User.objects.create_user(
                email=f'patient{i}@gmail.com',
                password='1',
                first_name='Bệnh nhân',
                last_name=f'Mẫu Số {i}',
                role='patient',
                phone_number=f'09880000{i:02d}',
            )
            patients.append(user)

        # 3. TẠO DATA CHAT AI & MEDICAL HISTORY CHO BỆNH NHÂN
        self.stdout.write("Đang khởi tạo Lịch sử Machine Learning...")
        for patient in patients:
            # Logs trò chuyện AI
            ChatMessage.objects.create(user=patient, sender=ChatMessage.SENDER_USER, message="Xin chào bác sĩ máy tính, tôi bị đau bụng liên hồi và hay chóng mặt.")
            ChatMessage.objects.create(user=patient, sender=ChatMessage.SENDER_BOT, message="Chào bạn, triệu chứng này có thể do căng thẳng hoặc rối loạn tiền đình. Bạn nên đặt lịch khám sớm.")
            
            # Logs Hồ sơ sức khỏe dự đoán AI
            MedicalHistory.objects.create(
                user=patient,
                disease_type=random.choice(["Heart Disease", "Diabetes Disease", "Breast Cancer"]),
                prediction_result=random.choice(["Nguy cơ cực cao", "An toàn", "Khả năng mắc 45%"]),
                input_data={"feature_1": round(random.uniform(0, 1), 2), "feature_2": round(random.uniform(10, 50), 2)}
            )

        # 4. TẠO LỊCH LÀM VIỆC VÀ LỊCH HẸN TRẢI DÀI
        self.stdout.write("Đang lên Lên Ca Trực và tạo Lịch Hẹn Đặt Chỗ...")
        now = timezone.localtime()
        statuses = [TakeAppointment.STATUS_PENDING, TakeAppointment.STATUS_CONFIRMED, TakeAppointment.STATUS_ARRIVED, TakeAppointment.STATUS_COMPLETED, TakeAppointment.STATUS_CANCELLED]
        
        for doctor in doctors:
            # Tạo 15 khung giờ làm việc ngẫu nhiên cho mỗi bác sĩ
            for i in range(15):
                days_offset = random.randint(-10, 10) # Trải dài trong 20 ngày
                app_date = now.date() + datetime.timedelta(days=days_offset)
                hour = random.randint(7, 18) # Trong giờ hành chính
                
                start_time = datetime.time(hour, 0)
                end_time = datetime.time(hour, 30)
                
                # Ca làm việc (Khung trống trong Calendar)
                appointment = Appointment.objects.create(
                    user=doctor,
                    full_name=f"{doctor.first_name} {doctor.last_name}",
                    location=f"Phòng 10{random.randint(1,9)}, Lầu {random.randint(1,5)}",
                    qualification_name="Tiến sĩ Y khoa Phẫu Thuật",
                    institute_name="Bệnh viện Đa khoa Trung Ương",
                    hospital_name="Bệnh viện Đa Khoa Trung Ương",
                    department=doctor.doctor_profile.specialization,
                    start_time=start_time,
                    end_time=end_time,
                    date=app_date,
                    is_active=True
                )

                # Có 70% cơ hội sẽ có Bệnh nhân Đặt cái lịch này
                if random.random() > 0.3:
                    patient = random.choice(patients)
                    status = random.choice(statuses)
                    
                    # Logic ép lỗi: Lịch tương lai không thể ở trạng thái 'Đã hoàn thành' hoặc 'Đã tới khám'
                    if app_date > now.date():
                        status = random.choice([TakeAppointment.STATUS_PENDING, TakeAppointment.STATUS_CONFIRMED, TakeAppointment.STATUS_CANCELLED])
                    
                    # Tạo Lịch đặt
                    booking = TakeAppointment.objects.create(
                        user=patient,
                        appointment=appointment,
                        full_name=f"{patient.first_name} {patient.last_name}",
                        phone_number=patient.phone_number,
                        message="Thưa bác sĩ, tôi có kết quả xét nghiệm máu cũ mang theo được không?",
                        date=app_date,
                        time=start_time,
                        status=status,
                    )
                    
                    # Nếu lịch đã Khám xong, ép Bệnh nhân cho cái đánh giá 5 sao
                    if status == TakeAppointment.STATUS_COMPLETED:
                        DoctorReview.objects.create(
                            doctor=doctor,
                            patient=patient,
                            booking=booking,
                            rating=random.choice([4, 5]),
                            comment="Bác sĩ rất thân thiện và chuẩn đoán chính xác. Chờ số hơi lâu nhưng rất đáng."
                        )
                        
                    # Có 50% cơ hội Bác sĩ và Bệnh nhân chát chít với nhau trong Hộp thư
                    if status in [TakeAppointment.STATUS_CONFIRMED, TakeAppointment.STATUS_PENDING] and random.random() > 0.5:
                        DirectMessage.objects.create(
                            booking=booking,
                            sender=patient,
                            content="Bác sĩ ơi, tôi đến trễ 10 phút nhé do kẹt xe.",
                            is_read=True
                        )
                        DirectMessage.objects.create(
                            booking=booking,
                            sender=doctor,
                            content="Hoàn toàn được, bạn tới vội cứ vào phòng siêu âm luôn nhé.",
                            is_read=False # Cố tình để chửa đọc cho notification nó sáng lên
                        )

        self.stdout.write(self.style.SUCCESS("✅ HỆ THỐNG ĐÃ TRỘN DỮ LIỆU THÀNH CÔNG! TẠO 5 BÁC SĨ, 10 BỆNH NHÂN VÀ HÀNG TRĂM CUỘC HẸN."))
        self.stdout.write(self.style.WARNING("👉 Lời khuyên: Đăng nhập bằng tài khoản (doctor1@gmail.com / Pass: 1) để xem ngay Dashboard cực chiến!"))
