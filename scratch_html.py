import re

files = [
    'appoinment/templates/appointment/patient_my_appointments.html',
    'home/templates/diabetes.html',
    'home/templates/breast.html',
    'home/templates/kidney.html',
    'home/templates/heart.html',
    'home/templates/pneumonia.html',
]

translations = {
    'patient_my_appointments.html': [
        'Lịch hẹn của tôi',
        'Quản lý lịch khám của bạn dễ dàng hơn',
        'Chưa có lịch hẹn nào',
        'Khi đặt lịch thành công, các lịch khám sắp tới sẽ xuất hiện ở đây để bạn theo dõi và điều chỉnh.',
        'Lịch sử bệnh án',
        'Ngày khám',
        'Giờ khám',
        'Trạng thái',
        'Ghi chú',
        'Chưa có ghi chú',
        'Đổi lịch',
        'Hủy lịch',
        'Nhắn tin',
        'Xem bệnh án',
        'Đánh giá Bác sĩ',
        'Lịch này hiện không còn thao tác khả dụng.',
        'Xem lịch sử thay đổi',
    ],
    'diabetes.html': [
        'Sàng lọc Tiểu đường',
        'Cung cấp các chỉ số sức khỏe cơ bản để đánh giá nguy cơ tiểu đường của bạn.',
        'Nhập chỉ số sức khỏe của bạn',
        'Sàng lọc ngay',
        'Kết quả sàng lọc',
        'Nguy cơ tiểu đường:',
        'Dương tính',
        'Âm tính',
        'Lời khuyên sức khỏe',
    ],
    'breast.html': [
        'Sàng lọc Ung thư Vú',
        'Cung cấp các chỉ số từ kết quả sinh thiết (FNA) để dự đoán khối u lành tính hay ác tính.',
        'Nhập chỉ số tế bào',
        'Sàng lọc ngay',
        'Kết quả đánh giá khối u',
        'Ác tính',
        'Lành tính',
        'Lời khuyên sức khỏe',
    ],
    'kidney.html': [
        'Sàng lọc Bệnh Thận',
        'Cung cấp thông tin xét nghiệm máu và nước tiểu để đánh giá nguy cơ bệnh thận mãn tính.',
        'Tình trạng thận:',
        'Mắc bệnh Thận',
        'Không mắc bệnh Thận',
    ],
    'heart.html': [
        'Sàng lọc Bệnh Tim mạch',
        'Kiểm tra sức khỏe tim mạch dựa trên các yếu tố nguy cơ và chỉ số lâm sàng.',
        'Tình trạng tim mạch:',
        'Mắc bệnh Tim',
        'Không mắc bệnh Tim',
    ],
    'pneumonia.html': [
        'Sàng lọc Viêm phổi',
        'Tải lên ảnh X-quang phổi để hệ thống sử dụng AI phân tích nguy cơ Viêm phổi.',
        'Tải lên ảnh X-quang ngực',
        'Sàng lọc ngay',
        'Kết quả phân tích X-quang',
        'Viêm phổi',
        'Bình thường',
        'Bạn có viêm viêm phổi hoặc vấn đề về phổi',
        'Phổi của bạn bình thường', 
    ]
}

def apply_translations(text, trans_list):
    for t in trans_list:
        text = text.replace(f'>{t}<', f'>{{% trans \"{t}\" %}}<')
        # Handle cases with newlines or spaces around
        text = re.sub(rf'>\s*{re.escape(t)}\s*<', f'>{{% trans \"{t}\" %}}<', text)
    return text

for filepath in files:
    filename = filepath.split('/')[-1]
    trans_list = translations.get(filename, [])
    if not trans_list:
        continue
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = apply_translations(content, trans_list)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Processed {filepath}')
    except FileNotFoundError:
        print(f'File not found: {filepath}')

print('Done!')
