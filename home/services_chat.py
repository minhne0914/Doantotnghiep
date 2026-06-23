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
from django.db.models import Avg, Count, Exists, OuterRef, Q
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
MAX_CHAT_MESSAGES_IN_CONTEXT = 8


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
        'giờ khám', 'slot', 'khung giờ', 'hẹn khám', 'khám lúc nào',
    ],
    'my_history': [
        'lịch sử của tôi', 'kết quả của tôi', 'tôi đã khám', 'tôi đã làm',
        'tôi có', 'tôi bị', 'tôi đang', 'của tôi', 'của mình', 'mình bị',
        'mình đang', 'my history', 'my result', 'chỉ số của tôi',
    ],
    'my_bookings': [
        'lịch của tôi', 'lịch tôi đã đặt', 'lịch hẹn của tôi',
        'lịch hẹn', 'cuộc hẹn', 'đã đặt lịch', 'đặt lịch chưa',
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

INTENT_KEYWORDS['doctor'].extend([
    'bac si', 'chuyen khoa', 'da lieu', 'tim mach', 'tieu duong',
    'ung thu', 'mat', 'tai mui hong', 'than kinh', 'nha khoa',
])
INTENT_KEYWORDS['appointment'].extend([
    'lich', 'lich kham', 'lich hen', 'dat kham', 'dat hen', 'ca kham',
    'hom nay', 'ngay mai', 'tuan nay', 'gio kham', 'kham luc nao',
    'con lich', 'con trong', 'ranh', 'available',
])
INTENT_KEYWORDS['my_history'].extend([
    'lich su cua toi', 'ket qua cua toi', 'toi da kham', 'toi da lam',
    'cua toi', 'cua minh', 'tom tat suc khoe', 'ho so cua toi',
])
INTENT_KEYWORDS['my_bookings'].extend([
    'lich cua toi', 'lich hen cua toi', 'lich kham cua toi',
    'toi co lich', 'hom nay co lich', 'ngay mai co lich',
])
INTENT_KEYWORDS['emergency'].extend([
    'cap cuu', 'khan cap', 'kho tho', 'dau nguc', 'mat y thuc',
    'co giat', 'chay mau', 'dot quy', 'yeu liet', 'noi kho',
    'sot cao', 'dau dau du doi',
    'chest pain', 'shortness of breath', 'seizure', 'stroke',
    'unconscious', 'heavy bleeding', 'severe headache',
])
INTENT_KEYWORDS['screening'].extend([
    'sang loc', 'du doan', 'kiem tra', 'ket qua ai', 'da ai',
    'skin', 'da', 'x ray', 'xray',
])

for _generic_personal_phrase in (
    'tôi có', 'tôi bị', 'tôi đang', 'của tôi', 'của mình', 'mình bị', 'mình đang',
    'toi co', 'toi bi', 'toi dang', 'cua toi', 'cua minh', 'minh bi', 'minh dang',
):
    while _generic_personal_phrase in INTENT_KEYWORDS['my_history']:
        INTENT_KEYWORDS['my_history'].remove(_generic_personal_phrase)

# Keep screening/history retrieval explicit.  Short words such as ``da`` and
# ``tim`` are common inside unrelated Vietnamese phrases (for example
# "đau đầu" and "tìm bác sĩ") and must not route a symptom question to AI
# history.
for _ambiguous_keyword in ('AI', 'ai', 'tim', 'da'):
    while _ambiguous_keyword in INTENT_KEYWORDS['screening']:
        INTENT_KEYWORDS['screening'].remove(_ambiguous_keyword)

INTENT_KEYWORDS['screening'].extend([
    'ket qua sang loc', 'lich su sang loc', 'ket qua ai', 'sang loc da',
    'ung thu da', 'benh tim', 'benh than', 'benh tieu duong',
])

INTENT_KEYWORDS['symptom'] = [
    'đau đầu', 'dau dau', 'chóng mặt', 'chong mat', 'buồn nôn', 'buon non',
    'sốt', 'sot', 'bị ho', 'bi ho', 'ho nhiều', 'ho nhieu', 'đau bụng', 'dau bung', 'mệt', 'met moi',
    'đau lưng', 'dau lung', 'đau họng', 'dau hong', 'triệu chứng', 'trieu chung',
]

INTENT_KEYWORDS['appointment_change'] = [
    'đổi lịch', 'doi lich', 'dời lịch', 'doi gio', 'đổi giờ', 'đổi ngày', 'doi ngay',
    'hủy lịch', 'huy lich', 'hủy khám', 'huy kham', 'không khám nữa', 'khong kham nua',
]

INTENT_KEYWORDS['account'] = [
    'quên mật khẩu', 'quen mat khau', 'đặt lại mật khẩu', 'dat lai mat khau',
    'không đăng nhập', 'khong dang nhap', 'tài khoản', 'tai khoan',
    'hồ sơ', 'ho so', 'đổi thông tin', 'doi thong tin',
]


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


def _contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def _extract_booking_date_filter(user_message):
    """Return an exact date when the user asks about today/tomorrow bookings."""
    _, msg_no_accent = _normalize(user_message)
    today = timezone.localdate()
    if _contains_any(msg_no_accent, ('hom nay', 'toi nay', 'today')):
        return today
    if _contains_any(msg_no_accent, ('ngay mai', 'tomorrow')):
        return today + timedelta(days=1)
    return None


def _looks_like_user_booking_question(user_message):
    """Detect questions about the current user's own appointment calendar."""
    _, msg_no_accent = _normalize(user_message)
    booking_terms = (
        'lich kham', 'lich hen', 'cuoc hen', 'dat lich', 'lich cua',
        'appointment', 'booking',
    )
    personal_terms = (
        'toi', 'minh', 'cua toi', 'cua minh', 'my ', 'i have', 'do i',
    )
    exact_date_terms = ('hom nay', 'toi nay', 'ngay mai', 'today', 'tomorrow')
    question_terms = (' co ', 'khong', 'chua', 'da dat')
    available_slot_terms = (
        'bac si nao', 'doctor', 'slot', 'con trong', 'trong tuan',
        'ranh', 'free', 'available',
    )

    if not _contains_any(msg_no_accent, booking_terms):
        return False
    if _contains_any(msg_no_accent, personal_terms):
        return True
    if (
        _contains_any(msg_no_accent, exact_date_terms)
        and _contains_any(f' {msg_no_accent} ', question_terms)
    ):
        return True
    if _contains_any(msg_no_accent, available_slot_terms):
        return False
    return False


def detect_intents(user_message):
    """Trả về set intent đang active dựa trên keyword."""
    msg_lower, msg_no_accent = _normalize(user_message)
    intents = set()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            kw_lower = kw.lower()
            _, kw_no_accent = _normalize(kw)
            # Very short terms need word boundaries to avoid matching inside a
            # normal Vietnamese word (e.g. ``da`` in ``dau``).
            if len(kw_no_accent) <= 3:
                matched = bool(re.search(
                    rf'(?<![a-z0-9]){re.escape(kw_no_accent)}(?![a-z0-9])',
                    msg_no_accent,
                ))
            else:
                matched = kw_lower in msg_lower or kw_no_accent in msg_no_accent
            if matched:
                intents.add(intent)
                break
    if _looks_like_user_booking_question(user_message):
        intents.add('my_bookings')
    return intents


def detect_primary_intent(user_message):
    """Choose exactly one response path when a message matches several topics.

    The priority prevents incidental words from pulling a patient into an
    unrelated database query.  Medical safety and explicit actions always win.
    """
    intents = detect_intents(user_message)
    _, message = _normalize(user_message)

    # Keep this resolver deliberately linear so one message has one route.
    if 'emergency' in intents:
        return 'emergency'
    if 'appointment_change' in intents:
        return 'appointment_change'
    if 'my_bookings' in intents:
        return 'my_bookings'
    if 'symptom' in intents:
        return 'symptom'
    if 'account' in intents:
        return 'account'
    if 'appointment' in intents:
        return 'appointment'
    if 'doctor' in intents:
        return 'doctor'
    if 'my_history' in intents or 'screening' in intents:
        return 'history'
    if _contains_any(message, ('ket qua ai', 'ket qua sang loc', 'lich su sang loc')):
        return 'history'
    return 'general'
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

    queryset = (
        User.objects.filter(role=UserRole.DOCTOR)
        .select_related('doctor_profile')
        .annotate(
            avg_rating=Avg('doctor_reviews__rating'),
            review_count=Count('doctor_reviews'),
        )
    )
    if matched_specialties:
        # Match exact specialty trong DoctorProfile
        queryset = queryset.filter(doctor_profile__specialization__in=matched_specialties)

    return list(queryset[:top_k])


def search_available_slots(user_message, top_k=MAX_SLOTS_IN_CONTEXT):
    """Tìm slot khám trống trong vòng 7 ngày tới."""
    from appoinment.models import Appointment, TakeAppointment

    today = timezone.localdate()
    week_later = today + timedelta(days=7)
    active_bookings = TakeAppointment.objects.filter(
        appointment=OuterRef('pk'),
        date=OuterRef('date'),
        time=OuterRef('start_time'),
        status__in=TakeAppointment.ACTIVE_STATUSES,
    )

    queryset = (
        Appointment.objects.filter(
            is_active=True,
            date__gte=today,
            date__lte=week_later,
        )
        .select_related('user')
        .annotate(is_booked=Exists(active_bookings))
        .filter(is_booked=False)
        .order_by('date', 'start_time')
    )

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


def get_user_bookings(user, top_k=MAX_BOOKINGS_IN_CONTEXT, target_date=None):
    """Lấy booking active của user."""
    from appoinment.models import TakeAppointment

    if not user or not user.is_authenticated:
        return []
    today = timezone.localdate()
    filters = {
        'user': user,
        'status__in': TakeAppointment.ACTIVE_STATUSES,
    }
    if target_date:
        filters['date'] = target_date
    else:
        filters['date__gte'] = today
    queryset = (
        TakeAppointment.objects.filter(**filters)
        .select_related('appointment', 'appointment__user')
        .order_by('date', 'time')
    )
    return list(queryset[:top_k])


def get_doctor_bookings(user, top_k=8, target_date=None):
    """Return active bookings for the logged-in doctor."""
    from appoinment.models import TakeAppointment

    if not user or not user.is_authenticated or getattr(user, 'role', '') != 'doctor':
        return []
    today = timezone.localdate()
    filters = {
        'appointment__user': user,
        'status__in': TakeAppointment.ACTIVE_STATUSES,
    }
    if target_date:
        filters['date'] = target_date
    else:
        filters['date__gte'] = today
    return list(
        TakeAppointment.objects.filter(**filters)
        .select_related('appointment', 'user')
        .order_by('date', 'time')[:top_k]
    )


def get_recent_chat_messages(user, exclude_message_id=None, top_k=MAX_CHAT_MESSAGES_IN_CONTEXT):
    """Lấy vài tin nhắn gần nhất để Gemini hiểu câu hỏi nối tiếp."""
    from .models import ChatMessage

    if not user or not user.is_authenticated:
        return []

    queryset = ChatMessage.objects.filter(user=user)
    if exclude_message_id:
        queryset = queryset.exclude(pk=exclude_message_id)

    return list(queryset.order_by('-created_at')[:top_k])[::-1]


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
    avg_rating = getattr(doctor, 'avg_rating', None)
    review_count = getattr(doctor, 'review_count', 0) or 0
    if avg_rating:
        line += f', đánh giá TB: {avg_rating:.1f}/5 ({review_count} lượt)'
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
    disease = _HISTORY_DISEASE_LABELS.get(item.disease_type, item.disease_type)
    return (
        f'- {item.created_at.strftime("%d/%m/%Y %H:%M")}: {disease}. '
        f'{_friendly_history_result(item)}'
    )


_HISTORY_DISEASE_LABELS = {
    'Diabetes': 'Sàng lọc nguy cơ tiểu đường',
    'Diabetes Disease': 'Sàng lọc nguy cơ tiểu đường',
    'Heart Disease': 'Sàng lọc nguy cơ tim mạch',
    'Breast Cancer': 'Sàng lọc nguy cơ ung thư vú',
    'Kidney Disease': 'Sàng lọc nguy cơ bệnh thận',
    'Pneumonia': 'Sàng lọc nguy cơ viêm phổi',
    'Skin Cancer': 'Sàng lọc tổn thương da',
}


def _friendly_history_result(item):
    """Hide model labels such as ``have`` and ``Positive`` from patients."""
    raw_result = (item.prediction_result or '').strip()
    normalized = raw_result.lower()
    if item.disease_type == 'Skin Cancer':
        return 'Kết quả đã được lưu; xem chi tiết để theo dõi tổn thương da.'
    if normalized in {'positive', 'have', 'elevated', 'high risk'}:
        return 'Có chỉ số cần theo dõi thêm cùng bác sĩ.'
    if normalized in {'negative', "don't have", 'lower', 'low risk'}:
        return 'Chưa thấy tín hiệu nguy cơ nổi bật từ lần sàng lọc này.'
    return raw_result or 'Kết quả sàng lọc đã được lưu.'


def _format_history_card(item):
    disease = _HISTORY_DISEASE_LABELS.get(item.disease_type, item.disease_type)
    return (
        f"- {item.created_at.strftime('%d/%m/%Y')}: {disease}. "
        f"{_friendly_history_result(item)}"
    )


def _format_booking(booking):
    appt = booking.appointment
    return (
        f'- {booking.date.strftime("%d/%m/%Y")} {booking.time.strftime("%H:%M")} '
        f'| BS. {appt.user.first_name} {appt.user.last_name} '
        f'| Trạng thái: {booking.get_status_display()}'
    )


def _format_chat_message(message):
    sender = 'Người dùng' if message.sender == 'user' else 'Medic AI'
    text = re.sub(r'\s+', ' ', message.message or '').strip()
    if len(text) > 360:
        text = text[:357] + '...'
    return f'- {sender} ({message.created_at.strftime("%d/%m/%Y %H:%M")}): {text}'


# =============================================================================
# Main entry point - build RAG context
# =============================================================================

def build_rag_context(user, user_message, current_message_id=None):
    """Build context block để inject vào prompt Gemini.

    Trả về string đã format, có thể empty nếu không tìm thấy info nào.
    """
    intents = detect_intents(user_message)
    primary_intent = detect_primary_intent(user_message)
    is_personal_booking_question = _looks_like_user_booking_question(user_message)
    booking_date_filter = _extract_booking_date_filter(user_message)
    blocks = []

    # 0. Bộ nhớ hội thoại gần đây - giúp trả lời các câu hỏi nối tiếp như
    # "vậy tôi nên làm gì tiếp?" mà không bắt user lặp lại toàn bộ ngữ cảnh.
    recent_messages = get_recent_chat_messages(user, exclude_message_id=current_message_id)
    if recent_messages:
        lines = ['## Ngữ cảnh hội thoại gần đây:']
        lines.extend(_format_chat_message(m) for m in recent_messages)
        blocks.append('\n'.join(lines))

    # 1. FAQ - luôn search vì câu hỏi nào cũng có thể trùng FAQ
    faqs = [] if primary_intent in {'symptom', 'emergency'} else search_faqs(user_message)
    if faqs:
        lines = ['## Câu hỏi thường gặp về hệ thống Medic:']
        for faq in faqs:
            lines.append(f'\n### {faq["question"]}')
            lines.append(faq['answer'])
        blocks.append('\n'.join(lines))

    # 2. Bác sĩ
    if primary_intent == 'doctor':
        doctors = search_doctors(user_message)
        lines = ['## Bác sĩ trong hệ thống (phù hợp với câu hỏi):']
        if doctors:
            lines.extend(_format_doctor(d) for d in doctors)
        else:
            lines.append('- Chưa tìm thấy bác sĩ phù hợp trong dữ liệu hiện có.')
        blocks.append('\n'.join(lines))

    # 3. Lịch khám trống
    if primary_intent == 'appointment' and not is_personal_booking_question:
        slots = search_available_slots(user_message)
        lines = ['## Lịch khám trống trong 7 ngày tới:']
        if slots:
            lines.extend(_format_slot(s) for s in slots)
        else:
            lines.append('- Chưa tìm thấy slot trống phù hợp trong 7 ngày tới.')
        blocks.append('\n'.join(lines))

    # 4. Lịch sử user (nếu hỏi về bản thân)
    if primary_intent == 'history':
        history = get_user_medical_history(user)
        lines = ['## Lịch sử sàng lọc AI của bạn (3 mục gần nhất):']
        if history:
            lines.extend(_format_history(h) for h in history)
        else:
            lines.append('- Bạn chưa có lịch sử sàng lọc AI trong hệ thống.')
        blocks.append('\n'.join(lines))

    # 5. Booking của user
    if primary_intent == 'my_bookings':
        bookings = get_user_bookings(user, target_date=booking_date_filter)
        lines = ['## Lịch khám bạn đã đặt (sắp tới):']
        if bookings:
            lines.extend(_format_booking(b) for b in bookings)
        else:
            lines.append('- Bạn chưa có lịch khám sắp tới đang hoạt động.')
        blocks.append('\n'.join(lines))

    # 6. Cảnh báo cấp cứu - nếu detect → AI sẽ ưu tiên trả lời 115
    if primary_intent == 'emergency':
        blocks.insert(0,
            '## ⚠️ CẢNH BÁO: Câu hỏi có dấu hiệu khẩn cấp y tế.\n'
            'Hãy ưu tiên hướng dẫn user GỌI 115 hoặc đến bệnh viện ngay '
            'thay vì giải thích dài dòng.'
        )

    if not blocks:
        return ''

    return '\n\n'.join(blocks)


def _action(label, url, tone='primary'):
    return {'label': label, 'url': url, 'tone': tone}


def _symptom_specialty(user_message):
    """Return a conservative specialty suggestion for non-emergency symptoms."""
    _, message = _normalize(user_message)
    mappings = (
        (('dau dau', 'chong mat', 'dau lung', 'te bi', 'yeu tay'), 'thần kinh', 'Nội thần kinh'),
        (('dau hong', 'nghet mui', 'dau tai'), 'tai mũi họng', 'Tai Mũi Họng'),
        (('dau rang', 'dau loi', 'sung loi'), 'nha khoa', 'Nha khoa'),
        (('mat do', 'mo mat', 'dau mat'), 'mắt', 'Nhãn khoa'),
    )
    for keywords, search_term, label in mappings:
        if _contains_any(message, keywords):
            return search_term, label
    return None, None


def get_contextual_suggestions(source):
    """Short follow-up prompts rendered as chat buttons after each answer."""
    suggestions = {
        'local_symptom': [
            'Triệu chứng bắt đầu từ khi nào?',
            'Tôi muốn tìm bác sĩ phù hợp',
        ],
        'local_bookings': [
            'Tôi muốn đổi lịch khám',
            'Tôi cần chuẩn bị gì trước buổi khám?',
        ],
        'local_appointment_change': [
            'Lịch của tôi',
            'Bác sĩ nào rảnh hôm nay?',
        ],
        'local_history': [
            'Giải thích kết quả sàng lọc gần nhất',
            'Tìm bác sĩ phù hợp với kết quả này',
        ],
        'local_account': [
            'Tôi không nhận được email đặt lại mật khẩu',
            'Tôi muốn cập nhật hồ sơ',
        ],
    }
    return suggestions.get(source, [
        'Hôm nay tôi có lịch khám không?',
        'Tìm bác sĩ phù hợp',
        'Cho tôi xem kết quả sàng lọc AI',
    ])


def _format_doctor_card(doctor):
    profile = getattr(doctor, 'doctor_profile', None)
    specialty = (profile.specialization if profile else None) or 'chưa cập nhật'
    rating = getattr(doctor, 'avg_rating', None)
    review_count = getattr(doctor, 'review_count', 0) or 0
    rating_text = f' - đánh giá {rating:.1f}/5 ({review_count} lượt)' if rating else ''
    return (
        f"BS. {doctor.first_name} {doctor.last_name} - {specialty}"
        f"{rating_text}."
    )


def _format_booking_card(booking):
    appointment = booking.appointment
    return (
        f"{booking.date.strftime('%d/%m/%Y')} lúc {booking.time.strftime('%H:%M')} "
        f"với BS. {appointment.user.first_name} {appointment.user.last_name} "
        f"({appointment.department}) - trạng thái: {booking.get_status_display()}."
    )


def _format_doctor_booking_card(booking):
    appointment = booking.appointment
    note = f" - ghi chú: {booking.message}" if booking.message else ""
    return (
        f"{booking.date.strftime('%d/%m/%Y')} lúc {booking.time.strftime('%H:%M')} - "
        f"{booking.full_name} ({booking.phone_number}) "
        f"khám {appointment.department}; trạng thái: {booking.get_status_display()}{note}."
    )


def _format_slot_card(slot):
    return (
        f"{slot.date.strftime('%d/%m/%Y')} {slot.start_time.strftime('%H:%M')}-"
        f"{slot.end_time.strftime('%H:%M')} với BS. {slot.user.first_name} "
        f"{slot.user.last_name} ({slot.department}) tại {slot.hospital_name}."
    )


def build_local_chat_response(user, user_message):
    """Return a deterministic DB-backed chatbot response.

    This lets Medic AI keep working during demos even when the external AI key is
    missing or the provider is temporarily unavailable.
    """
    intents = detect_intents(user_message)
    primary_intent = detect_primary_intent(user_message)
    is_personal_booking_question = _looks_like_user_booking_question(user_message)
    booking_date_filter = _extract_booking_date_filter(user_message)
    today = timezone.localdate()
    actions = []

    if getattr(user, 'role', '') == 'doctor' and (
        primary_intent in {'my_bookings', 'appointment'}
    ):
        target_date = booking_date_filter or today
        bookings = get_doctor_bookings(user, top_k=10, target_date=target_date)
        actions.extend([
            _action('Mở dashboard bác sĩ', '/account/doctor/dashboard/', 'primary'),
            _action('Mở lịch khám', '/appoinment/doctor/appointment/', 'secondary'),
        ])
        if bookings:
            if target_date == today:
                lines = ['Hôm nay bác sĩ có các lịch khám đang hoạt động:']
            else:
                lines = [f'Các lịch khám ngày {target_date.strftime("%d/%m/%Y")}:']
            lines.extend(f'- {_format_doctor_booking_card(booking)}' for booking in bookings)
            first_booking = bookings[0]
            actions.insert(
                0,
                _action('Mở chat bệnh nhân đầu tiên', f'/appoinment/doctor/inbox/{first_booking.id}/', 'success'),
            )
            return {
                'reply': '\n'.join(lines),
                'actions': actions,
                'source': 'local_doctor_schedule',
            }
        empty = (
            'Hôm nay bác sĩ chưa có lịch khám đang hoạt động.'
            if target_date == today
            else f'Bác sĩ chưa có lịch khám đang hoạt động vào ngày {target_date.strftime("%d/%m/%Y")}.'
        )
        return {
            'reply': empty,
            'actions': actions,
            'source': 'local_doctor_schedule',
        }

    if primary_intent == 'emergency':
        return {
            'reply': (
                'Tôi thấy nội dung của bạn có dấu hiệu khẩn cấp. Nếu bạn đang khó thở, '
                'đau ngực dữ dội, ngất, co giật, chảy máu nhiều hoặc có dấu hiệu đột quỵ, '
                'hãy gọi 115 hoặc đến cơ sở y tế gần nhất ngay. Medic AI chỉ hỗ trợ tham khảo, '
                'không thay thế cấp cứu.'
            ),
            'actions': [
                _action('Xem danh sách bác sĩ', '/appoinment/doctor/', 'danger'),
            ],
            'source': 'local_emergency',
        }

    if primary_intent == 'symptom':
        specialty_query, specialty_label = _symptom_specialty(user_message)
        suggested_doctors = search_doctors(specialty_query, top_k=2) if specialty_query else []
        specialty_note = ''
        symptom_actions = [
            _action('Tìm bác sĩ phù hợp', '/appoinment/doctor/', 'primary'),
            _action('Đặt lịch khám', '/appoinment/doctor/', 'secondary'),
        ]
        if specialty_label:
            specialty_note = f' Với triệu chứng này, bạn có thể ưu tiên khám chuyên khoa {specialty_label}.'
        if suggested_doctors:
            doctor = suggested_doctors[0]
            symptom_actions.insert(
                0,
                _action(
                    f'Xem BS. {doctor.first_name} {doctor.last_name}',
                    f'/appoinment/doctor/{doctor.id}/profile/',
                    'success',
                ),
            )
        return {
            'reply': (
                'Tôi hiểu bạn đang khó chịu. Với đau đầu hoặc triệu chứng nhẹ mới xuất hiện, '
                'bạn có thể nghỉ ở nơi yên tĩnh, uống đủ nước và theo dõi diễn tiến. '
                'Tôi không thể xác định nguyên nhân chỉ qua chat. Nếu đau đầu xuất hiện đột ngột và dữ dội, '
                'kèm yếu liệt, nói khó, lú lẫn, sốt cao/cứng gáy, nhìn mờ, ngất hoặc sau chấn thương đầu, '
                'hãy gọi 115 hoặc đến cơ sở y tế ngay. Nếu triệu chứng kéo dài, tái diễn hoặc khiến bạn lo lắng, '
                'bạn nên đặt lịch khám để được đánh giá trực tiếp.'
                f'{specialty_note} Để tư vấn sát hơn, bạn có thể cho biết triệu chứng bắt đầu từ khi nào, '
                'mức độ đau từ 0-10 và có sốt, nôn, nhìn mờ hoặc tê yếu không.'
            ),
            'actions': symptom_actions,
            'source': 'local_symptom',
        }

    if primary_intent == 'appointment_change':
        return {
            'reply': (
                'Bạn có thể đổi hoặc hủy lịch trong mục Lịch hẹn của tôi. Chọn lịch đang ở trạng thái '
                'chờ xác nhận hoặc đã xác nhận, sau đó bấm Đổi lịch hoặc Hủy lịch. Khi đổi sang giờ mới, '
                'hệ thống sẽ kiểm tra khung giờ trống và gửi yêu cầu để bác sĩ xác nhận lại.'
            ),
            'actions': [
                _action('Mở lịch hẹn của tôi', '/appoinment/patient/my-appointments/', 'primary'),
                _action('Tìm lịch trống', '/appoinment/doctor/', 'secondary'),
            ],
            'source': 'local_appointment_change',
        }

    if primary_intent == 'account':
        _, normalized_message = _normalize(user_message)
        if _contains_any(normalized_message, ('quen mat khau', 'dat lai mat khau', 'khong dang nhap')):
            return {
                'reply': (
                    'Bạn có thể đặt lại mật khẩu bằng email đã đăng ký. Bấm Quên mật khẩu, nhập email, '
                    'rồi mở email để dùng liên kết đặt lại mật khẩu.'
                ),
                'actions': [_action('Đặt lại mật khẩu', '/account/password_reset/', 'primary')],
                'source': 'local_account',
            }
        return {
            'reply': 'Bạn có thể cập nhật thông tin cá nhân trong Hồ sơ. Thông tin chuyên môn của bác sĩ do quản trị viên quản lý để bảo đảm chính xác.',
            'actions': [_action('Mở trang chủ', '/', 'secondary')],
            'source': 'local_account',
        }

    if primary_intent == 'my_bookings':
        bookings = get_user_bookings(user, top_k=5, target_date=booking_date_filter)
        actions.append(_action('Mở lịch hẹn của tôi', '/appoinment/patient/my-appointments/', 'primary'))
        if bookings:
            if booking_date_filter == today:
                lines = ['Hôm nay bạn có lịch khám:']
            elif booking_date_filter:
                lines = [f'Ngày {booking_date_filter.strftime("%d/%m/%Y")} bạn có lịch khám:']
            else:
                lines = ['Đây là các lịch hẹn sắp tới của bạn:']
            lines.extend(f'- {_format_booking_card(booking)}' for booking in bookings)
            return {
                'reply': '\n'.join(lines),
                'actions': actions,
                'source': 'local_bookings',
            }
        if booking_date_filter == today:
            empty_reply = (
                'Hôm nay bạn không có lịch khám nào đang hoạt động. '
                'Nếu cần khám, bạn có thể xem danh sách bác sĩ và đặt lịch mới.'
            )
        elif booking_date_filter:
            empty_reply = (
                f'Ngày {booking_date_filter.strftime("%d/%m/%Y")} bạn không có lịch khám nào đang hoạt động. '
                'Nếu cần khám, bạn có thể xem danh sách bác sĩ và đặt lịch mới.'
            )
        else:
            empty_reply = (
                'Hiện tại bạn chưa có lịch hẹn sắp tới đang hoạt động. '
                'Bạn có thể vào danh sách bác sĩ để chọn chuyên khoa và đặt lịch mới.'
            )
        return {
            'reply': empty_reply,
            'actions': [
                _action('Tìm bác sĩ', '/appoinment/doctor/', 'primary'),
                *actions,
            ],
            'source': 'local_bookings',
        }

    if primary_intent == 'appointment' and not is_personal_booking_question:
        slots = search_available_slots(user_message, top_k=5)
        if slots:
            lines = ['Tôi tìm thấy một số khung khám còn trống trong 7 ngày tới:']
            lines.extend(f'- {_format_slot_card(slot)}' for slot in slots)
            actions.extend([
                _action('Xem tất cả bác sĩ', '/appoinment/doctor/', 'primary'),
                _action('Lịch hẹn của tôi', '/appoinment/patient/my-appointments/', 'secondary'),
            ])
            first_slot = slots[0]
            actions.insert(0, _action('Đặt lịch gợi ý đầu tiên', f'/appoinment/patient-take-appointment/{first_slot.id}/', 'success'))
            return {
                'reply': '\n'.join(lines),
                'actions': actions,
                'source': 'local_slots',
            }
        return {
            'reply': (
                'Tôi chưa tìm thấy khung khám trống phù hợp trong 7 ngày tới. '
                'Bạn thử đổi ngày, đổi chuyên khoa hoặc xem toàn bộ danh sách bác sĩ.'
            ),
            'actions': [_action('Xem đội ngũ bác sĩ', '/appoinment/doctor/', 'primary')],
            'source': 'local_slots',
        }

    if primary_intent == 'doctor':
        doctors = search_doctors(user_message, top_k=5)
        if doctors:
            lines = ['Tôi tìm thấy các bác sĩ phù hợp trong hệ thống:']
            lines.extend(f'- {_format_doctor_card(doctor)}' for doctor in doctors)
            actions.extend([
                _action('Xem danh sách bác sĩ', '/appoinment/doctor/', 'primary'),
                _action('Xem bác sĩ đầu tiên', f'/appoinment/doctor/{doctors[0].id}/profile/', 'success'),
            ])
            return {
                'reply': '\n'.join(lines),
                'actions': actions,
                'source': 'local_doctors',
            }
        return {
            'reply': 'Tôi chưa tìm thấy bác sĩ phù hợp với câu hỏi này trong database.',
            'actions': [_action('Xem tất cả bác sĩ', '/appoinment/doctor/', 'primary')],
            'source': 'local_doctors',
        }

    if primary_intent == 'history':
        history = get_user_medical_history(user, top_k=5)
        actions.append(_action('Mở lịch sử AI', '/history/', 'primary'))
        if history:
            lines = ['Đây là các kết quả sàng lọc AI gần đây của bạn:']
            lines.extend(_format_history_card(item) for item in history)
            lines.append('Lưu ý: kết quả AI chỉ có tính tham khảo, bạn nên gặp bác sĩ để được kết luận chính xác.')
            return {
                'reply': '\n'.join(lines),
                'actions': actions,
                'source': 'local_history',
            }
        return {
            'reply': (
                'Bạn chưa có lịch sử sàng lọc AI trong hệ thống. '
                'Bạn có thể thử các công cụ sàng lọc trên website, sau đó Medic AI sẽ đọc lại kết quả cho bạn.'
            ),
            'actions': [
                _action('Sàng lọc da bằng AI', '/skin_cancer/', 'primary'),
                _action('Lịch sử AI', '/history/', 'secondary'),
            ],
            'source': 'local_history',
        }

    return {
        'reply': (
            'Tôi là Medic AI. Bạn có thể hỏi tôi về bác sĩ, chuyên khoa, lịch khám còn trống, '
            'lịch hẹn của bạn hoặc kết quả sàng lọc AI. Nếu bạn mô tả triệu chứng, tôi sẽ chỉ '
            'đưa ra thông tin tham khảo và khuyên bạn gặp bác sĩ khi cần.'
        ),
        'actions': [
            _action('Tìm bác sĩ', '/appoinment/doctor/', 'primary'),
            _action('Lịch hẹn của tôi', '/appoinment/patient/my-appointments/', 'secondary'),
            _action('Lịch sử AI', '/history/', 'secondary'),
        ],
        'source': 'local_general',
    }
