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

translations = {'Anh tai len vuot qua gioi han dung luong cho phep.': 'Uploaded image exceeds '
                                                       'the allowed file size '
                                                       'limit.',
 'BMI': 'BMI',
 'BMI cho thay ban dang thua can. Nen duy tri van dong deu dan khoang 30 phut moi ngay.': 'Your '
                                                                                          'BMI '
                                                                                          'indicates '
                                                                                          'overweight. '
                                                                                          'Try '
                                                                                          'to '
                                                                                          'exercise '
                                                                                          'regularly '
                                                                                          'for '
                                                                                          'about '
                                                                                          '30 '
                                                                                          'minutes '
                                                                                          'a '
                                                                                          'day.',
 'Biểu Đồ Sức Khỏe': 'Health Dashboards',
 'Bác sĩ': 'Doctors',
 'Bác sĩ duyệt': 'Approved',
 'Bác sĩ và Trợ Lý Ảo': 'Doctors and Virtual Assistants',
 'Bình thường': 'Normal',
 'Bạn chưa có lịch hẹn nào': 'You have no appointments yet',
 'Bệnh nhân': 'Patient',
 'Bệnh tim mạch': 'Heart Disease',
 'Bệnh tiểu đường': 'Diabetes Disease',
 'Bệnh viện của': 'The Hospital of the',
 'Bệnh Án EMR': 'EMR Records',
 'Chatbot thông minh Google Gemini tư vấn 24/7 theo bệnh án.': 'Smart Gemini '
                                                               'Chatbot '
                                                               'consults 24/7 '
                                                               'alongside '
                                                               'medical '
                                                               'records.',
 'Cholesterol dang cao. Hay han che thuc an nhieu mo va noi tang dong vat.': 'Cholesterol '
                                                                             'is '
                                                                             'high. '
                                                                             'Limit '
                                                                             'fatty '
                                                                             'foods '
                                                                             'and '
                                                                             'animal '
                                                                             'organs.',
 'Chuyên ngành': 'Specialist',
 'Chúng tôi cung cấp các giải pháp công nghệ hiện đại nhất áp dụng trong chăm sóc sức khỏe.': 'We '
                                                                                              'provide '
                                                                                              'the '
                                                                                              'most '
                                                                                              'modern '
                                                                                              'technological '
                                                                                              'solutions '
                                                                                              'in '
                                                                                              'healthcare.',
 'Chưa có bệnh nhân nào.': 'No patients yet.',
 'Chưa có ghi chú': 'No notes applied',
 'Chưa có lịch hẹn nào': 'No appointments yet',
 'Chất lượng y tế': 'Medical excellence',
 'Chẩn Đoán Đa Khoa': 'General Diagnostics',
 'Chẩn đoán Hình Ảnh': 'Imaging Diagnosis',
 'Chỉ số bổ sung': 'Additional Metrics',
 'Chỉ số khối cơ thể (Cân nặng / Chiều cao^2): Thừa cân đóng vai trò trực tiếp gây bệnh.': 'Body '
                                                                                           'Mass '
                                                                                           'Index: '
                                                                                           'Overweight '
                                                                                           'directly '
                                                                                           'affects '
                                                                                           'disease '
                                                                                           'risk.',
 'Chỉ số này ước tính lượng mỡ cơ thể, yếu tố tác động tới kháng Insulin.': 'Estimates '
                                                                            'body '
                                                                            'fat, '
                                                                            'impacting '
                                                                            'insulin '
                                                                            'resistance.',
 'Chỉ số tiền sử gia đình': 'Diabetes Pedigree',
 'Chỉnh sửa hồ sơ': 'Edit Profile',
 'Chọn một bệnh nhân để bắt đầu trò chuyện': 'Select a patient to start '
                                             'chatting',
 'Chống trùng lịch, tự động nhắc hẹn bệnh nhân qua Email.': 'Prevent overlap, '
                                                            'auto-remind '
                                                            'patients via '
                                                            'Email.',
 'Chờ xác nhận': 'Pending',
 'Co dau hieu ro ri protein qua nuoc tieu, nen tham khao bac si de duoc danh gia them.': 'Signs '
                                                                                         'of '
                                                                                         'protein '
                                                                                         'leakage '
                                                                                         'in '
                                                                                         'urine, '
                                                                                         'consult '
                                                                                         'a '
                                                                                         'doctor '
                                                                                         'for '
                                                                                         'further '
                                                                                         'evaluation.',
 'Cung cấp các chỉ số sức khỏe cơ bản để đánh giá nguy cơ tiểu đường của bạn.': 'Provide '
                                                                                'basic '
                                                                                'health '
                                                                                'metrics '
                                                                                'to '
                                                                                'assess '
                                                                                'your '
                                                                                'diabetes '
                                                                                'risk.',
 'Cung cấp các chỉ số từ kết quả sinh thiết (FNA) để dự đoán khối u lành tính hay ác tính.': 'Provide '
                                                                                             'cell '
                                                                                             'indices '
                                                                                             'from '
                                                                                             'biopsy '
                                                                                             'results '
                                                                                             '(FNA) '
                                                                                             'to '
                                                                                             'predict '
                                                                                             'benign '
                                                                                             'or '
                                                                                             'malignant '
                                                                                             'tumors.',
 'Cung cấp thông tin xét nghiệm máu và nước tiểu để đánh giá nguy cơ bệnh thận mãn tính.': 'Provide '
                                                                                           'blood '
                                                                                           'and '
                                                                                           'urine '
                                                                                           'test '
                                                                                           'information '
                                                                                           'to '
                                                                                           'assess '
                                                                                           'the '
                                                                                           'risk '
                                                                                           'of '
                                                                                           'chronic '
                                                                                           'kidney '
                                                                                           'disease.',
 'Cài đặt': 'Settings',
 'Công nghệ Đột phá': 'Breakthrough Technology',
 'Cấp độ Insulin trong huyết thanh: Giúp máy học tính toán vòng chuyển hóa đường.': 'Serum '
                                                                                    'insulin '
                                                                                    'level: '
                                                                                    'Helps '
                                                                                    'ML '
                                                                                    'map '
                                                                                    'sugar '
                                                                                    'metabolism.',
 'Danh sách Lịch khám': 'Appointment List',
 'Dinh dang anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.': 'Invalid '
                                                                  'image '
                                                                  'format. '
                                                                  'Only JPG, '
                                                                  'PNG, or '
                                                                  'WEBP are '
                                                                  'accepted.',
 'Du lieu khong hop le.': 'Invalid data.',
 'Duong huyet cua ban kha cao. Hay han che do ngot va tinh bot hap thu nhanh.': 'Your '
                                                                                'blood '
                                                                                'sugar '
                                                                                'is '
                                                                                'quite '
                                                                                'high. '
                                                                                'Limit '
                                                                                'sweets '
                                                                                'and '
                                                                                'fast-absorbing '
                                                                                'carbs.',
 'Duong huyet luc doi dang canh bao nguy co tim mach cao hon binh thuong.': 'Fasting '
                                                                            'blood '
                                                                            'sugar '
                                                                            'warns '
                                                                            'of '
                                                                            'higher-than-normal '
                                                                            'cardiovascular '
                                                                            'risk.',
 'Duy tri uong du nuoc va tranh lam dung thuoc giam dau hoac thuoc khong ro nguon goc.': 'Drink '
                                                                                         'plenty '
                                                                                         'of '
                                                                                         'water '
                                                                                         'and '
                                                                                         'avoid '
                                                                                         'overusing '
                                                                                         'painkillers '
                                                                                         'or '
                                                                                         'unknown '
                                                                                         'medications.',
 'Duy trì chế độ ăn lành mạnh, ngủ đủ và tập luyện đều để giảm nguy cơ sau này.': 'Maintain '
                                                                                  'a '
                                                                                  'healthy '
                                                                                  'diet, '
                                                                                  'get '
                                                                                  'enough '
                                                                                  'sleep, '
                                                                                  'and '
                                                                                  'exercise '
                                                                                  'regularly '
                                                                                  'to '
                                                                                  'reduce '
                                                                                  'future '
                                                                                  'risks.',
 'Dương tính': 'Positive',
 'Dịch vụ y tế mà bạn': 'Medical services that you',
 'Dịch vụ ưu việt': 'Our Best Services',
 'Dự báo chẩn đoán bệnh lý đa khoa bằng các mô hình Học Máy chuẩn xác và bảo mật. Trợ lý Ảo AI tư vấn cá nhân hóa.': 'Predictive '
                                                                                                                     'diagnosis '
                                                                                                                     'using '
                                                                                                                     'accurate '
                                                                                                                     'ML '
                                                                                                                     'models. '
                                                                                                                     'Personalized '
                                                                                                                     'Virtual '
                                                                                                                     'AI '
                                                                                                                     'assistant.',
 'English': 'English',
 'File tai len khong phai la anh hop le.': 'Uploaded file is not a valid '
                                           'image.',
 'Ghi chú': 'Notes',
 'Giảm đồ uống có đường, kiểm soát khẩu phần ăn và duy trì vận động phù hợp.': 'Reduce '
                                                                               'sugary '
                                                                               'drinks, '
                                                                               'control '
                                                                               'portions, '
                                                                               'and '
                                                                               'maintain '
                                                                               'appropriate '
                                                                               'exercise.',
 'Giới tính': 'Gender',
 'Giờ khám': 'Time',
 'Glucose': 'Glucose',
 'Gợi ý sức khỏe dành riêng cho bạn': 'Personalized health suggestions',
 'He thong du doan tam thoi gap su co. Vui long thu lai sau.': 'The prediction '
                                                               'system is '
                                                               'temporarily '
                                                               'down. Please '
                                                               'try again '
                                                               'later.',
 'Hemoglobin thap co the lien quan den thieu mau. Ban nen kiem tra them khi di kham.': 'Low '
                                                                                       'hemoglobin '
                                                                                       'may '
                                                                                       'be '
                                                                                       'linked '
                                                                                       'to '
                                                                                       'anemia. '
                                                                                       'Check '
                                                                                       'it '
                                                                                       'further '
                                                                                       'when '
                                                                                       'visiting '
                                                                                       'a '
                                                                                       'doctor.',
 'Hoàn thành': 'Completed',
 'Huyet ap dang o muc can luu y. Hay giam an man va theo doi huyet ap thuong xuyen.': 'Your '
                                                                                      'blood '
                                                                                      'pressure '
                                                                                      'requires '
                                                                                      'attention. '
                                                                                      'Reduce '
                                                                                      'salt '
                                                                                      'intake '
                                                                                      'and '
                                                                                      'monitor '
                                                                                      'it '
                                                                                      'frequently.',
 'Huyet ap nghi dang o muc cao. Ban nen giam an man va theo doi huyet ap tai nha.': 'Resting '
                                                                                    'blood '
                                                                                    'pressure '
                                                                                    'is '
                                                                                    'high. '
                                                                                    'Cut '
                                                                                    'down '
                                                                                    'on '
                                                                                    'salt '
                                                                                    'and '
                                                                                    'monitor '
                                                                                    'your '
                                                                                    'blood '
                                                                                    'pressure '
                                                                                    'at '
                                                                                    'home.',
 'Huyết áp': 'Blood Pressure',
 'Huyết áp tâm trương: Cao huyết áp thường đi chung với bệnh tiểu đường type 2.': 'Diastolic '
                                                                                  'measure: '
                                                                                  'Typically '
                                                                                  'coexists '
                                                                                  'with '
                                                                                  'type '
                                                                                  '2 '
                                                                                  'diabetes.',
 'Hệ thống chưa ghi nhận dấu hiệu nguy cơ nổi bật từ các chỉ số đã nhập, nhưng bạn vẫn nên theo dõi sức khỏe định kỳ.': 'No '
                                                                                                                        'prominent '
                                                                                                                        'risk '
                                                                                                                        'signs '
                                                                                                                        'detected. '
                                                                                                                        'Maintain '
                                                                                                                        'routine '
                                                                                                                        'check-ups.',
 'Hệ thống không chỉ có các Y bác sĩ chuyên môn cao mà còn được trợ lực bởi sức mạnh của Generative AI (LLM).': 'Our '
                                                                                                                'system '
                                                                                                                'features '
                                                                                                                'both '
                                                                                                                'top '
                                                                                                                'specialists '
                                                                                                                'and '
                                                                                                                'the '
                                                                                                                'power '
                                                                                                                'of '
                                                                                                                'Generative '
                                                                                                                'AI '
                                                                                                                '(LLM).',
 'Hệ thống phát hiện nguy cơ tiểu đường ở mức cần lưu ý. Bạn nên thực hiện xét nghiệm và thăm khám sớm để xác nhận.': 'High '
                                                                                                                      'risk '
                                                                                                                      'detected. '
                                                                                                                      'Get '
                                                                                                                      'tested '
                                                                                                                      'and '
                                                                                                                      'consult '
                                                                                                                      'a '
                                                                                                                      'doctor '
                                                                                                                      'soon.',
 'Hồ sơ bệnh án': 'Medical Records',
 'Hộp thư bệnh nhân': 'Patient Inbox',
 'Hủy lịch': 'Cancel Appointment',
 'Hủy lịch hẹn': 'Cancelled',
 'Insulin': 'Insulin',
 'Khi đặt lịch thành công, các lịch khám sắp tới sẽ xuất hiện ở đây để bạn theo dõi và điều chỉnh.': 'Upcoming '
                                                                                                     'appointments '
                                                                                                     'will '
                                                                                                     'appear '
                                                                                                     'here '
                                                                                                     'after '
                                                                                                     'a '
                                                                                                     'successful '
                                                                                                     'booking '
                                                                                                     'for '
                                                                                                     'you '
                                                                                                     'to '
                                                                                                     'track '
                                                                                                     'and '
                                                                                                     'adjust.',
 'Khoa Nội tim mạch': 'Cardiology',
 'Khung giờ': 'Available from',
 'Khuyến cáo chung nên làm gì tiếp theo?': 'General recommendations on what to '
                                           'do next?',
 'Khám:': 'Appt:',
 'Không mắc bệnh Thận': 'No Kidney Disease',
 'Không mắc bệnh Tim': 'No Heart Disease',
 'Không nên dùng kết quả này như kết luận cuối cùng về tình trạng bệnh.': 'Do '
                                                                          'not '
                                                                          'treat '
                                                                          'this '
                                                                          'result '
                                                                          'as '
                                                                          'a '
                                                                          'definitive '
                                                                          'diagnosis '
                                                                          'of '
                                                                          'your '
                                                                          'condition.',
 'Không tìm thấy lịch khám nào khớp với bộ lọc của bạn.': 'No appointments '
                                                          'matching your '
                                                          'filters were found.',
 'Kiểm tra sức khỏe tim mạch dựa trên các yếu tố nguy cơ và chỉ số lâm sàng.': 'Check '
                                                                               'cardiovascular '
                                                                               'health '
                                                                               'based '
                                                                               'on '
                                                                               'risk '
                                                                               'factors '
                                                                               'and '
                                                                               'clinical '
                                                                               'indices.',
 'Kết quả phân tích X-quang': 'X-ray Analysis Results',
 'Kết quả sàng lọc': 'Screening Results',
 'Kết quả đánh giá khối u': 'Tumor Assessment Results',
 'Liên kết nhanh': 'Quick Links',
 'Loi nhap lieu: ': 'Input Error: ',
 'Lành tính': 'Benign (Non-cancerous)',
 'Lý do:': 'Reason:',
 'Lưu ý minh bạch:': 'Disclaimer:',
 'Lịch Khám Online': 'Online Check-ups',
 'Lịch hẹn': 'Appointments',
 'Lịch hẹn của tôi': 'My Appointments',
 'Lịch này hiện không còn thao tác khả dụng.': 'No available actions for this '
                                               'appointment.',
 'Lịch sử bệnh án': 'Medical History',
 'Lịch sử sức khỏe': 'Health History',
 'Lọc': 'Filter',
 'Lời khuyên sức khỏe': 'Health Advice',
 'Mo hinh du doan hien khong kha dung. Vui long thu lai sau.': 'The prediction '
                                                               'model is '
                                                               'currently '
                                                               'unavailable. '
                                                               'Please try '
                                                               'again later.',
 'Mô hình Dữ liệu Khoa học Máy tính (Machine Learning) dựa theo tiêu chuẩn bộ PIMA Indians Diabetes Database. Kết quả dự đoán chỉ mang tính học thuật và tham khảo ban đầu, không thay thế cho chẩn đoán y khoa chuyên nghiệp.': 'Model '
                                                                                                                                                                                                                                 'based '
                                                                                                                                                                                                                                 'on '
                                                                                                                                                                                                                                 'PIMA '
                                                                                                                                                                                                                                 'Indians '
                                                                                                                                                                                                                                 'dataset. '
                                                                                                                                                                                                                                 'Results '
                                                                                                                                                                                                                                 'are '
                                                                                                                                                                                                                                 'for '
                                                                                                                                                                                                                                 'academic '
                                                                                                                                                                                                                                 'reference '
                                                                                                                                                                                                                                 'and '
                                                                                                                                                                                                                                 'do '
                                                                                                                                                                                                                                 'not '
                                                                                                                                                                                                                                 'replace '
                                                                                                                                                                                                                                 'professional '
                                                                                                                                                                                                                                 'diagnosis.',
 'Mắc bệnh Thận': 'Kidney Disease Detected',
 'Mắc bệnh Tim': 'Heart Disease Detected',
 'Nam': 'Male',
 'Neu co dau nguc hoac kho tho khi gang suc, ban nen di kham tim mach som.': 'If '
                                                                             'you '
                                                                             'experience '
                                                                             'chest '
                                                                             'pain '
                                                                             'or '
                                                                             'shortness '
                                                                             'of '
                                                                             'breath '
                                                                             'on '
                                                                             'exertion, '
                                                                             'see '
                                                                             'a '
                                                                             'cardiologist '
                                                                             'soon.',
 'Nguy cơ bệnh thận': 'Kidney Disease Risk',
 'Nguy cơ bệnh tim': 'Heart Disease Risk',
 'Nguy cơ cao hơn bình thường': 'Higher than normal risk',
 'Nguy cơ thấp hơn': 'Lower risk',
 'Nguy cơ tiểu đường': 'Diabetes Risk',
 'Nguy cơ tiểu đường:': 'Diabetes Risk:',
 'Nguy cơ ung thư vú': 'Breast Cancer Risk',
 'Nguy cơ viêm phổi': 'Pneumonia Risk',
 'Ngày khám': 'Exam Date',
 'Ngày khám:': 'Date:',
 'Nha khoa': 'Dentistry',
 'Nhãn khoa / Mắt': 'Eye Care',
 'Nhập chỉ số sức khỏe của bạn': 'Enter your health indicators',
 'Nhập chỉ số tế bào': 'Enter cell metrics',
 'Nhập tin nhắn...': 'Type a message...',
 'Nhắn tin': 'Message',
 'Nên sàng lọc lại nếu có tiền sử gia đình, tăng cân nhanh hoặc xuất hiện triệu chứng mới.': 'Re-screen '
                                                                                             'if '
                                                                                             "there's "
                                                                                             'a '
                                                                                             'family '
                                                                                             'history, '
                                                                                             'rapid '
                                                                                             'weight '
                                                                                             'gain, '
                                                                                             'or '
                                                                                             'new '
                                                                                             'symptoms '
                                                                                             'appear.',
 'Nồng độ đường huyết: Đây là yếu tố quan trọng nhất để AI học máy nhận biết rối loạn chuyển hóa.': 'Blood '
                                                                                                    'sugar '
                                                                                                    'level: '
                                                                                                    'Central '
                                                                                                    'to '
                                                                                                    "ML's "
                                                                                                    'metabolic '
                                                                                                    'detection.',
 'Nội thần kinh': 'Neurology',
 'Nữ': 'Female',
 'Phát hiện viêm phổi X-Quang chuẩn xác bằng công nghệ CNN.': 'Accurate X-Ray '
                                                              'pneumonia '
                                                              'detection via '
                                                              'CNN technology.',
 'Phả hệ bệnh tiểu đường: Yếu tố di truyền chiếm trọng số rất lớn trong cây quyết định của AI.': 'Genetic '
                                                                                                 'factor '
                                                                                                 'carries '
                                                                                                 'heavy '
                                                                                                 'weight '
                                                                                                 'in '
                                                                                                 "AI's "
                                                                                                 'logic '
                                                                                                 'tree.',
 'Quản lý hồ sơ điện tử, đơn thuốc, lịch trình theo dõi an toàn.': 'Manage '
                                                                   'e-records, '
                                                                   'prescriptions, '
                                                                   'and '
                                                                   'follow-ups '
                                                                   'securely.',
 'Quản lý lịch khám của bạn dễ dàng hơn': 'Manage your medical appointments '
                                          'easily',
 'Sàng Lọc Nguy Cơ Tiểu Đường': 'Diabetes Risk Screening',
 'Sàng lọc Bệnh Thận': 'Kidney Disease Screening',
 'Sàng lọc Bệnh Tim mạch': 'Heart Disease Screening',
 'Sàng lọc Tiểu đường': 'Diabetes Screening',
 'Sàng lọc Ung thư Vú': 'Breast Cancer Screening',
 'Sàng lọc Viêm phổi': 'Pneumonia Screening',
 'Sàng lọc ngay': 'Screen Now',
 'Sàng lọc nguy cơ': 'Risk Screening',
 'Sàng lọc nguy cơ tiểu đường': 'Diabetes Risk Screening',
 'Số lần mang thai': 'Pregnancies',
 'Tai Mũi Họng': 'ENT Specialists',
 'Tang huyet ap la yeu to nguy co lon voi than. Hay theo doi huyet ap deu dan.': 'High '
                                                                                 'blood '
                                                                                 'pressure '
                                                                                 'is '
                                                                                 'a '
                                                                                 'major '
                                                                                 'risk '
                                                                                 'factor '
                                                                                 'for '
                                                                                 'kidneys. '
                                                                                 'Monitor '
                                                                                 'your '
                                                                                 'blood '
                                                                                 'pressure.',
 'Ten file anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.': 'Invalid '
                                                                 'image file '
                                                                 'name. Only '
                                                                 'JPG, PNG, or '
                                                                 'WEBP are '
                                                                 'accepted.',
 'Thay đổi thời gian': 'Time changed',
 'Theo dõi các dấu hiệu như khát nhiều, tiểu nhiều, mệt mỏi, sụt cân hoặc nhìn mờ.': 'Monitor '
                                                                                     'symptoms '
                                                                                     'like '
                                                                                     'excessive '
                                                                                     'thirst, '
                                                                                     'frequent '
                                                                                     'urination, '
                                                                                     'fatigue, '
                                                                                     'weight '
                                                                                     'loss, '
                                                                                     'or '
                                                                                     'blurred '
                                                                                     'vision.',
 'Theo dõi tiến trình sinh tồn qua Dashboard thời gian thực.': 'Monitor vitals '
                                                               'via real-time '
                                                               'dashboards.',
 'Thông tin chuyển hóa': 'Metabolic Information',
 'Thể hiện thông tin qua hình ảnh': 'Imaging Information',
 'Thực hiện sàng lọc': 'Run Screening',
 'Tiep tuc duy tri loi song lanh manh va kham suc khoe dinh ky.': 'Continue '
                                                                  'maintaining '
                                                                  'a healthy '
                                                                  'lifestyle '
                                                                  'and regular '
                                                                  'health '
                                                                  'check-ups.',
 'Tiếng Việt': 'Vietnamese',
 'Trang chủ': 'Home',
 'Trang sau': 'Next',
 'Trang trước': 'Previous',
 'Triển khai Machine Learning cho Chẩn đoán Ung Thư Vú, Bệnh Tim, Tiểu Đường và mô hình Học Sâu (Deep Learning) cho Viêm phổi.': 'Deploy '
                                                                                                                                 'ML '
                                                                                                                                 'for '
                                                                                                                                 'Breast '
                                                                                                                                 'Cancer, '
                                                                                                                                 'Heart '
                                                                                                                                 'Disease, '
                                                                                                                                 'Diabetes '
                                                                                                                                 'and '
                                                                                                                                 'Deep '
                                                                                                                                 'Learning '
                                                                                                                                 'for '
                                                                                                                                 'Pneumonia.',
 'Trung Tâm Y Tế ĐH Công Nghiệp Hà Nội': 'Haui Medical Center',
 'Trạng thái': 'Status',
 'Trợ lý Y tế AI': 'AI Health Assistant',
 'Tuổi': 'Age',
 'Tâm lý / Chiêm tinh học': 'Psychology / Astrology',
 'Tên Bác sĩ / Cơ sở...': 'Doctor / Hospital Name...',
 'Tìm hiểu thêm': 'Read More',
 'Tình trạng thận:': 'Kidney Condition:',
 'Tình trạng tim mạch:': 'Cardiovascular Condition:',
 'Tại sao cần số này? Tình trạng thai kỳ trước đây có liên quan đến tiểu đường thai kỳ.': 'Why? '
                                                                                          'Past '
                                                                                          'pregnancies '
                                                                                          'correlate '
                                                                                          'with '
                                                                                          'gestational '
                                                                                          'diabetes.',
 'Tạo lịch hẹn': 'Created',
 'Tạo lịch khám': 'Create Appointment',
 'Tạo mới': 'Created',
 'Tải lên ảnh X-quang ngực': 'Upload Chest X-ray',
 'Tải lên ảnh X-quang phổi để hệ thống sử dụng AI phân tích nguy cơ Viêm phổi.': 'Upload '
                                                                                 'a '
                                                                                 'chest '
                                                                                 'X-ray '
                                                                                 'image '
                                                                                 'for '
                                                                                 'the '
                                                                                 'system '
                                                                                 'to '
                                                                                 'analyze '
                                                                                 'pneumonia '
                                                                                 'risk '
                                                                                 'using '
                                                                                 'AI.',
 'Tất cả chuyên khoa': 'All Departments',
 'Từ:': 'From:',
 'Ung thư vú': 'Breast Cancer',
 'Ure hoac creatinine dang vuot nguong tham khao. Ban nen kiem tra chuc nang than som.': 'Urea '
                                                                                         'or '
                                                                                         'creatinine '
                                                                                         'levels '
                                                                                         'exceed '
                                                                                         'reference '
                                                                                         'range. '
                                                                                         'Check '
                                                                                         'your '
                                                                                         'kidney '
                                                                                         'function '
                                                                                         'soon.',
 'Viêm phổi': 'Pneumonia',
 'Vui long chon anh X-quang truoc khi sang loc.': 'Please select an X-ray '
                                                  'image before screening.',
 'Vui lòng thử thay đổi chuyên khoa, khoảng thời gian, hoặc kiểm tra lại từ khóa.': 'Please '
                                                                                    'try '
                                                                                    'changing '
                                                                                    'the '
                                                                                    'department, '
                                                                                    'time '
                                                                                    'interval, '
                                                                                    'or '
                                                                                    'check '
                                                                                    'your '
                                                                                    'keyword '
                                                                                    'again.',
 'Ví dụ: 0.5': 'e.g., 0.5',
 'Ví dụ: 120': 'e.g., 120',
 'Ví dụ: 2': 'e.g., 2',
 'Ví dụ: 20': 'e.g., 20',
 'Ví dụ: 24.5': 'e.g., 24.5',
 'Ví dụ: 35': 'e.g., 35',
 'Ví dụ: 80': 'e.g., 80',
 'Ví dụ: 85': 'e.g., 85',
 'Vật lý trị liệu': 'Physical Therapy',
 'Xem bệnh án': 'View Medical Record',
 'Xem lại tất cả bác sĩ': 'View all doctors',
 'Xem lịch sử thay đổi': 'View change history',
 'Xây dựng Bệnh Án Điện Tử EMR và Hệ thống cảnh báo tự động SMS/Email, tối ưu quy trình làm việc của Bác Sĩ.': 'Develop '
                                                                                                               'EMR '
                                                                                                               'and '
                                                                                                               'automatic '
                                                                                                               'SMS/Email '
                                                                                                               'alerts '
                                                                                                               'to '
                                                                                                               'optimize '
                                                                                                               "doctors' "
                                                                                                               'workflows.',
 'Xét nghiệm huyết học': 'Blood Screening',
 'có thể tin cậy': 'can trust',
 'lúc': 'at',
 'mỗi ngày': 'every day',
 'tương lai': 'future, today',
 'tại': 'at',
 'Ác tính': 'Malignant (Cancerous)',
 'Âm tính': 'Negative',
 'Đi cấp cứu nếu có dấu hiệu kiệt sức, lú lẫn, khó thở hoặc mất nước nặng.': 'Seek '
                                                                             'emergency '
                                                                             'care '
                                                                             'if '
                                                                             'showing '
                                                                             'signs '
                                                                             'of '
                                                                             'severe '
                                                                             'exhaustion, '
                                                                             'confusion, '
                                                                             'shortness '
                                                                             'of '
                                                                             'breath, '
                                                                             'or '
                                                                             'dehydration.',
 'Đánh giá': 'Rating',
 'Đánh giá Bác sĩ': 'Rate Doctor',
 'Đã hủy': 'Cancelled',
 'Đã khóa chat': 'Chat locked',
 'Đã xác nhận': 'Confirmed',
 'Đăng ký': 'Register',
 'Đăng ký Bác sĩ': 'Doctor Registration',
 'Đăng ký Bệnh nhân': 'Patient Registration',
 'Đăng nhập': 'Login',
 'Đăng xuất': 'Logout',
 'Đặt lịch khám': 'Take Appointment',
 'Đặt lịch khám sớm để làm xét nghiệm đường huyết và được bác sĩ đánh giá chính xác.': 'Schedule '
                                                                                       'a '
                                                                                       'checkup '
                                                                                       'early '
                                                                                       'for '
                                                                                       'blood '
                                                                                       'tests '
                                                                                       'and '
                                                                                       'accurate '
                                                                                       'medical '
                                                                                       'assessment.',
 'Đến:': 'To:',
 'Địa chỉ': 'Address',
 'Địa chỉ:': 'Location:',
 'Đổi lịch': 'Reschedule',
 'Độ dày nếp gấp da': 'Skin Thickness',
 'Đội ngũ Bác sĩ': 'Our Doctors',
 'đến': 'to',
 'Ứng dụng Random Forest & KNN phân lớp rủi ro bệnh lý tức thì.': 'Apply '
                                                                  'Random '
                                                                  'Forest & '
                                                                  'KNN for '
                                                                  'instant '
                                                                  'risk '
                                                                  'classification.'}

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
