"""Custom template tags: load news + reviews trực tiếp trong template.

Cách dùng:
    {% load medic_tags %}
    {% latest_news 6 as news_items %}
    {% latest_reviews 4 as reviews %}
"""

from django import template
from django.utils.translation import gettext as _

from home.services_news import load_latest_news, load_latest_reviews


register = template.Library()


SPECIALTY_LABELS = {
    'Heart Disease': 'Bệnh tim mạch',
    'Diabetes Disease': 'Bệnh tiểu đường',
    'Breast Cancer': 'Ung thư vú',
    'Dentistry': 'Nha khoa',
    'Cardiology': 'Khoa Nội tim mạch',
    'ENT Specialists': 'Tai Mũi Họng',
    'Astrology': 'Tâm lý / Chiêm tinh học',
    'Neuroanatomy': 'Nội thần kinh',
    'Blood Screening': 'Xét nghiệm huyết học',
    'Eye Care': 'Nhãn khoa / Mắt',
    'Physical Therapy': 'Vật lý trị liệu',
}


@register.simple_tag
def latest_news(limit=6):
    return load_latest_news(limit=limit)


@register.simple_tag
def latest_reviews(limit=6):
    return load_latest_reviews(limit=limit)


@register.filter
def specialty_label(value):
    normalized = str(value or '').strip()
    if not normalized:
        return _('Đang cập nhật')
    return _(SPECIALTY_LABELS.get(normalized, normalized))
