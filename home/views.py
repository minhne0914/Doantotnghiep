import base64
import csv
import json
import joblib
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
import tensorflow as tf
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from PIL import Image

from notifications.realtime import push_realtime_notification

from .forms import BreastCancerForm, DiabetesForm, HeartDiseaseForm, KidneyDiseaseForm
from .models import ChatMessage, MedicalHistory


DATA_DIR = Path(settings.BASE_DIR) / 'data'


@lru_cache(maxsize=1)
def get_diabetes_model():
    with open(DATA_DIR / 'diabetes_model.pkl', 'rb') as file:
        return joblib.load(file)


@lru_cache(maxsize=1)
def get_breast_model():
    with open(DATA_DIR / 'breast_model.pkl', 'rb') as file:
        return joblib.load(file)


@lru_cache(maxsize=1)
def get_heart_model():
    with open(DATA_DIR / 'heart_disease_model.pkl', 'rb') as file:
        return joblib.load(file)


@lru_cache(maxsize=1)
def get_pneumonia_model():
    model_path = DATA_DIR / 'pneumonia_classifiers.h5'
    if not model_path.exists():
        return None
    return tf.keras.models.load_model(model_path, compile=True)


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


def index(request):
    return render(request, 'index.html')


def diabetes(request):
    value = ''
    error = ''
    advices = []

    if request.method == 'POST':
        form = DiabetesForm(request.POST)
        if form.is_valid():
            user_data = np.array([
                form.cleaned_data['pregnancies'],
                form.cleaned_data['glucose'],
                form.cleaned_data['bloodpressure'],
                form.cleaned_data['skinthickness'],
                form.cleaned_data['bmi'],
                form.cleaned_data['insulin'],
                form.cleaned_data['pedigree'],
                form.cleaned_data['age'],
            ]).reshape(1, 8)

            prediction = get_diabetes_model().predict(user_data)[0]
            value = 'Positive' if int(prediction) == 1 else 'Negative'
            save_medical_history(request, 'Diabetes', value, form.cleaned_data)

            if form.cleaned_data['glucose'] >= 140:
                advices.append('Đường huyết của bạn khá cao. Hãy hạn chế đồ ngọt, nước có gas và tinh bột hấp thụ nhanh.')
            if form.cleaned_data['bmi'] >= 25:
                advices.append('BMI cho thấy bạn đang thừa cân. Nên duy trì vận động đều đặn khoảng 30 phút mỗi ngày.')
            if form.cleaned_data['bloodpressure'] >= 130:
                advices.append('Huyết áp đang ở mức cần lưu ý. Hãy giảm ăn mặn và theo dõi huyết áp thường xuyên.')
            if not advices:
                advices.append('Tiếp tục duy trì lối sống lành mạnh, ăn nhiều rau xanh và khám sức khỏe định kỳ.')
        else:
            error = 'Dữ liệu không hợp lệ. Vui lòng nhập đầy đủ các chỉ số ở dạng số.'

    return render(request, 'diabetes.html', {'context': value, 'error': error, 'advices': advices})


def breast(request):
    value = ''
    error = ''
    advices = []

    if request.method == 'POST':
        form = BreastCancerForm(request.POST)
        if form.is_valid():
            user_data = np.array([
                form.cleaned_data['radius'],
                form.cleaned_data['texture'],
                form.cleaned_data['perimeter'],
                form.cleaned_data['area'],
                form.cleaned_data['smoothness'],
            ]).reshape(1, 5)

            prediction = get_breast_model().predict(user_data)[0]
            value = 'have' if int(prediction) == 1 else "don't have"
            save_medical_history(request, 'Breast Cancer', value, form.cleaned_data)

            advices = [
                'Duy trì thói quen tự kiểm tra vùng ngực định kỳ để phát hiện sớm bất thường.',
                'Không nên tự ý dùng nội tiết hoặc thuốc không rõ nguồn gốc khi chưa có chỉ định.',
                'Tăng cường rau xanh, trái cây và khám tầm soát theo hướng dẫn của bác sĩ.',
                'Nếu thấy khối u, đau kéo dài hoặc tiết dịch bất thường, hãy đi khám sớm.',
            ]
        else:
            error = 'Dữ liệu không hợp lệ. Vui lòng nhập đầy đủ các chỉ số ở dạng số.'

    return render(request, 'breast.html', {'context': value, 'error': error, 'advices': advices})


def heart(request):
    value = ''
    error = ''
    advices = []

    if request.method == 'POST':
        form = HeartDiseaseForm(request.POST)
        if form.is_valid():
            user_data = np.array([
                form.cleaned_data['age'],
                form.cleaned_data['sex'],
                form.cleaned_data['cp'],
                form.cleaned_data['trestbps'],
                form.cleaned_data['chol'],
                form.cleaned_data['fbs'],
                form.cleaned_data['restecg'],
                form.cleaned_data['thalach'],
                form.cleaned_data['exang'],
                form.cleaned_data['oldpeak'],
                form.cleaned_data['slope'],
                form.cleaned_data['ca'],
                form.cleaned_data['thal'],
            ]).reshape(1, 13)

            prediction = get_heart_model().predict(user_data)[0]
            value = 'have' if int(prediction) == 1 else "don't have"
            save_medical_history(request, 'Heart Disease', value, form.cleaned_data)

            if form.cleaned_data['trestbps'] >= 130:
                advices.append('Huyết áp nghỉ đang ở mức cao. Bạn nên giảm ăn mặn và theo dõi huyết áp tại nhà.')
            if form.cleaned_data['chol'] >= 240:
                advices.append('Cholesterol đang cao. Hãy hạn chế thức ăn nhiều mỡ và nội tạng động vật.')
            if form.cleaned_data['fbs'] == 1:
                advices.append('Đường huyết lúc đói đang cảnh báo nguy cơ tim mạch cao hơn bình thường.')
            if form.cleaned_data['exang'] == 1 or form.cleaned_data['cp'] > 0:
                advices.append('Nếu có đau ngực hoặc khó thở khi gắng sức, bạn nên đi khám tim mạch sớm.')
            if not advices:
                advices.append('Tiếp tục duy trì chế độ ăn lành mạnh và tập luyện nhẹ nhàng, đều đặn.')
        else:
            error = 'Dữ liệu không hợp lệ. Vui lòng nhập đầy đủ các chỉ số ở dạng số.'

    return render(request, 'heart.html', {'context': value, 'error': error, 'advices': advices})


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
                advices.append('Ure hoặc creatinine đang vượt ngưỡng tham khảo. Bạn nên kiểm tra chức năng thận sớm.')
            if hypertension == 1:
                advices.append('Tăng huyết áp là yếu tố nguy cơ lớn với thận. Hãy theo dõi huyết áp đều đặn.')
            if albumin > 0:
                advices.append('Có dấu hiệu rò rỉ protein qua nước tiểu, nên tham khảo bác sĩ để được đánh giá thêm.')
            if hemoglobin < 12:
                advices.append('Hemoglobin thấp có thể liên quan đến thiếu máu. Bạn nên kiểm tra thêm khi đi khám.')
            if not advices:
                advices.append('Duy trì uống đủ nước và tránh lạm dụng thuốc giảm đau hoặc thuốc không rõ nguồn gốc.')
        else:
            error = 'Dữ liệu không hợp lệ. Vui lòng nhập đầy đủ các chỉ số ở dạng số.'

    return render(request, 'kidney.html', {'context': value, 'error': error, 'advices': advices})


def pneumonia_detector(request):
    uploaded_image = None
    pneumonia_detected = None
    probability = None
    error = None

    if request.method == 'POST':
        img = request.FILES.get('xray')
        if img is None:
            error = 'Vui lòng chọn ảnh X-quang trước khi sàng lọc.'
        else:
            original_image = Image.open(img).convert('RGB')
            preview_image = original_image.copy()
            processed_image = np.array(original_image.resize((224, 224))) / 255.0
            model = get_pneumonia_model()

            if model is None:
                error = 'Chưa tìm thấy mô hình viêm phổi trong thư mục dữ liệu.'
            else:
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
    writer.writerow(['Thời gian', 'Loại bệnh', 'Kết quả', 'Chi tiết chỉ số'])

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
        'Bạn là trợ lý y tế Medic AI. Hãy trả lời bằng tiếng Việt rõ ràng, thân thiện và an toàn. '
        'Không đưa ra kết luận chẩn đoán cuối cùng và luôn khuyên người dùng đi khám khi cần.\n\n'
    )
    latest_history = MedicalHistory.objects.filter(user=user).order_by('-created_at').first()
    if latest_history:
        context_string += (
            f'Thông tin sàng lọc gần nhất: bệnh {latest_history.disease_type}, '
            f'kết quả {latest_history.prediction_result}, chỉ số {latest_history.input_data}.\n'
        )
        context_string += 'Hãy đưa ra hướng dẫn ngắn gọn, thực tế, và nói rõ nếu thông tin chưa đủ để kết luận.\n'
    else:
        context_string += 'Người dùng chưa có dữ liệu sàng lọc lưu trữ. Hãy trả lời ở mức tham khảo chung.\n'
    return context_string + '\nCâu hỏi của người dùng: ' + user_message


def is_urgent_chat_reply(reply):
    normalized = (reply or '').lower()
    urgent_keywords = [
        'cấp cứu',
        '115',
        'đến bệnh viện ngay',
        'đi cấp cứu ngay',
        'khó thở dữ dội',
        'đau ngực dữ dội',
        'mất ý thức',
        'nguy hiểm',
        'khẩn cấp',
        'đến cơ sở y tế ngay',
    ]
    return any(keyword in normalized for keyword in urgent_keywords)


def push_urgent_chat_notification(user, reply):
    push_realtime_notification(
        user,
        title='Cảnh báo từ Medic AI',
        message='Medic AI vừa phát hiện nội dung có mức độ khẩn. Hãy mở khung chat để xem khuyến cáo và cân nhắc đi khám ngay.',
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
        return JsonResponse({'error': 'Phương thức không hợp lệ.'}, status=405)

    ChatMessage.objects.filter(user=request.user).delete()
    request.session.pop('chat_last_sent_at', None)
    return JsonResponse({'success': True})


@login_required(login_url='login')
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Phương thức không hợp lệ.'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dữ liệu gửi lên không hợp lệ.'}, status=400)

    user_message = (data.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'Vui lòng nhập nội dung cần tư vấn.'}, status=400)
    if len(user_message) > 1000:
        return JsonResponse({'error': 'Tin nhắn quá dài. Vui lòng rút gọn dưới 1000 ký tự.'}, status=400)

    now = time.time()
    last_sent_at = request.session.get('chat_last_sent_at', 0)
    if now - last_sent_at < 2:
        return JsonResponse({'error': 'Bạn gửi quá nhanh. Vui lòng đợi vài giây rồi thử lại.'}, status=429)
    request.session['chat_last_sent_at'] = now

    ChatMessage.objects.create(
        user=request.user,
        sender=ChatMessage.SENDER_USER,
        message=user_message,
    )

    try:
        import google.generativeai as genai

        if not getattr(settings, 'GEMINI_API_KEY', None):
            return JsonResponse({'error': 'Hệ thống chat AI chưa được cấu hình.'}, status=503)

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(build_chat_prompt(request.user, user_message))
        reply = getattr(response, 'text', '').strip()

        if not reply:
            return JsonResponse({'error': 'AI chưa trả về nội dung hợp lệ. Vui lòng thử lại sau.'}, status=502)

        ChatMessage.objects.create(
            user=request.user,
            sender=ChatMessage.SENDER_BOT,
            message=reply,
        )
        if is_urgent_chat_reply(reply):
            push_urgent_chat_notification(request.user, reply)
        return JsonResponse({'reply': reply})
    except Exception:
        return JsonResponse({'error': 'Hệ thống AI tạm thời gặp sự cố. Vui lòng thử lại sau.'}, status=503)
