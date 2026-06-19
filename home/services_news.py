"""Helper module load tin tức từ data/medic_news.json + reviews từ DB."""

import json
import logging
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.utils.translation import get_language

logger = logging.getLogger(__name__)

NEWS_PATH = Path(settings.BASE_DIR) / 'data' / 'medic_news.json'

NEWS_TRANSLATIONS_EN = {
    'ai-skin-cancer': {
        'title': 'Medic launches AI skin cancer screening',
        'excerpt': (
            'Medic now integrates a CNN model that classifies 7 groups of skin '
            'lesions based on the HAM10000 dataset, helping users check moles '
            'and suspicious lesions from home.'
        ),
        'category': 'Product news',
    },
    'abcde-melanoma': {
        'title': 'The ABCDE rule: detect melanoma early',
        'excerpt': (
            'Self-check moles using 5 criteria: Asymmetry, Border, Color, '
            'Diameter, and Evolution. Early detection can raise survival rates '
            'above 95%.'
        ),
        'category': 'Health education',
    },
    'diabetes-screening': {
        'title': '5 lab indicators to know for diabetes prevention',
        'excerpt': (
            'Fasting glucose, HbA1c, BMI, blood pressure, and insulin are key '
            'indicators that help Medic AI estimate your type 2 diabetes risk.'
        ),
        'category': 'Health education',
    },
    'telehealth': {
        'title': 'Medic upgrades realtime doctor chat',
        'excerpt': (
            'Patients can chat directly with doctors via WebSocket after booking, '
            'send questions, and receive quick guidance before the appointment.'
        ),
        'category': 'Product news',
    },
    'pneumonia-xray': {
        'title': 'AI analyzes X-ray images to detect pneumonia',
        'excerpt': (
            'Medic CNN reaches about 90% accuracy on the Chest X-Ray dataset, '
            'supporting pneumonia screening before seeing a doctor.'
        ),
        'category': 'Product news',
    },
    'heart-disease': {
        'title': 'Preventing cardiovascular disease in young adults',
        'excerpt': (
            'Cardiovascular disease is affecting younger people. Regular checkups, '
            'stress control, and a low-salt diet are key prevention habits.'
        ),
        'category': 'Health education',
    },
    'emr-secure-records': {
        'title': 'Electronic medical records support continuous health tracking',
        'excerpt': (
            'Medic stores visit history, vital signs, prescriptions, and AI screening '
            'results in one unified record so patients and doctors can follow treatment '
            'progress more clearly.'
        ),
        'category': 'Product news',
    },
    'smart-booking-guide': {
        'title': 'Smart appointment booking: choose the right specialty from the start',
        'excerpt': (
            'Based on symptoms and screening results, Medic suggests suitable specialties, '
            'shows available doctor schedules, and helps patients manage appointments more easily.'
        ),
        'category': 'User guide',
    },
}

FALLBACK_REVIEWS_VI = [
    {
        'patient': ('Minh', 'Nguyen'),
        'doctor': ('Hoang', 'Minh'),
        'rating': 5,
        'comment': '\u0110\u1eb7t l\u1ecbch nhanh, b\u00e1c s\u0129 t\u01b0 v\u1ea5n r\u00f5 r\u00e0ng v\u00e0 l\u1ecbch s\u1eed kh\u00e1m \u0111\u01b0\u1ee3c l\u01b0u l\u1ea1i r\u1ea5t ti\u1ec7n theo d\u00f5i.',
    },
    {
        'patient': ('Lan', 'Tran'),
        'doctor': ('Khoa', 'Hoang'),
        'rating': 5,
        'comment': 'Ph\u1ea7n s\u00e0ng l\u1ecdc AI gi\u00fap t\u00f4i bi\u1ebft n\u00ean ch\u1ecdn chuy\u00ean khoa n\u00e0o tr\u01b0\u1edbc khi \u0111\u1eb7t l\u1ecbch kh\u00e1m.',
    },
]

FALLBACK_REVIEWS_EN = [
    {
        'patient': ('Minh', 'Nguyen'),
        'doctor': ('Hoang', 'Minh'),
        'rating': 5,
        'comment': 'Booking was quick, the doctor explained everything clearly, and my visit history is easy to follow.',
    },
    {
        'patient': ('Lan', 'Tran'),
        'doctor': ('Khoa', 'Hoang'),
        'rating': 5,
        'comment': 'The AI screening helped me understand which specialty to choose before booking an appointment.',
    },
]


def _fallback_review_from_data(item):
    patient_first, patient_last = item['patient']
    doctor_first, doctor_last = item['doctor']
    return SimpleNamespace(
        rating=item['rating'],
        comment=item['comment'],
        patient=SimpleNamespace(first_name=patient_first, last_name=patient_last),
        doctor=SimpleNamespace(first_name=doctor_first, last_name=doctor_last),
    )


def _build_fallback_reviews(limit, existing_count=0):
    current_language = get_language() or ''
    source = FALLBACK_REVIEWS_EN if current_language.startswith('en') else FALLBACK_REVIEWS_VI
    needed = max(limit - existing_count, 0)
    if not source:
        return []
    return [_fallback_review_from_data(source[index % len(source)]) for index in range(needed)]


@lru_cache(maxsize=1)
def _load_all_news():
    if not NEWS_PATH.exists():
        logger.warning('News file not found: %s', NEWS_PATH)
        return []
    try:
        with open(NEWS_PATH, encoding='utf-8') as f:
            return json.load(f).get('news', [])
    except (OSError, json.JSONDecodeError):
        logger.exception('Failed to load %s', NEWS_PATH)
        return []


def load_latest_news(limit=6):
    current_language = get_language() or ''
    items = _load_all_news()[:limit]
    if not current_language.startswith('en'):
        return items
    localized_items = []
    for item in items:
        localized = dict(item)
        localized.update(NEWS_TRANSLATIONS_EN.get(item.get('id'), {}))
        localized_items.append(localized)
    return localized_items


def load_latest_reviews(limit=6):
    try:
        from appoinment.models import DoctorReview
        reviews = list(
            DoctorReview.objects
            .select_related('doctor', 'patient')
            .order_by('-rating', '-created_at')[:limit]
        )
        if len(reviews) < limit:
            reviews.extend(_build_fallback_reviews(limit, len(reviews)))
        return reviews
    except Exception:
        logger.exception('Failed to load latest reviews')
        return _build_fallback_reviews(limit)
