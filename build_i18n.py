import os
import subprocess
import sys

def install_polib():
    try:
        import polib
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "polib"])
        import polib
    return polib

polib = install_polib()

os.makedirs('locale/en/LC_MESSAGES', exist_ok=True)
os.makedirs('locale/vi/LC_MESSAGES', exist_ok=True)

po = polib.POFile()
po.metadata = {
    'Project-Id-Version': '1.0',
    'MIME-Version': '1.0',
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Transfer-Encoding': '8bit',
    'Language': 'en',
}

translations = {
    "Tiếng Việt": "Vietnamese",
    "English": "English",
    "Bệnh tim mạch": "Heart Disease",
    "Bệnh tiểu đường": "Diabetes Disease",
    "Ung thư vú": "Breast Cancer",
    "Nha khoa": "Dentistry",
    "Khoa Nội tim mạch": "Cardiology",
    "Tai Mũi Họng": "ENT Specialists",
    "Tâm lý / Chiêm tinh học": "Psychology / Astrology",
    "Nội thần kinh": "Neurology",
    "Xét nghiệm huyết học": "Blood Screening",
    "Nhãn khoa / Mắt": "Eye Care",
    "Vật lý trị liệu": "Physical Therapy",
    "Danh sách Lịch khám": "Appointment List",
    "Trang chủ": "Home",
    "Đội ngũ Bác sĩ": "Our Doctors",
    "Tên Bác sĩ / Cơ sở...": "Doctor / Hospital Name...",
    "Tất cả chuyên khoa": "All Departments",
    "Lọc": "Filter",
    "Không tìm thấy lịch khám nào khớp với bộ lọc của bạn.": "No appointments matching your filters were found.",
    "Vui lòng thử thay đổi chuyên khoa, khoảng thời gian, hoặc kiểm tra lại từ khóa.": "Please try changing the department, time interval, or check your keyword again.",
    "Xem lại tất cả bác sĩ": "View all doctors",
    "Đánh giá": "Rating",
    "Chuyên ngành": "Specialist",
    "Ngày khám:": "Date:",
    "Khung giờ": "Available from",
    "đến": "to",
    "tại": "at",
    "Địa chỉ:": "Location:",
    "Đặt lịch khám": "Take Appointment",
    "Trang trước": "Previous",
    "Trang sau": "Next",
    
    # Phase 1: Common UI
    "Trung Tâm Y Tế ĐH Công Nghiệp Hà Nội": "Haui Medical Center",
    "Sàng lọc nguy cơ": "Risk Screening",
    "Nguy cơ tiểu đường": "Diabetes Risk",
    "Nguy cơ ung thư vú": "Breast Cancer Risk",
    "Nguy cơ bệnh tim": "Heart Disease Risk",
    "Nguy cơ bệnh thận": "Kidney Disease Risk",
    "Nguy cơ viêm phổi": "Pneumonia Risk",
    "Bác sĩ": "Doctors",
    "Cài đặt": "Settings",
    "Lịch hẹn": "Appointments",
    "Tạo lịch khám": "Create Appointment",
    "Đăng xuất": "Logout",
    "Lịch sử sức khỏe": "Health History",
    "Lịch hẹn của tôi": "My Appointments",
    "Hồ sơ bệnh án": "Medical Records",
    "Chỉnh sửa hồ sơ": "Edit Profile",
    "Đăng ký": "Register",
    "Bệnh nhân": "Patient",
    "Đăng nhập": "Login",
    "Đăng ký Bác sĩ": "Doctor Registration",
    "Đăng ký Bệnh nhân": "Patient Registration",
    "Giới tính": "Gender",
    "Nam": "Male",
    "Nữ": "Female",
    "Địa chỉ": "Address",
    "Liên kết nhanh": "Quick Links",
    
    # Phase 2: Index & ML Models
    "Dịch vụ y tế mà bạn": "Medical services that you",
    "có thể tin cậy": "can trust",
    "Dự báo chẩn đoán bệnh lý đa khoa bằng các mô hình Học Máy chuẩn xác và bảo mật. Trợ lý Ảo AI tư vấn cá nhân hóa.": "Predictive diagnosis using accurate ML models. Personalized Virtual AI assistant.",
    "Tìm hiểu thêm": "Read More",
    "Chất lượng y tế": "Medical excellence",
    "mỗi ngày": "every day",
    "Triển khai Machine Learning cho Chẩn đoán Ung Thư Vú, Bệnh Tim, Tiểu Đường và mô hình Học Sâu (Deep Learning) cho Viêm phổi.": "Deploy ML for Breast Cancer, Heart Disease, Diabetes and Deep Learning for Pneumonia.",
    "Bệnh viện của": "The Hospital of the",
    "tương lai": "future, today",
    "Xây dựng Bệnh Án Điện Tử EMR và Hệ thống cảnh báo tự động SMS/Email, tối ưu quy trình làm việc của Bác Sĩ.": "Develop EMR and automatic SMS/Email alerts to optimize doctors' workflows.",
    "Công nghệ Đột phá": "Breakthrough Technology",
    "Bác sĩ và Trợ Lý Ảo": "Doctors and Virtual Assistants",
    "Hệ thống không chỉ có các Y bác sĩ chuyên môn cao mà còn được trợ lực bởi sức mạnh của Generative AI (LLM).": "Our system features both top specialists and the power of Generative AI (LLM).",
    "Dịch vụ ưu việt": "Our Best Services",
    "Chúng tôi cung cấp các giải pháp công nghệ hiện đại nhất áp dụng trong chăm sóc sức khỏe.": "We provide the most modern technological solutions in healthcare.",
    "Chẩn Đoán Đa Khoa": "General Diagnostics",
    "Ứng dụng Random Forest & KNN phân lớp rủi ro bệnh lý tức thì.": "Apply Random Forest & KNN for instant risk classification.",
    "Trợ lý Y tế AI": "AI Health Assistant",
    "Chatbot thông minh Google Gemini tư vấn 24/7 theo bệnh án.": "Smart Gemini Chatbot consults 24/7 alongside medical records.",
    "Bệnh Án EMR": "EMR Records",
    "Quản lý hồ sơ điện tử, đơn thuốc, lịch trình theo dõi an toàn.": "Manage e-records, prescriptions, and follow-ups securely.",
    "Lịch Khám Online": "Online Check-ups",
    "Chống trùng lịch, tự động nhắc hẹn bệnh nhân qua Email.": "Prevent overlap, auto-remind patients via Email.",
    "Chẩn đoán Hình Ảnh": "Imaging Diagnosis",
    "Phát hiện viêm phổi X-Quang chuẩn xác bằng công nghệ CNN.": "Accurate X-Ray pneumonia detection via CNN technology.",
    "Biểu Đồ Sức Khỏe": "Health Dashboards",
    "Theo dõi tiến trình sinh tồn qua Dashboard thời gian thực.": "Monitor vitals via real-time dashboards.",
    "Sàng Lọc Nguy Cơ Tiểu Đường": "Diabetes Risk Screening",
    "Sàng lọc nguy cơ tiểu đường": "Diabetes Risk Screening",
    "Lưu ý minh bạch:": "Disclaimer:",
    "Mô hình Dữ liệu Khoa học Máy tính (Machine Learning) dựa theo tiêu chuẩn bộ PIMA Indians Diabetes Database. Kết quả dự đoán chỉ mang tính học thuật và tham khảo ban đầu, không thay thế cho chẩn đoán y khoa chuyên nghiệp.": "Model based on PIMA Indians dataset. Results are for academic reference and do not replace professional diagnosis.",
    "Kết quả sàng lọc": "Screening Results",
    "Nguy cơ cao hơn bình thường": "Higher than normal risk",
    "Nguy cơ thấp hơn": "Lower risk",
    "Hệ thống phát hiện nguy cơ tiểu đường ở mức cần lưu ý. Bạn nên thực hiện xét nghiệm và thăm khám sớm để xác nhận.": "High risk detected. Get tested and consult a doctor soon.",
    "Hệ thống chưa ghi nhận dấu hiệu nguy cơ nổi bật từ các chỉ số đã nhập, nhưng bạn vẫn nên theo dõi sức khỏe định kỳ.": "No prominent risk signs detected. Maintain routine check-ups.",
    "Thông tin chuyển hóa": "Metabolic Information",
    "Số lần mang thai": "Pregnancies",
    "Tại sao cần số này? Tình trạng thai kỳ trước đây có liên quan đến tiểu đường thai kỳ.": "Why? Past pregnancies correlate with gestational diabetes.",
    "Ví dụ: 2": "e.g., 2",
    "Glucose": "Glucose",
    "Nồng độ đường huyết: Đây là yếu tố quan trọng nhất để AI học máy nhận biết rối loạn chuyển hóa.": "Blood sugar level: Central to ML's metabolic detection.",
    "Ví dụ: 120": "e.g., 120",
    "Huyết áp": "Blood Pressure",
    "Huyết áp tâm trương: Cao huyết áp thường đi chung với bệnh tiểu đường type 2.": "Diastolic measure: Typically coexists with type 2 diabetes.",
    "Ví dụ: 80": "e.g., 80",
    "Chỉ số bổ sung": "Additional Metrics",
    "Độ dày nếp gấp da": "Skin Thickness",
    "Chỉ số này ước tính lượng mỡ cơ thể, yếu tố tác động tới kháng Insulin.": "Estimates body fat, impacting insulin resistance.",
    "Ví dụ: 20": "e.g., 20",
    "Insulin": "Insulin",
    "Cấp độ Insulin trong huyết thanh: Giúp máy học tính toán vòng chuyển hóa đường.": "Serum insulin level: Helps ML map sugar metabolism.",
    "Ví dụ: 85": "e.g., 85",
    "BMI": "BMI",
    "Chỉ số khối cơ thể (Cân nặng / Chiều cao^2): Thừa cân đóng vai trò trực tiếp gây bệnh.": "Body Mass Index: Overweight directly affects disease risk.",
    "Ví dụ: 24.5": "e.g., 24.5",
    "Chỉ số tiền sử gia đình": "Diabetes Pedigree",
    "Phả hệ bệnh tiểu đường: Yếu tố di truyền chiếm trọng số rất lớn trong cây quyết định của AI.": "Genetic factor carries heavy weight in AI's logic tree.",
    "Ví dụ: 0.5": "e.g., 0.5",
    "Ví dụ: 0.5": "e.g., 0.5",
    "Tuổi": "Age",
    "Ví dụ: 35": "e.g., 35",
    "Thực hiện sàng lọc": "Run Screening",
    
    # Phase 3: Inbox
    "Hộp thư bệnh nhân": "Patient Inbox",
    "Khám:": "Appt:",
    "Chưa có bệnh nhân nào.": "No patients yet.",
    "Đã khóa chat": "Chat locked",
    "Nhập tin nhắn...": "Type a message...",
    "Chọn một bệnh nhân để bắt đầu trò chuyện": "Select a patient to start chatting",
}

for msgid, msgstr in translations.items():
    entry = polib.POEntry(
        msgid=msgid,
        msgstr=msgstr,
    )
    po.append(entry)

po.save('locale/en/LC_MESSAGES/django.po')
po.save_as_mofile('locale/en/LC_MESSAGES/django.mo')

# Dummy file for VI (so django doesn't complain)
po_vi = polib.POFile()
po_vi.metadata = po.metadata.copy()
po_vi.metadata['Language'] = 'vi'
for msgid in translations.keys():
    po_vi.append(polib.POEntry(msgid=msgid, msgstr=msgid))
po_vi.save('locale/vi/LC_MESSAGES/django.po')
po_vi.save_as_mofile('locale/vi/LC_MESSAGES/django.mo')

print("Compiled translations successfully.")
