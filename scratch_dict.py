import ast
import pprint

with open('build_i18n.py', 'r', encoding='utf-8') as f:
    text = f.read()

start_idx = text.find('translations = {')
end_idx = text.find('}', start_idx) + 1

dict_str = text[start_idx+15:end_idx]
translations = ast.literal_eval(dict_str)

new_keys = {
    'Mo hinh du doan hien khong kha dung. Vui long thu lai sau.': 'The prediction model is currently unavailable. Please try again later.',
    'He thong du doan tam thoi gap su co. Vui long thu lai sau.': 'The prediction system is temporarily down. Please try again later.',
    'Vui long chon anh X-quang truoc khi sang loc.': 'Please select an X-ray image before screening.',
    'Anh tai len vuot qua gioi han dung luong cho phep.': 'Uploaded image exceeds the allowed file size limit.',
    'Dinh dang anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.': 'Invalid image format. Only JPG, PNG, or WEBP are accepted.',
    'Ten file anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.': 'Invalid image file name. Only JPG, PNG, or WEBP are accepted.',
    'File tai len khong phai la anh hop le.': 'Uploaded file is not a valid image.',
    'Loi nhap lieu: ': 'Input Error: ',
    'Du lieu khong hop le.': 'Invalid data.',
    'Duong huyet cua ban kha cao. Hay han che do ngot va tinh bot hap thu nhanh.': 'Your blood sugar is quite high. Limit sweets and fast-absorbing carbs.',
    'BMI cho thay ban dang thua can. Nen duy tri van dong deu dan khoang 30 phut moi ngay.': 'Your BMI indicates overweight. Try to exercise regularly for about 30 minutes a day.',
    'Huyet ap dang o muc can luu y. Hay giam an man va theo doi huyet ap thuong xuyen.': 'Your blood pressure requires attention. Reduce salt intake and monitor it frequently.',
    'Tiep tuc duy tri loi song lanh manh va kham suc khoe dinh ky.': 'Continue maintaining a healthy lifestyle and regular health check-ups.',
    'Huyet ap nghi dang o muc cao. Ban nen giam an man va theo doi huyet ap tai nha.': 'Resting blood pressure is high. Cut down on salt and monitor your blood pressure at home.',
    'Cholesterol dang cao. Hay han che thuc an nhieu mo va noi tang dong vat.': 'Cholesterol is high. Limit fatty foods and animal organs.',
    'Duong huyet luc doi dang canh bao nguy co tim mach cao hon binh thuong.': 'Fasting blood sugar warns of higher-than-normal cardiovascular risk.',
    'Neu co dau nguc hoac kho tho khi gang suc, ban nen di kham tim mach som.': 'If you experience chest pain or shortness of breath on exertion, see a cardiologist soon.',
    'Ure hoac creatinine dang vuot nguong tham khao. Ban nen kiem tra chuc nang than som.': 'Urea or creatinine levels exceed reference range. Check your kidney function soon.',
    'Tang huyet ap la yeu to nguy co lon voi than. Hay theo doi huyet ap deu dan.': 'High blood pressure is a major risk factor for kidneys. Monitor your blood pressure.',
    'Co dau hieu ro ri protein qua nuoc tieu, nen tham khao bac si de duoc danh gia them.': 'Signs of protein leakage in urine, consult a doctor for further evaluation.',
    'Hemoglobin thap co the lien quan den thieu mau. Ban nen kiem tra them khi di kham.': 'Low hemoglobin may be linked to anemia. Check it further when visiting a doctor.',
    'Duy tri uong du nuoc va tranh lam dung thuoc giam dau hoac thuoc khong ro nguon goc.': 'Drink plenty of water and avoid overusing painkillers or unknown medications.',
    'Lịch hẹn của tôi': 'My Appointments',
    'Quản lý lịch khám của bạn dễ dàng hơn': 'Manage your medical appointments easily',
    'Chưa có lịch hẹn nào': 'No appointments yet',
    'Khi đặt lịch thành công, các lịch khám sắp tới sẽ xuất hiện ở đây để bạn theo dõi và điều chỉnh.': 'Upcoming appointments will appear here after a successful booking for you to track and adjust.',
    'Lịch sử bệnh án': 'Medical History',
    'Ngày khám': 'Exam Date',
    'Giờ khám': 'Time',
    'Trạng thái': 'Status',
    'Ghi chú': 'Notes',
    'Chưa có ghi chú': 'No notes applied',
    'Đổi lịch': 'Reschedule',
    'Hủy lịch': 'Cancel Appointment',
    'Nhắn tin': 'Message',
    'Xem bệnh án': 'View Medical Record',
    'Đánh giá Bác sĩ': 'Rate Doctor',
    'Lịch này hiện không còn thao tác khả dụng.': 'No available actions for this appointment.',
    'Xem lịch sử thay đổi': 'View change history',
    'Sàng lọc Tiểu đường': 'Diabetes Screening',
    'Cung cấp các chỉ số sức khỏe cơ bản để đánh giá nguy cơ tiểu đường của bạn.': 'Provide basic health metrics to assess your diabetes risk.',
    'Nhập chỉ số sức khỏe của bạn': 'Enter your health indicators',
    'Sàng lọc ngay': 'Screen Now',
    'Kết quả sàng lọc': 'Screening Results',
    'Nguy cơ tiểu đường:': 'Diabetes Risk:',
    'Dương tính': 'Positive',
    'Âm tính': 'Negative',
    'Lời khuyên sức khỏe': 'Health Advice',
    'Sàng lọc Ung thư Vú': 'Breast Cancer Screening',
    'Cung cấp các chỉ số từ kết quả sinh thiết (FNA) để dự đoán khối u lành tính hay ác tính.': 'Provide cell indices from biopsy results (FNA) to predict benign or malignant tumors.',
    'Nhập chỉ số tế bào': 'Enter cell metrics',
    'Kết quả đánh giá khối u': 'Tumor Assessment Results',
    'Ác tính': 'Malignant (Cancerous)',
    'Lành tính': 'Benign (Non-cancerous)',
    'Sàng lọc Bệnh Thận': 'Kidney Disease Screening',
    'Cung cấp thông tin xét nghiệm máu và nước tiểu để đánh giá nguy cơ bệnh thận mãn tính.': 'Provide blood and urine test information to assess the risk of chronic kidney disease.',
    'Tình trạng thận:': 'Kidney Condition:',
    'Mắc bệnh Thận': 'Kidney Disease Detected',
    'Không mắc bệnh Thận': 'No Kidney Disease',
    'Sàng lọc Bệnh Tim mạch': 'Heart Disease Screening',
    'Kiểm tra sức khỏe tim mạch dựa trên các yếu tố nguy cơ và chỉ số lâm sàng.': 'Check cardiovascular health based on risk factors and clinical indices.',
    'Tình trạng tim mạch:': 'Cardiovascular Condition:',
    'Mắc bệnh Tim': 'Heart Disease Detected',
    'Không mắc bệnh Tim': 'No Heart Disease',
    'Sàng lọc Viêm phổi': 'Pneumonia Screening',
    'Tải lên ảnh X-quang phổi để hệ thống sử dụng AI phân tích nguy cơ Viêm phổi.': 'Upload a chest X-ray image for the system to analyze pneumonia risk using AI.',
    'Tải lên ảnh X-quang ngực': 'Upload Chest X-ray',
    'Thể hiện thông tin qua hình ảnh': 'Imaging Information',
    'Kết quả phân tích X-quang': 'X-ray Analysis Results',
    'Viêm phổi': 'Pneumonia',
    'Bình thường': 'Normal',
}

translations.update(new_keys)

new_dict_str = 'translations = ' + pprint.pformat(translations)

text = text[:start_idx] + new_dict_str + text[end_idx:]

with open('build_i18n.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated translations map in build_i18n.py')
