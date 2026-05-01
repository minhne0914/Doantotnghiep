"""RAG (Retrieval-Augmented Generation) cho Medic Chatbot.

Module này không "train" model - thay vào đó nó:
  1. Detect intent từ câu hỏi của user (rule-based keyword matching)
  2. Search dữ liệu liên quan trong DB (bác sĩ, lịch, FAQ, lịch sử user)
  3. Build context block để inject vào prompt cho Gemini

Cách dùng:
    from home.services_chat import build_rag_context
    context = build_rag_context(user, user_message)
    # context là string đã format, sẵn sàng append vào prompt
"""

import json
import logging
import re
import unicodedata
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db.models import Avg, Q
from django.utils import timezone


logger = logging.getLogger(__name__)


# =============================================================================
# Constants & paths
# =============================================================================

DATA_DIR = Path(settings.BASE_DIR) / 'data'
FAQ_PATH = DATA_DIR / 'medic_faq.json'

# Số lượng tối đa block đưa vào context (tránh prompt quá dài)
MAX_FAQS_IN_CONTEXT = 3
MAX_DOCTORS_IN_CONTEXT = 5
MAX_SLOTS_IN_CONTEXT = 5
MAX_HISTORY_IN_CONTEXT = 3
MAX_BOOKINGS_IN_CONTEXT = 3


# =============================================================================
# Intent detection - rule-based keyword matching
# =============================================================================

# Mỗi intent có list keyword. Keyword match "any of" → intent active.
INTENT_KEYWORDS = {
    'doctor': [
        'bác sĩ', 'bs', 'doctor', 'chuyên khoa', 'specialist',
        'tim mạch', 'tiểu đường', 'ung thư', 'da liễu', 'nha khoa',
        'mắt', 'tai mũi họng', 'thần kinh',
    ],
    'appointment': [
        'lịch', 'đặt khám', 'đặt hẹn', 'book', 'appointment', 'ca khám',
        'thứ', 'chủ nhật', 'sáng mai', 'hôm nay', 'ngày mai', 'tuần',
        'giờ khám', 'slot', 'khung giờ',
    ],
    'my_history': [
        'lịch sử của tôi', 'kết quả của tôi', 'tôi đã khám', 'tôi đã làm',
        'tôi có', 'của tôi', 'my history', 'my result',
    ],
    'my_bookings': [
        'lịch của tôi', 'lịch tôi đã đặt', 'lịch hẹn của tôi',
        'my appointment', 'my booking',
    ],
    'emergency': [
        'cấp cứu', 'khẩn cấp', '115', 'đột tử', 'đột quỵ',
        'khó thở', 'đau ngực', 'mất ý thức', 'co giật', 'chảy máu',
    ],
    'screening': [
        'sàng lọc', 'screening', 'dự đoán', 'AI', 'kiểm tra',
        'tiểu đường', 'ung thư', 'tim', 'thận', 'viêm phổi',
    ],
}


def _normalize(text):
    """Lowercase + bỏ dấu để so sánh keyword chính xác hơn.

    Trả về tuple (text_lowercase_d, text_no_accent) để hỗ trợ cả
    substring match có dấu lẫn không dấu.
    """
    if not text:
        return ('', '')
    text = text.lower()
    # Decompose unicode để bỏ dấu tiếng Việt
    nfkd = unicodedata.normalize('NFD', text)
    no_accent = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Replace 'đ' → 'd' (không bị NFD phân tách)
    no_accent = no_accent.replace('đ', 'd').replace('Đ', 'D')
    return (text, no_accent)


def detect_intents(user_message):
    """Trả về set intent đang active dựa trên keyword."""
    msg_lower, msg_no_accent = _normalize(user_message)
    intents = set()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            kw_lower = kw.lower()
            _, kw_no_accent = _normalize(kw)
            if kw_lower in msg_lower or kw_no_accent in msg_no_accent:
                intents.add(intent)
                break
    return intents


# =============================================================================
# FAQ search - keyword overlap scoring
# =============================================================================

@lru_cache(maxsize=1)
def load_faqs():
    """Load FAQ JSON. Cache để tránh đọc file mỗi request."""
    if not FAQ_PATH.exists():
        logger.warning('FAQ file not found at %s', FAQ_PATH)
        return []
    try:
        with open(FAQ_PATH, encoding='utf-8') as f:
            data = json.load(f)
        return data.get('faqs', [])
    except (OSError, json.JSONDecodeError):
        logger.exception('Failed to load FAQ from %s', FAQ_PATH)
        return []


def _tokenize(text):
    """Tokenize đơn giản: lowercase, bỏ dấu, split theo non-alphanumeric."""
    if not text:
        return set()
    text_lower, text_no_accent = _normalize(text)
    # Tokens với dấu (cho match từ tiếng Việt nguyên gốc)
    tokens = set(re.findall(r'\w+', text_lower, flags=re.UNICODE))
    # Tokens không dấu (cho match khi user gõ không dấu)
    tokens.update(re.findall(r'\w+', text_no_accent, flags=re.UNICODE))
    # Loại stopwords ngắn
    return {t for t in tokens if len(t) >= 2}


def search_faqs(user_message, top_k=MAX_FAQS_IN_CONTEXT):
    """Tìm top-k FAQ liên quan nhất bằng keyword overlap.

    Score = số keyword/token chung giữa câu hỏi và (keywords + question) của FAQ.
    Đơn giản nhưng đủ tốt cho dataset 30 FAQ.
    """
    faqs = load_faqs()
    if not faqs:
        return []

    user_tokens = _tokenize(user_message)
    if not user_tokens:
        return []

    scored = []
    for faq in faqs:
        # Build searchable text: keywords + question
        searchable = ' '.join(faq.get('keywords', [])) + ' ' + faq.get('question', '')
        faq_tokens = _tokenize(searchable)
        # Overlap score
        overlap = len(user_tokens & faq_tokens)
        # Boost nếu có keyword phrase match nguyên cụm
        msg_lower, _ = _normalize(user_message)
        for kw in faq.get('keywords', []):
            kw_lower, _ = _normalize(kw)
            if len(kw_lower) >= 4 and kw_lower in msg_lower:
                overlap += 3  # match phrase = mạnh hơn match token
        if overlap > 0:
            scored.append((overlap, faq))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [faq for _, faq in scored[:top_k]]


# =============================================================================
# DB search - import lazy để tránh circular import
# =============================================================================

def search_doctors(user_message, top_k=MAX_DOCTORS_IN_CONTEXT):
    """Search bác sĩ theo chuyên khoa/tên trong câu hỏi."""
    from accounts.models import User, UserRole

    msg_lower, msg_no_accent = _normalize(user_message)

    # Mapping keyword tiếng Việt -> tên chuyên khoa trong DB (bằng tiếng Anh)
    specialty_map = {
        'tim mạch': 'Heart Disease',
        'tim': 'Cardiology',
        'tiểu đường': 'Diabetes Disease',
        'ung thư vú': 'Breast Cancer',
        'nha khoa': 'Dentistry',
        'tai mũi họng': 'ENT Specialists',
        'tai mui hong': 'ENT Specialists',
        'tâm lý': 'Astrology',
        'thần kinh': 'Neuroanatomy',
        'than kinh': 'Neuroanatomy',
        'huyết học': 'Blood Screening',
        'mắt': 'Eye Care',
        'nhãn khoa': 'Eye Care',
        'vật lý trị liệu': 'Physical Therapy',
    }

    matched_specialties = []
    for vn, en in specialty_map.items():
        vn_lower, vn_no_accent = _normalize(vn)
        if vn_lower in msg_lower or vn_no_accent in msg_no_accent:
            matched_specialties.append(en)

    queryset = User.objects.filter(role=UserRole.DOCTOR).select_related('doctor_profile')
    if matched_specialties:
        # Match exact specialty trong DoctorProfile
        queryset = queryset.filter(doctor_profile__specialization__in=matched_specialties)

    return list(queryset[:top_k])


def search_available_slots(user_message, top_k=MAX_SLOTS_IN_CONTEXT):
    """Tìm slot khám trống trong vòng 7 ngày tới."""
    from appoinment.models import Appointment

    today = timezone.localdate()
    week_later = today + timedelta(days=7)

    queryset = Appointment.objects.filter(
        is_active=True,
        date__gte=today,
        date__lte=week_later,
    ).select_related('user').order_by('date', 'start_time')

    # Filter theo chuyên khoa nếu có trong câu hỏi
    msg_lower, msg_no_accent = _normalize(user_message)
    for vn, en in {
        'tim mạch': 'Heart Disease', 'tiểu đường': 'Diabetes Disease',
        'ung thư vú': 'Breast Cancer', 'nha khoa': 'Dentistry',
        'mắt': 'Eye Care',
    }.items():
        vn_lower, vn_no_accent = _normalize(vn)
        if vn_lower in msg_lower or vn_no_accent in msg_no_accent:
            queryset = queryset.filter(department=en)
            break

    return list(queryset[:top_k])


def get_user_medical_history(user, top_k=MAX_HISTORY_IN_CONTEXT):
    """Lấy lịch sử screening AI gần nhất của user."""
    from .models import MedicalHistory

    if not user or not user.is_authenticated:
        return []
    return list(
        MedicalHistory.objects.filter(user=user)
        .order_by('-created_at')[:top_k]
    )


def get_user_bookings(user, top_k=MAX_BOOKINGS_IN_CONTEXT):
    """Lấy booking active của user."""
    from appoinment.models import TakeAppointment

    if not user or not user.is_authenticated:
        return []
    today = timezone.localdate()
    return list(
        TakeAppointment.objects.filter(
            user=user, date__gte=today,
            status__in=TakeAppointment.ACTIVE_STATUSES,
        )
        .select_related('appointment')
        .order_by('date', 'time')[:top_k]
    )


# =============================================================================
# Format helpers - convert objects -> markdown text cho Gemini đọc
# =============================================================================

def _format_doctor(doctor):
    profile = getattr(doctor, 'doctor_profile', None)
    spec = (profile.specialization if profile else None) or 'Chưa cập nhật'
    qual = (profile.qualifications if profile else None) or ''
    line = f'- BS. {doctor.first_name} {doctor.last_name} ({doctor.email}), chuyên khoa {spec}'
    if qual:
        line += f', bằng cấp: {qual[:60]}'
    return line


def _format_slot(slot):
    doctor = slot.user
    return (
        f'- {slot.date.strftime("%d/%m/%Y")} '
        f'{slot.start_time.strftime("%H:%M")}-{slot.end_time.strftime("%H:%M")} '
        f'| BS. {doctor.first_name} {doctor.last_name} '
        f'| Khoa: {slot.department or "Chưa cập nhật"} '
        f'| Cơ sở: {slot.hospital_name or "—"}'
    )


def _format_history(item):
    return (
        f'- {item.created_at.strftime("%d/%m/%Y %H:%M")}: {item.disease_type} '
        f'→ {item.prediction_result}'
    )


def _format_booking(booking):
    appt = booking.appointment
    return (
        f'- {booking.date.strftime("%d/%m/%Y")} {booking.time.strftime("%H:%M")} '
        f'| BS. {appt.user.first_name} {appt.user.last_name} '
        f'| Trạng thái: {booking.get_status_display()}'
    )


# =============================================================================
# Main entry point - build RAG context
# =============================================================================

def build_rag_context(user, user_message):
    """Build context block để inject vào prompt Gemini.

    Trả về string đã format, có thể empty nếu không tìm thấy info nào.
    """
    intents = detect_intents(user_message)
    blocks = []

    # 1. FAQ - luôn search vì câu hỏi nào cũng có thể trùng FAQ
    faqs = search_faqs(user_message)
    if faqs:
        lines = ['## Câu hỏi thường gặp về hệ thống Medic:']
        for faq in faqs:
            lines.append(f'\n### {faq["question"]}')
            lines.append(faq['answer'])
        blocks.append('\n'.join(lines))

    # 2. Bác sĩ
    if 'doctor' in intents:
        doctors = search_doctors(user_message)
        if doctors:
            lines = ['## Bác sĩ trong hệ thống (phù hợp với câu hỏi):']
            lines.extend(_format_doctor(d) for d in doctors)
            blocks.append('\n'.join(lines))

    # 3. Lịch khám trống
    if 'appointment' in intents:
        slots = search_available_slots(user_message)
        if slots:
            lines = ['## Lịch khám trống trong 7 ngày tới:']
            lines.extend(_format_slot(s) for s in slots)
            blocks.append('\n'.join(lines))

    # 4. Lịch sử user (nếu hỏi về bản thân)
    if 'my_history' in intents or 'screening' in intents:
        history = get_user_medical_history(user)
        if history:
            lines = ['## Lịch sử sàng lọc AI của bạn (3 mục gần nhất):']
            lines.extend(_format_history(h) for h in history)
            blocks.append('\n'.join(lines))

    # 5. Booking của user
    if 'my_bookings' in intents:
        bookings = get_user_bookings(user)
        if bookings:
            lines = ['## Lịch khám bạn đã đặt (sắp tới):']
            lines.extend(_format_booking(b) for b in bookings)
            blocks.append('\n'.join(lines))

    # 6. Cảnh báo cấp cứu - nếu detect → AI sẽ ưu tiên trả lời 115
    if 'emergency' in intents:
        blocks.insert(0,
            '## ⚠️ CẢNH BÁO: Câu hỏi có dấu hiệu khẩn cấp y tế.\n'
            'Hãy ưu tiên hướng dẫn user GỌI 115 hoặc đến bệnh viện ngay '
            'thay vì giải thích dài dòng.'
        )

    if not blocks:
        return ''

    return '\n\n'.join(blocks)
