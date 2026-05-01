import base64
import csv
import json
import logging
import os
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

# QUAN TRỌNG: phải set BEFORE import tensorflow.
# Skin cancer model (model.h5 từ repo gốc) train với Keras 2 API,
# nhưng TensorFlow 2.16+ dùng Keras 3 - không tương thích trực tiếp.
# Set flag này để TF dùng tf_keras (Keras 2 legacy) khi cần.
os.environ.setdefault('TF_USE_LEGACY_KERAS', '1')

import joblib
import numpy as np
import tensorflow as tf
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

from notifications.realtime import push_realtime_notification

from .forms import (
    BreastCancerForm,
    DiabetesForm,
    HeartDiseaseForm,
    KidneyDiseaseForm,
    PneumoniaUploadForm,
    SkinCancerUploadForm,
)
from .models import ChatMessage, MedicalHistory


DATA_DIR = Path(settings.BASE_DIR) / 'data'
ALLOWED_XRAY_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
logger = logging.getLogger(__name__)


# ----- Skin Cancer Detection (HAM10000 7-class) -----------------------------
# Map index -> (mã nội bộ, tên VN, tên EN, mức độ nguy hiểm)
# Thứ tự index theo HAM10000 / repo gốc DACS_5_AI_SkinCancer.
SKIN_LESION_CLASSES = [
    {'code': 'akiec', 'vi': 'Tổn thương dày sừng quang hóa', 'en': 'Actinic keratoses',
     'severity': 'precancerous', 'badge': 'warning'},
    {'code': 'bcc',   'vi': 'Ung thư biểu mô tế bào đáy',     'en': 'Basal cell carcinoma',
     'severity': 'malignant', 'badge': 'danger'},
    {'code': 'bkl',   'vi': 'Tổn thương dày sừng lành tính',  'en': 'Benign keratosis-like lesions',
     'severity': 'benign', 'badge': 'success'},
    {'code': 'df',    'vi': 'U xơ da',                         'en': 'Dermatofibroma',
     'severity': 'benign', 'badge': 'success'},
    {'code': 'nv',    'vi': 'Nốt ruồi hắc tố',                 'en': 'Melanocytic nevi',
     'severity': 'benign', 'badge': 'success'},
    {'code': 'mel',   'vi': 'Ung thư hắc tố (Melanoma)',       'en': 'Melanoma',
     'severity': 'malignant_high', 'badge': 'danger'},
    {'code': 'vasc',  'vi': 'Tổn thương mạch máu da',          'en': 'Vascular lesions',
     'severity': 'benign', 'badge': 'info'},
]
# Class nguy hiểm cần cảnh báo cấp cứu / khám gấp
SKIN_DANGEROUS_CODES = {'mel', 'bcc', 'akiec'}


def image_to_base64(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def save_medical_history(request, disease_type, prediction_result, input_data):
    if request.user.is_authenticated:
        MedicalHistory.objects.create(
            user=request.user,
            disease_type=disease_type,
            prediction_result=prediction_result,
            input_data=input_data,
        )


def load_pickle_model(filename):
    model_path = DATA_DIR / filename
    if not model_path.exists():
        logger.warning('Model file missing: %s', model_path)
        return None

    try:
        with open(model_path, 'rb') as file:
            return joblib.load(file)
    except Exception:
        logger.exception('Failed to load pickle model: %s', model_path)
        return None


@lru_cache(maxsize=1)
def get_diabetes_model():
    return load_pickle_model('diabetes_model.pkl')


@lru_cache(maxsize=1)
def get_breast_model():
    return load_pickle_model('breast_model.pkl')


@lru_cache(maxsize=1)
def get_heart_model():
    return load_pickle_model('heart_disease_model.pkl')


@lru_cache(maxsize=1)
def get_pneumonia_model():
    model_path = DATA_DIR / 'pneumonia_classifiers.h5'
    if not model_path.exists():
        logger.warning('Model file missing: %s', model_path)
        return None

    try:
        return tf.keras.models.load_model(model_path, compile=True)
    except Exception:
        logger.exception('Failed to load pneumonia model: %s', model_path)
        return None


@lru_cache(maxsize=1)
def get_skin_cancer_model():
    """Load model phân loại 7-class tổn thương da (HAM10000).

    Tên file mặc định: data/skin_cancer_model.h5. Có thể override qua
    settings.SKIN_CANCER_MODEL_FILE nếu user đặt tên khác (vd: model.h5).

    Fallback: nếu TF Keras 3 không load được file .h5 cũ (train với Keras 2),
    thử lại với tf_keras (legacy Keras 2 API).
    """
    candidates = [
        getattr(settings, 'SKIN_CANCER_MODEL_FILE', None),
        'skin_cancer_model.h5',
        'skin_cancer_classifier.h5',
        'model.h5',  # tên nguyên bản từ repo DACS_5_AI_SkinCancer
    ]
    for filename in candidates:
        if not filename:
            continue
        model_path = DATA_DIR / filename
        if not model_path.exists():
            continue

        # Thử với tf.keras hiện tại (Keras 3 trong TF >= 2.16, Keras 2 trong TF < 2.16)
        try:
            return tf.keras.models.load_model(model_path, compile=False)
        except Exception as primary_err:
            logger.warning(
                'Primary load failed for %s (%s). Trying tf_keras legacy fallback.',
                model_path, primary_err.__class__.__name__,
            )

        # Fallback: tf_keras (Keras 2 standalone) cho file train với Keras cũ
        try:
            import tf_keras
            return tf_keras.models.load_model(model_path, compile=False)
        except ImportError:
            logger.error(
                'Skin cancer model needs Keras 2 to load. '
                'Install with: pip install tf_keras'
            )
            return None
        except Exception:
            logger.exception('tf_keras fallback also failed for %s', model_path)
            return None

    logger.warning('Skin cancer model file not found in %s. Tried: %s', DATA_DIR, candidates)
    return None


def _preprocess_skin_image(image):
    """Tiền xử lý ảnh giống pipeline gốc: resize 100x75, normalize per-image.

    Trả về numpy array shape (1, 75, 100, 3) sẵn sàng cho model.predict().
    """
    rgb = image.convert('RGB').resize((100, 75))
    arr = np.asarray(rgb, dtype=np.float32)
    mean = float(arr.mean())
    std = float(arr.std()) or 1.0  # tránh chia cho 0 với ảnh đơn sắc
    normalized = (arr - mean) / std
    return normalized.reshape(1, 75, 100, 3)


def _build_skin_predictions(probabilities):
    """Convert vector xác suất 7-class thành list dict đã format cho template."""
    items = []
    for idx, cls in enumerate(SKIN_LESION_CLASSES):
        prob = round(float(probabilities[idx]) * 100, 2)
        items.append({
            'code': cls['code'],
            'label_vi': cls['vi'],
            'label_en': cls['en'],
            'severity': cls['severity'],
            'badge': cls['badge'],
            'probability': prob,
        })
    items.sort(key=lambda x: x['probability'], reverse=True)
    return items


def _build_skin_advice(top_class, all_predictions):
    """Sinh khuyến nghị y tế dựa vào class top-1 và phân bố xác suất.

    Lưu ý: KHÔNG được trình bày như chẩn đoán xác định. Đây là sàng lọc sơ bộ.
    """
    advices = []
    if top_class['code'] == 'mel':
        advices.append(_('Ket qua nghi ngo Melanoma - day la dang ung thu da nguy hiem nhat. Hay di kham chuyen khoa Da lieu/Ung buou trong 1-2 ngay toi.'))
    if top_class['code'] == 'bcc':
        advices.append(_('Co dau hieu cua ung thu bieu mo te bao day. Tien luong tot neu phat hien som, ban nen di kham chuyen khoa Da lieu sap toi.'))
    if top_class['code'] == 'akiec':
        advices.append(_('Ton thuong dang sung quang hoa la ton thuong tien ung thu. Can dieu tri som tranh tien trien thanh ung thu te bao gai.'))
    if top_class['code'] == 'nv':
        advices.append(_('Da phan not ruoi la lanh tinh. Theo doi quy tac ABCDE: Asymmetry, Border, Color, Diameter, Evolution. Khi co thay doi - di kham.'))
    if top_class['code'] == 'bkl':
        advices.append(_('Ton thuong day sung lanh tinh, thuong xuat hien o nguoi lon tuoi. Khong nguy hiem nhung neu ngua nhieu hoac chay mau hay di kham.'))
    if top_class['code'] == 'df':
        advices.append(_('U xo da thuong lanh tinh, khong can dieu tri tru khi gay kho chiu hoac mat tham my.'))
    if top_class['code'] == 'vasc':
        advices.append(_('Ton thuong mach mau da phan lanh tinh. Theo doi neu thay doi kich thuoc nhanh.'))

    # Cảnh báo nếu top-2 là dangerous với xác suất > 25%
    second = all_predictions[1] if len(all_predictions) > 1 else None
    if second and second['code'] in SKIN_DANGEROUS_CODES and second['probability'] >= 25:
        advices.append(_('Mo hinh con phan van, xac suat lop nguy hiem khac kha cao. Hay di kham truc tiep de bac si quyet dinh sinh thiet hay khong.'))

    advices.append(_('Day chi la sang loc tham khao bang AI, KHONG thay the chan doan cua bac si Da lieu. Hay luu lai anh va di kham som de duoc soi da (dermoscopy).'))
    return advices


def skin_cancer_detector(request):
    """View sàng lọc ung thư da bằng CNN (HAM10000, 7 lớp)."""
    uploaded_image = None
    predictions = None
    top_class = None
    is_dangerous = None
    error = None
    advices = []

    if request.method == 'POST':
        form = SkinCancerUploadForm(request.POST, request.FILES)
        image_file = request.FILES.get('skin_image')
        # Reuse validator của pneumonia (cùng giới hạn dung lượng & MIME)
        error = validate_uploaded_xray(image_file)

        if form.is_valid() and not error:
            model = get_skin_cancer_model()
            if model is None:
                error = _('Mo hinh sang loc ung thu da chua duoc trien khai. Vui long lien he quan tri vien.')
            else:
                try:
                    original_image = Image.open(image_file)
                    preview_image = original_image.copy()

                    x_test = _preprocess_skin_image(original_image)
                    raw = model.predict(x_test, verbose=0)
                    probabilities = raw[0] if raw.ndim > 1 else raw

                    predictions = _build_skin_predictions(probabilities)
                    top_class = predictions[0]
                    is_dangerous = top_class['code'] in SKIN_DANGEROUS_CODES
                    advices = _build_skin_advice(top_class, predictions)
                    uploaded_image = image_to_base64(preview_image)

                    save_medical_history(
                        request,
                        'Skin Cancer',
                        f"{top_class['code']} ({top_class['probability']}%)",
                        {
                            'top_class': top_class['code'],
                            'top_label': top_class['label_vi'],
                            'top_probability': top_class['probability'],
                            'distribution': {p['code']: p['probability'] for p in predictions},
                        },
                    )

                    # Push notification cảnh báo nếu dangerous & user đã login
                    if is_dangerous and request.user.is_authenticated:
                        try:
                            push_realtime_notification(
                                request.user,
                                title=str(_('Canh bao ket qua sang loc da')),
                                message=str(_('Ket qua sang loc nghi ngo ton thuong nguy hiem. Vui long di kham Da lieu som.')),
                                level='warning',
                                category='skin-cancer',
                                payload={'top_class': top_class['code']},
                            )
                        except Exception:
                            logger.exception('Skin cancer warning notification failed')
                except UnidentifiedImageError:
                    error = _('Khong doc duoc anh. Vui long tai len anh JPG/PNG hop le.')
                except Exception:
                    logger.exception(
                        'Skin cancer detection failed for upload: %s',
                        getattr(image_file, 'name', '<unknown>'),
                    )
                    error = _('He thong phan tich anh tam thoi gap su co. Vui long thu lai sau.')
        elif not error:
            error = _('Vui long tai len mot anh ton thuong da hop le.')

    return render(request, 'skin_cancer.html', {
        'uploaded_image': uploaded_image,
        'predictions': predictions,
        'top_class': top_class,
        'is_dangerous': is_dangerous,
        'error': error,
        'advices': advices,
        'classes': SKIN_LESION_CLASSES,
    })


def run_prediction(model, user_data, prediction_name):
    if model is None:
        return None, _('Mo hinh du doan hien khong kha dung. Vui long thu lai sau.')

    try:
        return model.predict(user_data)[0], ''
    except Exception as e:
        logger.error('Error running model %s: %s', prediction_name, e, exc_info=True)
        return None, _("He thong du doan tam thoi gap su co. Vui long thu lai sau.")


def validate_uploaded_xray(uploaded_file):
    if uploaded_file is None:
        return _('Vui long chon anh X-quang truoc khi sang loc.')

    if uploaded_file.size > getattr(settings, 'MAX_XRAY_UPLOAD_BYTES', 5 * 1024 * 1024):
        return _('Anh tai len vuot qua gioi han dung luong cho phep.')

    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    if content_type and content_type not in getattr(
        settings,
        'ALLOWED_XRAY_CONTENT_TYPES',
        ('image/jpeg', 'image/png', 'image/webp'),
    ):
        return _('Dinh dang anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.')

    suffix = Path(uploaded_file.name or '').suffix.lower()
    if suffix and suffix not in ALLOWED_XRAY_EXTENSIONS:
        return _('Ten file anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.')

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.verify()
        uploaded_file.seek(0)
    except (UnidentifiedImageError, OSError):
        logger.warning('Invalid xray upload received: %s', getattr(uploaded_file, 'name', '<unknown>'))
        return _('File tai len khong phai la anh hop le.')

    return ''


def render_prediction_page(request, template_name, form, user_data, disease_type, positive_label, negative_label, advice_builder, prediction_name):
    value = ''
    error = ''
    advices = []

    if request.method == 'POST':
        if form.is_valid():
            prediction, prediction_error = run_prediction(
                model=form.model_loader(),
                user_data=user_data(form.cleaned_data),
                prediction_name=prediction_name,
            )
            if prediction_error:
                error = prediction_error
            else:
                value = positive_label if int(prediction) == 1 else negative_label
                save_medical_history(request, disease_type, value, form.cleaned_data)
                advices = advice_builder(form.cleaned_data)
        else:
            errors = [f"{field}: {', '.join(e)}" for field, e in form.errors.items()]
            from django.utils.translation import gettext as _
            error = str(_("Loi nhap lieu: ")) + ' | '.join(errors) if errors else str(_('Du lieu khong hop le.'))

    return render(request, template_name, {'context': value, 'error': error, 'advices': advices})


def index(request):
    return render(request, 'index.html')


def diabetes(request):
    form = DiabetesForm(request.POST or None)
    form.model_loader = get_diabetes_model

    def payload(data):
        return np.array([
            data['pregnancies'],
            data['glucose'],
            data['bloodpressure'],
            data['skinthickness'],
            data['bmi'],
            data['insulin'],
            data['pedigree'],
            data['age'],
        ]).reshape(1, 8)

    def advices(data):
        items = []
        if data['glucose'] >= 140:
            items.append(_('Duong huyet cua ban kha cao. Hay han che do ngot va tinh bot hap thu nhanh.'))
        if data['bmi'] >= 25:
            items.append(_('BMI cho thay ban dang thua can. Nen duy tri van dong deu dan khoang 30 phut moi ngay.'))
        if data['bloodpressure'] >= 130:
            items.append(_('Huyet ap dang o muc can luu y. Hay giam an man va theo doi huyet ap thuong xuyen.'))
        if not items:
            items.append(_('Tiep tuc duy tri loi song lanh manh va kham suc khoe dinh ky.'))
        return items

    return render_prediction_page(request, 'diabetes.html', form, payload, 'Diabetes', 'Positive', 'Negative', advices, 'diabetes')


def breast(request):
    form = BreastCancerForm(request.POST or None)
    form.model_loader = get_breast_model

    def payload(data):
        return np.array([
            data['radius'],
            data['texture'],
            data['perimeter'],
            data['area'],
            data['smoothness'],
        ]).reshape(1, 5)

    def advices(_data):
        return [
            _('Duy tri thoi quen tu kiem tra vung nguc dinh ky de phat hien som bat thuong.'),
            _('Khong nen tu y dung noi tiet hoac thuoc khong ro nguon goc khi chua co chi dinh.'),
            _('Tang cuong rau xanh, trai cay va kham tam soat theo huong dan cua bac si.'),
            _('Neu thay khoi u, dau keo dai hoac tiet dich bat thuong, hay di kham som.'),
        ]

    return render_prediction_page(request, 'breast.html', form, payload, 'Breast Cancer', 'have', "don't have", advices, 'breast')


def heart(request):
    form = HeartDiseaseForm(request.POST or None)
    form.model_loader = get_heart_model

    def payload(data):
        return np.array([
            data['age'],
            data['sex'],
            data['cp'],
            data['trestbps'],
            data['chol'],
            data['fbs'],
            data['restecg'],
            data['thalach'],
            data['exang'],
            data['oldpeak'],
            data['slope'],
            data['ca'],
            data['thal'],
        ]).reshape(1, 13)

    def advices(data):
        items = []
        if data['trestbps'] >= 130:
            items.append(_('Huyet ap nghi dang o muc cao. Ban nen giam an man va theo doi huyet ap tai nha.'))
        if data['chol'] >= 240:
            items.append(_('Cholesterol dang cao. Hay han che thuc an nhieu mo va noi tang dong vat.'))
        if data['fbs'] == 1:
            items.append(_('Duong huyet luc doi dang canh bao nguy co tim mach cao hon binh thuong.'))
        if data['exang'] == 1 or data['cp'] > 0:
            items.append(_('Neu co dau nguc hoac kho tho khi gang suc, ban nen di kham tim mach som.'))
        if not items:
            items.append(_('Tiep tuc duy tri che do an lanh manh va tap luyen nhe nhang deu dan.'))
        return items

    return render_prediction_page(request, 'heart.html', form, payload, 'Heart Disease', 'have', "don't have", advices, 'heart')


def kidney(request):
    value = ''
    error = ''
    advices = []

    if request.method == 'POST':
        form = KidneyDiseaseForm(request.POST)
        if form.is_valid():
            serum_creatinine = form.cleaned_data['serum_creatinine']
            blood_urea = form.cleaned_data['blood_urea']
            albumin = form.cleaned_data['albumin']
            hemoglobin = form.cleaned_data['hemoglobin']
            specific_gravity = form.cleaned_data['specific_gravity']
            hypertension = form.cleaned_data['hypertension']

            risk_score = 0
            if serum_creatinine > 1.2:
                risk_score += 1
            if blood_urea > 40:
                risk_score += 1
            if albumin >= 2:
                risk_score += 1
            if hemoglobin < 12:
                risk_score += 1
            if specific_gravity <= 1.015:
                risk_score += 1
            if hypertension == 1:
                risk_score += 1

            value = 'Elevated' if risk_score >= 3 else 'Lower'
            save_medical_history(request, 'Kidney Disease', value, form.cleaned_data)

            if serum_creatinine > 1.2 or blood_urea > 40:
                advices.append(_('Ure hoac creatinine dang vuot nguong tham khao. Ban nen kiem tra chuc nang than som.'))
            if hypertension == 1:
                advices.append(_('Tang huyet ap la yeu to nguy co lon voi than. Hay theo doi huyet ap deu dan.'))
            if albumin > 0:
                advices.append(_('Co dau hieu ro ri protein qua nuoc tieu, nen tham khao bac si de duoc danh gia them.'))
            if hemoglobin < 12:
                advices.append(_('Hemoglobin thap co the lien quan den thieu mau. Ban nen kiem tra them khi di kham.'))
            if not advices:
                advices.append(_('Duy tri uong du nuoc va tranh lam dung thuoc giam dau hoac thuoc khong ro nguon goc.'))
        else:
            errors = [f"{field}: {', '.join(e)}" for field, e in form.errors.items()]
            error = f"Loi nhap lieu: {' | '.join(errors)}" if errors else 'Du lieu khong hop le.'
    return render(request, 'kidney.html', {'context': value, 'error': error, 'advices': advices})


def pneumonia_detector(request):
    uploaded_image = None
    pneumonia_detected = None
    probability = None
    error = None

    if request.method == 'POST':
        form = PneumoniaUploadForm(request.POST, request.FILES)
        image_file = request.FILES.get('xray')
        error = validate_uploaded_xray(image_file)

        if form.is_valid() and not error:
            model = get_pneumonia_model()
            if model is None:
                error = 'Chua tim thay mo hinh viem phoi trong thu muc du lieu.'
            else:
                try:
                    original_image = Image.open(image_file).convert('RGB')
                    preview_image = original_image.copy()
                    processed_image = np.array(original_image.resize((224, 224))) / 255.0
                    prediction = model.predict(np.reshape(processed_image, [1, 224, 224, 3]), verbose=0)
                    probability = round(float(prediction.reshape(1, -1)[0][0]) * 100, 2)
                    pneumonia_detected = probability > 50
                    uploaded_image = image_to_base64(preview_image)
                    save_medical_history(
                        request,
                        'Pneumonia',
                        'Positive' if pneumonia_detected else 'Negative',
                        {'probability': probability},
                    )
                except Exception:
                    logger.exception('Pneumonia detection failed for upload: %s', getattr(image_file, 'name', '<unknown>'))
                    error = 'He thong phan tich anh tam thoi gap su co. Vui long thu lai sau.'
        elif not error:
            error = 'Vui long tai len mot anh X-quang hop le.'

    return render(request, 'pneumonia.html', {
        'uploaded_image': uploaded_image,
        'pneumonia_detected': pneumonia_detected,
        'probability': probability,
        'error': error,
    })


@login_required(login_url='login')
def export_health_history(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="lich-su-suc-khoe.csv"'
    writer = csv.writer(response)
    writer.writerow(('Thoi gian', 'Loai benh', 'Ket qua', 'Chi tiet chi so'))
    histories = MedicalHistory.objects.filter(user=request.user).order_by('-created_at')
    for history in histories:
        writer.writerow((
            history.created_at.strftime('%d/%m/%Y %H:%M'),
            history.disease_type,
            history.prediction_result,
            json.dumps(history.input_data or {}, ensure_ascii=False),
        ))
    return response


@login_required(login_url='login')
def history_view(request):
    histories = MedicalHistory.objects.filter(user=request.user).order_by('-created_at')

    diabetes_data = []
    blood_pressure_data = []
    for item in MedicalHistory.objects.filter(
        user=request.user, disease_type='Diabetes'
    ).order_by('created_at'):
        try:
            glucose = float((item.input_data or {}).get('glucose', 0))
        except (TypeError, ValueError):
            glucose = 0
        diabetes_data.append({
            'date': item.created_at.strftime('%d/%m'),
            'glucose': glucose,
            'result': item.prediction_result,
        })

    for item in MedicalHistory.objects.filter(
        user=request.user, disease_type='Heart Disease'
    ).order_by('created_at'):
        try:
            bp = float((item.input_data or {}).get('trestbps', 0))
        except (TypeError, ValueError):
            bp = 0
        blood_pressure_data.append({
            'date': item.created_at.strftime('%d/%m'),
            'bloodpressure': bp,
            'result': item.prediction_result,
        })

    chat_queryset = ChatMessage.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(chat_queryset, 6)
    chat_page_number = request.GET.get('chat_page', 1)
    chat_page_obj = paginator.get_page(chat_page_number)
    chat_messages = list(chat_page_obj.object_list)[::-1]

    return render(request, 'history.html', {
        'histories': histories,
        'chat_messages': chat_messages,
        'chat_page_obj': chat_page_obj,
        'diabetes_data_json': json.dumps(diabetes_data, ensure_ascii=False),
        'blood_pressure_data_json': json.dumps(blood_pressure_data, ensure_ascii=False),
    })


def build_chat_prompt(user, user_message):
    """Build prompt cho Gemini với RAG context.

    Pipeline:
      1. System prompt (rules, persona, safety)
      2. RAG context: FAQ + bác sĩ + lịch + history user (từ services_chat)
      3. Câu hỏi của user
    """
    from .services_chat import build_rag_context

    system_prompt = (
        "Bạn là Medic AI - trợ lý y tế của hệ thống đặt lịch khám và bệnh án "
        "điện tử Medic. Hãy trả lời:\n"
        "- Bằng TIẾNG VIỆT, ngắn gọn, dễ hiểu.\n"
        "- KHÔNG đưa chẩn đoán cuối cùng - luôn khuyên đi khám bác sĩ chuyên khoa.\n"
        "- Nếu hỏi về CÁCH SỬ DỤNG hệ thống → DỰA VÀO 'CONTEXT' bên dưới để trả lời.\n"
        "- Nếu trong CONTEXT có cảnh báo CẤP CỨU → ƯU TIÊN khuyên gọi 115 hoặc tới bệnh viện ngay.\n"
        "- Nếu user hỏi vượt ngoài kiến thức hệ thống Medic → trả lời theo kiến thức y học chung "
        "kèm khuyến nghị đi khám.\n"
        "- KHÔNG bịa thông tin về bác sĩ/lịch khám không có trong CONTEXT.\n\n"
    )

    # RAG: tìm context liên quan trong DB + FAQ
    try:
        rag_context = build_rag_context(user, user_message)
    except Exception:
        logger.exception('build_rag_context failed for user_id=%s', getattr(user, 'id', None))
        rag_context = ''

    if rag_context:
        system_prompt += "=== CONTEXT (data thực từ hệ thống Medic) ===\n"
        system_prompt += rag_context + "\n=== HẾT CONTEXT ===\n\n"

    # Lịch sử screening AI gần nhất của user (giữ tương thích logic cũ)
    latest_history = MedicalHistory.objects.filter(user=user).order_by('-created_at').first()
    if latest_history:
        system_prompt += (
            f"Thông tin sàng lọc gần nhất của user: bệnh {latest_history.disease_type}, "
            f"kết quả {latest_history.prediction_result}, chỉ số {latest_history.input_data or {}}.\n"
            "Hãy đưa ra hướng dẫn ngắn gọn, thực tế, và nói rõ nếu thông tin chưa đủ để kết luận.\n\n"
        )
    else:
        system_prompt += (
            "User chưa có dữ liệu sàng lọc lưu trữ. "
            "Trả lời theo kiến thức tham khảo chung.\n\n"
        )

    system_prompt += f"Câu hỏi của user: {user_message}"
    return system_prompt


def is_urgent_chat_reply(reply):
    reply = (reply or '').lower()
    urgent_keywords = (
        'cap cuu', '115', 'den benh vien ngay', 'di cap cuu ngay',
        'kho tho du doi', 'dau nguc du doi', 'mat y thuc', 'nguy hiem',
        'khan cap', 'den co so y te ngay',
    )
    return any(kw in reply for kw in urgent_keywords)


def push_urgent_chat_notification(user, reply):
    push_realtime_notification(
        user,
        title='Canh bao tu Medic AI',
        message='Medic AI vua phat hien noi dung co muc do khan. Hay mo khung chat de xem khuyen cao va can nhac di kham ngay.',
        level='danger',
        category='urgent_chat',
        link='/history/',
        payload={'preview': (reply or '')[:180]},
    )


@login_required(login_url='login')
def chat_history_api(request):
    messages = list(
        ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:20]
    )
    payload = [
        {
            'sender': m.sender,
            'message': m.message,
            'created_at': m.created_at.strftime('%d/%m/%Y %H:%M'),
        }
        for m in reversed(messages)
    ]
    return JsonResponse({'messages': payload})


@login_required(login_url='login')
def clear_chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Phuong thuc khong hop le.'}, status=405)
    ChatMessage.objects.filter(user=request.user).delete()
    request.session.pop('chat_last_sent_at', None)
    return JsonResponse({'success': True})


@login_required(login_url='login')
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Phuong thuc khong hop le.'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Du lieu gui len khong hop le.'}, status=400)

    user_message = (data.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'Vui long nhap noi dung can tu van.'}, status=400)
    if len(user_message) > 1000:
        return JsonResponse(
            {'error': 'Tin nhan qua dai. Vui long rut gon duoi 1000 ky tu.'},
            status=400,
        )

    if not getattr(settings, 'GEMINI_API_KEY', ''):
        logger.warning(
            'Chat request rejected because GEMINI_API_KEY is missing for user_id=%s',
            request.user.id,
        )
        return JsonResponse(
            {'error': 'He thong chat AI chua duoc cau hinh.'},
            status=503,
        )

    now = time.time()
    last_sent_at = request.session.get('chat_last_sent_at', 0)
    if now - last_sent_at < 2:
        return JsonResponse(
            {'error': 'Ban gui qua nhanh. Vui long doi vai giay roi thu lai.'},
            status=429,
        )
    request.session['chat_last_sent_at'] = now

    ChatMessage.objects.create(
        user=request.user,
        sender=ChatMessage.SENDER_USER,
        message=user_message,
    )

    try:
        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash'),
            contents=build_chat_prompt(request.user, user_message),
        )
        reply = (getattr(response, 'text', '') or '').strip()

        if not reply:
            logger.warning('Gemini returned empty reply for user_id=%s', request.user.id)
            return JsonResponse(
                {'error': 'AI chua tra ve noi dung hop le. Vui long thu lai sau.'},
                status=502,
            )

        ChatMessage.objects.create(
            user=request.user,
            sender=ChatMessage.SENDER_BOT,
            message=reply,
        )
        if is_urgent_chat_reply(reply):
            push_urgent_chat_notification(request.user, reply)
        return JsonResponse({'reply': reply})
    except Exception:
        logger.exception('Gemini chat request failed for user_id=%s', request.user.id)
        return JsonResponse(
            {'error': 'He thong AI tam thoi gap su co. Vui long thu lai sau.'},
            status=503,
        )
