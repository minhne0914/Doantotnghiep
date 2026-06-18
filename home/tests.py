import io
import json
from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import ChatMessage, MedicalHistory
from .services_chat import build_local_chat_response, build_rag_context, detect_intents


User = get_user_model()


def build_test_image(name='xray.png', image_format='PNG', content_type='image/png', size=(16, 16)):
    buffer = io.BytesIO()
    Image.new('RGB', size, color='white').save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class PredictionEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='patient@example.com',
            password='secret123',
            role='patient',
        )

    def test_diabetes_endpoint_handles_missing_model_gracefully(self):
        with patch('home.views.get_diabetes_model', return_value=None):
            response = self.client.post(reverse('diabetes'), {
                'pregnancies': 1,
                'glucose': 150,
                'bloodpressure': 80,
                'skinthickness': 20,
                'bmi': 24,
                'insulin': 85,
                'pedigree': 0.5,
                'age': 30,
            })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mo hinh du doan hien khong kha dung', status_code=200)

    def test_breast_endpoint_returns_prediction(self):
        mock_model = Mock()
        mock_model.predict.return_value = [1]

        with patch('home.views.get_breast_model', return_value=mock_model):
            response = self.client.post(reverse('breast'), {
                'radius': 12,
                'texture': 15,
                'perimeter': 80,
                'area': 300,
                'smoothness': 0.1,
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['context'], 'have')

    def test_heart_endpoint_returns_prediction(self):
        mock_model = Mock()
        mock_model.predict.return_value = [0]

        with patch('home.views.get_heart_model', return_value=mock_model):
            response = self.client.post(reverse('heart'), {
                'age': 45,
                'sex': 1,
                'cp': 0,
                'trestbps': 120,
                'chol': 180,
                'fbs': 0,
                'restecg': 1,
                'thalach': 150,
                'exang': 0,
                'oldpeak': 1,
                'slope': 2,
                'ca': 0,
                'thal': 2,
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['context'], "don't have")

    def test_kidney_endpoint_returns_assessment(self):
        response = self.client.post(reverse('kidney'), {
            'serum_creatinine': 1.4,
            'blood_urea': 45,
            'albumin': 2,
            'hemoglobin': 11,
            'specific_gravity': 1.010,
            'hypertension': 1,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['context'], 'Elevated')

    def test_pneumonia_endpoint_rejects_invalid_content_type(self):
        invalid_upload = build_test_image(name='xray.gif', image_format='PNG', content_type='image/gif')

        response = self.client.post(reverse('pneumonia_detector'), {'xray': invalid_upload})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dinh dang anh khong hop le', status_code=200)

    @override_settings(MAX_XRAY_UPLOAD_BYTES=10)
    def test_pneumonia_endpoint_rejects_oversized_upload(self):
        large_upload = build_test_image()

        response = self.client.post(reverse('pneumonia_detector'), {'xray': large_upload})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'vuot qua gioi han dung luong', status_code=200)

    def test_pneumonia_endpoint_handles_missing_model_gracefully(self):
        upload = build_test_image()

        with patch('home.views.get_pneumonia_model', return_value=None):
            response = self.client.post(reverse('pneumonia_detector'), {'xray': upload})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chua tim thay mo hinh viem phoi', status_code=200)

    def test_pneumonia_endpoint_returns_prediction(self):
        upload = build_test_image()
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[0.9]])

        self.client.force_login(self.user)
        with patch('home.views.get_pneumonia_model', return_value=mock_model):
            response = self.client.post(reverse('pneumonia_detector'), {'xray': upload})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['probability'], 90.0)
        self.assertTrue(MedicalHistory.objects.filter(user=self.user, disease_type='Pneumonia').exists())

    def test_skin_cancer_endpoint_renders_upload_page(self):
        response = self.client.get(reverse('skin_cancer_detector'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sàng lọc tổn thương da bằng AI', status_code=200)

    def test_skin_cancer_endpoint_handles_missing_model_gracefully(self):
        upload = build_test_image(name='lesion.png', image_format='PNG', content_type='image/png')

        with patch('home.views.get_skin_cancer_model', return_value=None):
            response = self.client.post(reverse('skin_cancer_detector'), {'skin_image': upload})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mô hình sàng lọc ung thư da chưa được triển khai', status_code=200)

    def test_skin_cancer_endpoint_returns_prediction_and_saves_history(self):
        upload = build_test_image(name='lesion.png', image_format='PNG', content_type='image/png', size=(120, 120))
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[0.02, 0.88, 0.03, 0.01, 0.03, 0.02, 0.01]])

        self.client.force_login(self.user)
        with patch('home.views.get_skin_cancer_model', return_value=mock_model):
            response = self.client.post(reverse('skin_cancer_detector'), {'skin_image': upload})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['top_class']['code'], 'bcc')
        self.assertTrue(response.context['is_dangerous'])
        self.assertTrue(MedicalHistory.objects.filter(user=self.user, disease_type='Skin Cancer').exists())


class HistoryEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='history@example.com',
            password='secret123',
            role='patient',
        )

    def test_history_requires_login(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 302)

    def test_history_page_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        MedicalHistory.objects.create(
            user=self.user,
            disease_type='Diabetes',
            prediction_result='Positive',
            input_data={'glucose': 150},
        )

        response = self.client.get(reverse('history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Positive', status_code=200)

    def test_export_health_history_returns_csv(self):
        self.client.force_login(self.user)
        MedicalHistory.objects.create(
            user=self.user,
            disease_type='Heart Disease',
            prediction_result='Negative',
            input_data={'trestbps': 120},
        )

        response = self.client.get(reverse('export_health_history'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8-sig')
        self.assertIn('Heart Disease', response.content.decode('utf-8-sig'))


class ChatEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='chat@example.com',
            password='secret123',
            role='patient',
        )

    def test_chat_api_requires_login(self):
        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'message': 'Xin chao'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)

    @override_settings(GEMINI_API_KEY='')
    def test_chat_api_uses_local_fallback_when_key_missing(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'message': 'Xin chao'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('reply', response.json())
        self.assertEqual(ChatMessage.objects.filter(user=self.user).count(), 2)

    @override_settings(GEMINI_API_KEY='test-key', GEMINI_MODEL='gemini-2.5-flash')
    def test_chat_api_returns_reply_and_saves_messages(self):
        self.client.force_login(self.user)
        fake_response = SimpleNamespace(text='Ban nen theo doi them va di kham neu trieu chung tang.')
        fake_client = Mock()
        fake_client.models.generate_content.return_value = fake_response

        with patch('google.genai.Client', return_value=fake_client):
            response = self.client.post(
                reverse('chat_api'),
                data=json.dumps({'message': 'Toi bi ho'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reply'], fake_response.text)
        self.assertEqual(ChatMessage.objects.filter(user=self.user).count(), 2)

    @override_settings(GEMINI_API_KEY='test-key', GEMINI_MODEL='gemini-2.5-flash')
    def test_chat_api_sends_recent_chat_context_to_provider(self):
        self.client.force_login(self.user)
        ChatMessage.objects.create(user=self.user, sender='user', message='Tôi bị đau đầu từ hôm qua')
        ChatMessage.objects.create(user=self.user, sender='bot', message='Bạn nên theo dõi thêm triệu chứng.')
        fake_response = SimpleNamespace(text='Bạn nên nghỉ ngơi và đi khám nếu đau tăng.')
        fake_client = Mock()
        fake_client.models.generate_content.return_value = fake_response

        with patch('google.genai.Client', return_value=fake_client):
            response = self.client.post(
                reverse('chat_api'),
                data=json.dumps({'message': 'Vậy tôi nên làm gì tiếp?'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        prompt = fake_client.models.generate_content.call_args.kwargs['contents']
        self.assertIn('Ngữ cảnh hội thoại gần đây', prompt)
        self.assertIn('Tôi bị đau đầu từ hôm qua', prompt)
        self.assertEqual(prompt.count('Vậy tôi nên làm gì tiếp?'), 1)

    @override_settings(GEMINI_API_KEY='test-key')
    def test_chat_api_uses_local_fallback_when_provider_fails(self):
        self.client.force_login(self.user)

        with patch('google.genai.Client', side_effect=RuntimeError('provider down')):
            with self.assertLogs('home.views', level='ERROR'):
                response = self.client.post(
                    reverse('chat_api'),
                    data=json.dumps({'message': 'Toi bi sot'}),
                    content_type='application/json',
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn('reply', response.json())
        self.assertEqual(ChatMessage.objects.filter(user=self.user).count(), 2)

    @override_settings(GEMINI_API_KEY='')
    def test_chat_api_returns_db_backed_booking_actions(self):
        from appoinment.models import Appointment, TakeAppointment

        doctor = User.objects.create_user(
            email='doctor-actions@example.com',
            password='secret123',
            role='doctor',
            first_name='An',
            last_name='Nguyen',
        )
        appointment = Appointment.objects.create(
            user=doctor,
            full_name='BS An Nguyen',
            location='Ha Noi',
            qualification_name='CKI',
            institute_name='Medic',
            hospital_name='Medic Center',
            department='Heart Disease',
            start_time=time(9, 0),
            end_time=time(9, 30),
            date=timezone.localdate() + timedelta(days=1),
        )
        TakeAppointment.objects.create(
            user=self.user,
            appointment=appointment,
            full_name='Patient Test',
            phone_number='0900000000',
            date=appointment.date,
            time=appointment.start_time,
            status=TakeAppointment.STATUS_CONFIRMED,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('chat_api'),
            data=json.dumps({'message': 'Toi co lich hen nao sap toi khong?'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('BS. An Nguyen', payload['reply'])
        self.assertTrue(payload['actions'])
        self.assertEqual(payload['source'], 'local_bookings')

    def test_chatbot_treats_today_schedule_question_as_user_bookings(self):
        from appoinment.models import Appointment, TakeAppointment

        doctor = User.objects.create_user(
            email='doctor-today@example.com',
            password='secret123',
            role='doctor',
            first_name='Minh',
            last_name='Hoang',
        )
        appointment = Appointment.objects.create(
            user=doctor,
            full_name='BS Minh Hoang',
            location='Da Nang',
            qualification_name='CKI',
            institute_name='Medic',
            hospital_name='Medic Center',
            department='Eye Care',
            start_time=time(14, 0),
            end_time=time(14, 30),
            date=timezone.localdate(),
        )
        TakeAppointment.objects.create(
            user=self.user,
            appointment=appointment,
            full_name='Patient Test',
            phone_number='0900000000',
            date=appointment.date,
            time=appointment.start_time,
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        message = 'hom nay co lich kham khong?'
        self.assertIn('my_bookings', detect_intents(message))

        payload = build_local_chat_response(self.user, message)

        self.assertEqual(payload['source'], 'local_bookings')
        self.assertIn('Hom nay ban co lich kham', payload['reply'])
        self.assertIn('BS. Minh Hoang', payload['reply'])
        self.assertNotIn('khung kham con trong', payload['reply'])

    def test_chatbot_says_no_booking_for_empty_today_schedule(self):
        message = 'hom nay co lich kham khong?'

        payload = build_local_chat_response(self.user, message)

        self.assertEqual(payload['source'], 'local_bookings')
        self.assertIn('Hom nay ban khong co lich kham', payload['reply'])

    def test_chatbot_returns_doctor_schedule_for_doctor_user(self):
        from appoinment.models import Appointment, TakeAppointment

        doctor = User.objects.create_user(
            email='doctor-schedule@example.com',
            password='secret123',
            role='doctor',
            first_name='An',
            last_name='Tran',
        )
        patient = User.objects.create_user(
            email='patient-schedule@example.com',
            password='secret123',
            role='patient',
            first_name='Patient',
            last_name='One',
        )
        appointment = Appointment.objects.create(
            user=doctor,
            full_name='BS An Tran',
            location='Da Nang',
            qualification_name='CKI',
            institute_name='Medic',
            hospital_name='Medic Center',
            department='Cardiology',
            start_time=time(8, 30),
            end_time=time(9, 0),
            date=timezone.localdate(),
        )
        TakeAppointment.objects.create(
            user=patient,
            appointment=appointment,
            full_name='Patient One',
            phone_number='0900000001',
            date=appointment.date,
            time=appointment.start_time,
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        payload = build_local_chat_response(doctor, 'Do I have appointments today?')

        self.assertEqual(payload['source'], 'local_doctor_schedule')
        self.assertIn('Today you have these active appointments', payload['reply'])
        self.assertIn('Patient One', payload['reply'])
        self.assertTrue(any(action['label'] == 'Open first patient chat' for action in payload['actions']))

    def test_chatbot_emergency_warning_uses_local_response(self):
        payload = build_local_chat_response(
            self.user,
            'I have chest pain and shortness of breath',
        )

        self.assertEqual(payload['source'], 'local_emergency')
        self.assertIn('115', payload['reply'])
        self.assertTrue(payload['actions'])

    def test_chat_history_endpoint_returns_messages(self):
        self.client.force_login(self.user)
        ChatMessage.objects.create(user=self.user, sender='user', message='Xin chao')
        ChatMessage.objects.create(user=self.user, sender='bot', message='Chao ban')

        response = self.client.get(reverse('chat_history_api'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['messages']), 2)

    def test_clear_chat_endpoint_removes_messages(self):
        self.client.force_login(self.user)
        ChatMessage.objects.create(user=self.user, sender='user', message='Xin chao')

        response = self.client.post(reverse('clear_chat_api'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_rag_context_excludes_already_booked_slots(self):
        from appoinment.models import Appointment, TakeAppointment

        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='secret123',
            role='doctor',
            first_name='An',
            last_name='Nguyen',
        )
        slot_date = timezone.localdate() + timedelta(days=1)
        free_slot = Appointment.objects.create(
            user=doctor,
            full_name='BS An Nguyen',
            location='Ha Noi',
            qualification_name='CKI',
            institute_name='Medic',
            hospital_name='Medic Center',
            department='Heart Disease',
            start_time=time(9, 0),
            end_time=time(9, 30),
            date=slot_date,
        )
        booked_slot = Appointment.objects.create(
            user=doctor,
            full_name='BS An Nguyen',
            location='Ha Noi',
            qualification_name='CKI',
            institute_name='Medic',
            hospital_name='Medic Center',
            department='Heart Disease',
            start_time=time(10, 0),
            end_time=time(10, 30),
            date=slot_date,
        )
        TakeAppointment.objects.create(
            user=self.user,
            appointment=booked_slot,
            full_name='Patient Test',
            phone_number='0900000000',
            date=booked_slot.date,
            time=booked_slot.start_time,
            status=TakeAppointment.STATUS_CONFIRMED,
        )

        context = build_rag_context(self.user, 'Có lịch khám tim mạch nào trong tuần không?')

        self.assertIn(free_slot.start_time.strftime('%H:%M'), context)
        self.assertNotIn(booked_slot.start_time.strftime('%H:%M'), context)
