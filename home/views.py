import base64
import csv
import json
import logging
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
import tensorflow as tf
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from PIL import Image, UnidentifiedImageError

from notifications.realtime import push_realtime_notification

from .forms import (
    BreastCancerForm,
    DiabetesForm,
    HeartDiseaseForm,
    KidneyDiseaseForm,
    PneumoniaUploadForm,
)
from .models import ChatMessage, MedicalHistory


DATA_DIR = Path(settings.BASE_DIR) / 'data'
ALLOWED_XRAY_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
logger = logging.getLogger(__name__)


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


def run_prediction(model, user_data, prediction_name):
    if model is None:
        return None, 'Mo hinh du doan hien khong kha dung. Vui long thu lai sau.'

    try:
        return model.predict(user_data)[0], ''
    except Exception:
        logger.exception('Prediction failed for %s', prediction_name)
        return None, 'He thong du doan tam thoi gap su co. Vui long thu lai sau.'


def validate_uploaded_xray(uploaded_file):
    if uploaded_file is None:
        return 'Vui long chon anh X-quang truoc khi sang loc.'

    if uploaded_file.size > getattr(settings, 'MAX_XRAY_UPLOAD_BYTES', 5 * 1024 * 1024):
        return 'Anh tai len vuot qua gioi han dung luong cho phep.'

    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    if content_type and content_type not in getattr(
        settings,
        'ALLOWED_XRAY_CONTENT_TYPES',
        ('image/jpeg', 'image/png', 'image/webp'),
    ):
        return 'Dinh dang anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.'

    suffix = Path(uploaded_file.name or '').suffix.lower()
    if suffix and suffix not in ALLOWED_XRAY_EXTENSIONS:
        return 'Ten file anh khong hop le. Chi chap nhan JPG, PNG hoac WEBP.'

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.verify()
        uploaded_file.seek(0)
    except (UnidentifiedImageError, OSError):
        logger.warning('Invalid xray upload received: %s', getattr(uploaded_file, 'name', '<unknown>'))
        return 'File tai len khong phai la anh hop le.'

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
            error = 'Du lieu khong hop le. Vui long nhap day du cac chi so o dang so.'

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
            items.append('Duong huyet cua ban kha cao. Hay han che do ngot va tinh bot hap thu nhanh.')
        if data['bmi'] >= 25:
            items.append('BMI cho thay ban dang thua can. Nen duy tri van dong deu dan khoang 30 phut moi ngay.')
        if data['bloodpressure'] >= 130:
            items.append('Huyet ap dang o muc can luu y. Hay giam an man va theo doi huyet ap thuong xuyen.')
        if not items:
            items.append('Tiep tuc duy tri loi song lanh manh va kham suc khoe dinh ky.')
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
            'Duy tri thoi quen tu kiem tra vung nguc dinh ky de phat hien som bat thuong.',
            'Khong nen tu y dung noi tiet hoac thuoc khong ro nguon goc khi chua co chi dinh.',
            'Tang cuong rau xanh, trai cay va kham tam soat theo huong dan cua bac si.',
            'Neu thay khoi u, dau keo dai hoac tiet dich bat thuong, hay di kham som.',
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
            items.append('Huyet ap nghi dang o muc cao. Ban nen giam an man va theo doi huyet ap tai nha.')
        if data['chol'] >= 240:
            items.append('Cholesterol dang cao. Hay han che thuc an nhieu mo va noi tang dong vat.')
        if data['fbs'] == 1:
            items.append('Duong huyet luc doi dang canh bao nguy co tim mach cao hon binh thuong.')
        if data['exang'] == 1 or data['cp'] > 0:
            items.append('Neu co dau nguc hoac kho tho khi gang suc, ban nen di kham tim mach som.')
        if not items:
            items.append('Tiep tuc duy tri che do an lanh manh va tap luyen nhe nhang deu dan.')
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
                advices.append('Ure hoac creatinine dang vuot nguong tham khao. Ban nen kiem tra chuc nang than som.')
            if hypertension == 1:
                advices.append('Tang huyet ap la yeu to nguy co lon voi than. Hay theo doi huyet ap deu dan.')
            if albumin > 0:
                advices.append('Co dau hieu ro ri protein qua nuoc tieu, nen tham khao bac si de duoc danh gia them.')
            if hemoglobin < 12:
                advices.append('Hemoglobin thap co the lien quan den thieu mau. Ban nen kiem tra them khi di kham.')
            if not advices:
                advices.append('Duy tri uong du nuoc va tranh lam dung thuoc giam dau hoac thuoc khong ro nguon goc.')
        else:
            error = 'Du lieu khong hop le. Vui long nhap day du cac chi so o dang so.'

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
    writer.writerow(['Thoi gian', 'Loai benh', 'Ket qua', 'Chi tiet chi so'])

    histories = MedicalHistory.objects.filter(user=request.user).order_by('-created_at')
    for history in histories:
        writer.writerow([
            history.created_at.strftime('%d/%m/%Y %H:%M'),
            history.disease_type,
            history.prediction_result,
            json.dumps(history.input_data, ensure_ascii=False) if history.input_data else '',
        ])

    return response


@login_required(login_url='login')
def history_view(request):
    histories = MedicalHistory.objects.filter(user=request.user).order_by('-created_at')
    diabetes_data = []
    blood_pressure_data = []

    for item in MedicalHistory.objects.filter(user=request.user, disease_type='Diabetes').order_by('created_at'):
        if item.input_data and 'glucose' in item.input_data:
            diabetes_data.append({
                'date': item.created_at.strftime('%d/%m'),
                'glucose': float(item.input_data['glucose']),
                'result': item.prediction_result,
            })

    for item in MedicalHistory.objects.filter(user=request.user, disease_type='Heart Disease').order_by('created_at'):
        if item.input_data and 'trestbps' in item.input_data:
            blood_pressure_data.append({
                'date': item.created_at.strftime('%d/%m'),
                'bloodpressure': float(item.input_data['trestbps']),
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
        'diabetes_data_json': json.dumps(diabetes_data),
        'blood_pressure_data_json': json.dumps(blood_pressure_data),
    })


def build_chat_prompt(user, user_message):
    context_string = (
        'Ban la tro ly y te Medic AI. Hay tra loi bang tieng Viet ro rang, than thien va an toan. '
        'Khong dua ra ket luan chan doan cuoi cung va luon khuyen nguoi dung di kham khi can.\n\n'
    )
    latest_history = MedicalHistory.objects.filter(user=user).order_by('-created_at').first()
    if latest_history:
        context_string += (
            f'Thong tin sang loc gan nhat: benh {latest_history.disease_type}, '
            f'ket qua {latest_history.prediction_result}, chi so {latest_history.input_data}.\n'
        )
        context_string += 'Hay dua ra huong dan ngan gon, thuc te, va noi ro neu thong tin chua du de ket luan.\n'
    else:
        context_string += 'Nguoi dung chua co du lieu sang loc luu tru. Hay tra loi o muc tham khao chung.\n'
    return context_string + '\nCau hoi cua nguoi dung: ' + user_message


def is_urgent_chat_reply(reply):
    normalized = (reply or '').lower()
    urgent_keywords = [
        'cap cuu',
        '115',
        'den benh vien ngay',
        'di cap cuu ngay',
        'kho tho du doi',
        'dau nguc du doi',
        'mat y thuc',
        'nguy hiem',
        'khan cap',
        'den co so y te ngay',
    ]
    return any(keyword in normalized for keyword in urgent_keywords)


def push_urgent_chat_notification(user, reply):
    push_realtime_notification(
        user,
        title='Canh bao tu Medic AI',
        message='Medic AI vua phat hien noi dung co muc do khan. Hay mo khung chat de xem khuyen cao va can nhac di kham ngay.',
        level='danger',
        category='urgent_chat',
        link='/history/',
        payload={
            'preview': reply[:180],
        },
    )


@login_required(login_url='login')
def chat_history_api(request):
    messages = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:20]
    payload = [{
        'sender': message.sender,
        'message': message.message,
        'created_at': message.created_at.strftime('%H:%M %d/%m'),
    } for message in reversed(messages)]
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
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Du lieu gui len khong hop le.'}, status=400)

    user_message = (data.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'Vui long nhap noi dung can tu van.'}, status=400)
    if len(user_message) > 1000:
        return JsonResponse({'error': 'Tin nhan qua dai. Vui long rut gon duoi 1000 ky tu.'}, status=400)

    if not getattr(settings, 'GEMINI_API_KEY', None):
        logger.warning('Chat request rejected because GEMINI_API_KEY is missing for user_id=%s', request.user.id)
        return JsonResponse({'error': 'He thong chat AI chua duoc cau hinh.'}, status=503)

    now = time.time()
    last_sent_at = request.session.get('chat_last_sent_at', 0)
    if now - last_sent_at < 2:
        return JsonResponse({'error': 'Ban gui qua nhanh. Vui long doi vai giay roi thu lai.'}, status=429)
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
            return JsonResponse({'error': 'AI chua tra ve noi dung hop le. Vui long thu lai sau.'}, status=502)

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
        return JsonResponse({'error': 'He thong AI tam thoi gap su co. Vui long thu lai sau.'}, status=503)
