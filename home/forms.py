from django import forms


class FriendlyScreeningForm(forms.Form):
    """Adds plain-language descriptions for the patient-facing forms."""

    field_guidance = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, guidance in self.field_guidance.items():
            self.fields[field_name].help_text = guidance


class DiabetesForm(FriendlyScreeningForm):
    pregnancies = forms.FloatField(required=True, min_value=0, max_value=20)
    glucose = forms.FloatField(required=True, min_value=10, max_value=500)
    bloodpressure = forms.FloatField(required=True, min_value=20, max_value=300)
    skinthickness = forms.FloatField(required=True, min_value=0, max_value=100)
    bmi = forms.FloatField(required=True, min_value=10, max_value=100)
    insulin = forms.FloatField(required=True, min_value=0, max_value=1000)
    pedigree = forms.FloatField(required=True, min_value=0.01, max_value=4.0)
    age = forms.FloatField(required=True, min_value=1, max_value=120)

    field_guidance = {
        'pregnancies': 'Số lần mang thai trước đây. Chỉ số này có ý nghĩa với người đã từng mang thai.',
        'glucose': 'Đường huyết, thường lấy từ kết quả xét nghiệm. Nhập đúng đơn vị ghi trên phiếu xét nghiệm.',
        'bloodpressure': 'Huyết áp tâm trương, là số nhỏ hơn khi đo huyết áp (ví dụ 80 trong 120/80 mmHg).',
        'skinthickness': 'Chỉ số đo nếp gấp da trong bộ dữ liệu tham khảo; chỉ nhập khi bạn có số liệu xét nghiệm/đo chuyên môn.',
        'bmi': 'Chỉ số khối cơ thể = cân nặng (kg) / chiều cao bình phương (m²).',
        'insulin': 'Nồng độ insulin từ xét nghiệm máu. Không cần tự ước lượng nếu bạn chưa từng xét nghiệm.',
        'pedigree': 'Chỉ số tiền sử gia đình trong bộ dữ liệu; chỉ nhập theo báo cáo chuyên môn nếu có.',
        'age': 'Tuổi hiện tại của bạn.',
    }


class BreastCancerForm(FriendlyScreeningForm):
    radius = forms.FloatField(required=True, min_value=5.0, max_value=40.0)
    texture = forms.FloatField(required=True, min_value=5.0, max_value=50.0)
    perimeter = forms.FloatField(required=True, min_value=30.0, max_value=250.0)
    area = forms.FloatField(required=True, min_value=100.0, max_value=3000.0)
    smoothness = forms.FloatField(required=True, min_value=0.01, max_value=0.3)

    field_guidance = {
        'radius': 'Bán kính trung bình của vùng mô, lấy từ báo cáo hình ảnh hoặc xét nghiệm tế bào.',
        'texture': 'Mức độ biến thiên bề mặt mô trên báo cáo chuyên môn, không phải cảm nhận khi tự sờ.',
        'perimeter': 'Chu vi trung bình của vùng mô được đo trên ảnh hoặc tiêu bản.',
        'area': 'Diện tích trung bình của vùng mô được hệ thống hình ảnh ghi nhận.',
        'smoothness': 'Độ đều của bề mặt mô trong báo cáo phân tích. Hãy dùng số trên kết quả chuyên môn.',
    }


class HeartDiseaseForm(FriendlyScreeningForm):
    age = forms.FloatField(required=True, min_value=1, max_value=120)
    sex = forms.FloatField(required=True, min_value=0, max_value=1)
    cp = forms.FloatField(required=True, min_value=0, max_value=3)
    trestbps = forms.FloatField(required=True, min_value=50, max_value=300)
    chol = forms.FloatField(required=True, min_value=50, max_value=600)
    fbs = forms.FloatField(required=True, min_value=0, max_value=1)
    restecg = forms.FloatField(required=True, min_value=0, max_value=2)
    thalach = forms.FloatField(required=True, min_value=50, max_value=250)
    exang = forms.FloatField(required=True, min_value=0, max_value=1)
    oldpeak = forms.FloatField(required=True, min_value=0.0, max_value=10.0)
    slope = forms.FloatField(required=True, min_value=0, max_value=2)
    ca = forms.FloatField(required=True, min_value=0, max_value=4)
    thal = forms.FloatField(required=True, min_value=0, max_value=3)

    field_guidance = {
        'age': 'Tuổi hiện tại.',
        'sex': 'Mã giới tính của bộ dữ liệu: 0 là nữ, 1 là nam.',
        'cp': 'Loại đau ngực theo mã bác sĩ ghi nhận: 0–3. Không nên tự đoán nếu chưa được khám.',
        'trestbps': 'Huyết áp lúc nghỉ, đơn vị mmHg; lấy số lớn hơn trong kết quả đo huyết áp.',
        'chol': 'Cholesterol toàn phần trong máu, đơn vị mg/dL, lấy từ xét nghiệm.',
        'fbs': 'Mã đường huyết đói: 1 khi lớn hơn 120 mg/dL, 0 khi không.',
        'restecg': 'Kết quả điện tâm đồ lúc nghỉ theo mã 0–2 trên báo cáo bác sĩ.',
        'thalach': 'Nhịp tim tối đa đạt được, đơn vị nhịp/phút.',
        'exang': 'Đau thắt ngực khi gắng sức: 1 là có, 0 là không.',
        'oldpeak': 'Mức chênh ST khi gắng sức, lấy từ kết quả điện tâm đồ.',
        'slope': 'Dạng đoạn ST theo mã 0–2 trong báo cáo điện tâm đồ.',
        'ca': 'Số mạch vành lớn được ghi nhận, mã 0–4 từ kết quả chuyên môn.',
        'thal': 'Chỉ số thalassemia/tưới máu theo mã 0–3 trong dữ liệu tim mạch.',
    }


class KidneyDiseaseForm(FriendlyScreeningForm):
    serum_creatinine = forms.FloatField(required=True, min_value=0.1, max_value=20.0)
    blood_urea = forms.FloatField(required=True, min_value=5.0, max_value=400.0)
    albumin = forms.FloatField(required=True, min_value=0, max_value=5)
    hemoglobin = forms.FloatField(required=True, min_value=2.0, max_value=25.0)
    specific_gravity = forms.FloatField(required=True, min_value=1.000, max_value=1.040)
    hypertension = forms.FloatField(required=True, min_value=0, max_value=1)

    field_guidance = {
        'serum_creatinine': 'Creatinine máu phản ánh khả năng lọc của thận; lấy từ xét nghiệm sinh hóa máu.',
        'blood_urea': 'Ure máu, một chỉ số xét nghiệm giúp đánh giá tình trạng chuyển hóa và chức năng thận.',
        'albumin': 'Mức albumin trong nước tiểu theo thang 0–5 của bộ dữ liệu. Dùng kết quả xét nghiệm nếu có.',
        'hemoglobin': 'Hemoglobin trong máu, đơn vị g/dL, thường có trong công thức máu.',
        'specific_gravity': 'Tỷ trọng nước tiểu; cho biết mức cô đặc của nước tiểu, lấy từ xét nghiệm nước tiểu.',
        'hypertension': 'Tiền sử tăng huyết áp: chọn Có nếu đã từng được bác sĩ chẩn đoán hoặc đang điều trị.',
    }


class PneumoniaUploadForm(FriendlyScreeningForm):
    xray = forms.ImageField(required=True)

    field_guidance = {
        'xray': 'Chỉ dùng ảnh X-quang ngực rõ nét. Ảnh chụp màn hình hoặc ảnh không phải X-quang có thể làm kết quả kém tin cậy.',
    }


class SkinCancerUploadForm(FriendlyScreeningForm):
    """Form upload ảnh tổn thương da cho tính năng sàng lọc 7-class."""

    skin_image = forms.ImageField(
        required=True,
        label='Ảnh tổn thương da',
        help_text='Ảnh chụp gần (macro) vùng tổn thương, ánh sáng tốt, không che khuất.',
    )

    field_guidance = {
        'skin_image': 'Chụp cận cảnh vùng da dưới ánh sáng đều, không dùng ảnh bị mờ, che khuất hoặc đã chỉnh màu mạnh.',
    }
