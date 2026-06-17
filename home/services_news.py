"""Helper module load tin tức từ data/medic_news.json + reviews từ DB."""

import json
import logging
from functools import lru_cache
from pathlib import Path

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
}


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
        return list(
            DoctorReview.objects
            .select_related('doctor', 'patient')
            .order_by('-rating', '-created_at')[:limit]
        )
    except Exception:
        logger.exception('Failed to load latest reviews')
        return []
