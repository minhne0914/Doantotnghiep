"""Admin cho home app: lịch sử screening ML, tin nhắn AI chat."""

import json

from django.contrib import admin
from django.utils.html import format_html

from .models import MedicalHistory, ChatMessage


@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_label', 'disease_badge', 'prediction_result',
        'short_input', 'created_at',
    )
    list_filter = ('disease_type', 'created_at')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'disease_type', 'prediction_result',
    )
    list_select_related = ('user',)
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'pretty_input_data')

    fieldsets = (
        ('Bệnh nhân', {'fields': ('user',)}),
        ('Kết quả sàng lọc', {'fields': ('disease_type', 'prediction_result')}),
        ('Dữ liệu đầu vào', {'fields': ('pretty_input_data', 'input_data'), 'classes': ('collapse',)}),
        ('Audit', {'fields': ('created_at',)}),
    )

    def user_label(self, obj):
        full = f'{obj.user.first_name} {obj.user.last_name}'.strip()
        return full or obj.user.email
    user_label.short_description = 'Bệnh nhân'

    def disease_badge(self, obj):
        # Color theo mức độ nguy hiểm
        risky = {'Pneumonia', 'Skin Cancer', 'Heart Disease', 'Breast Cancer'}
        moderate = {'Diabetes', 'Kidney Disease'}
        if obj.disease_type in risky:
            color = '#dc2626'
        elif obj.disease_type in moderate:
            color = '#f59e0b'
        else:
            color = '#3b82f6'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px">{}</span>',
            color, obj.disease_type or '—',
        )
    disease_badge.short_description = 'Loại bệnh'

    def short_input(self, obj):
        if not obj.input_data:
            return '—'
        try:
            text = json.dumps(obj.input_data, ensure_ascii=False)
        except Exception:
            text = str(obj.input_data)
        return (text[:60] + '...') if len(text) > 60 else text
    short_input.short_description = 'Chỉ số'

    def pretty_input_data(self, obj):
        if not obj.input_data:
            return '—'
        try:
            text = json.dumps(obj.input_data, indent=2, ensure_ascii=False)
        except Exception:
            text = str(obj.input_data)
        return format_html(
            '<pre style="background:#f3f4f6;padding:10px;border-radius:6px;'
            'font-size:12px;max-height:300px;overflow:auto">{}</pre>',
            text,
        )
    pretty_input_data.short_description = 'Chỉ số (đẹp)'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_label', 'sender_badge', 'short_message', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'message')
    list_select_related = ('user',)
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

    def user_label(self, obj):
        full = f'{obj.user.first_name} {obj.user.last_name}'.strip()
        return full or obj.user.email
    user_label.short_description = 'Người dùng'

    def sender_badge(self, obj):
        if obj.sender == ChatMessage.SENDER_USER:
            return format_html(
                '<span style="background:#3b82f6;color:#fff;padding:2px 8px;'
                'border-radius:6px;font-size:11px">👤 User</span>'
            )
        return format_html(
            '<span style="background:#8b5cf6;color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px">🤖 AI</span>'
        )
    sender_badge.short_description = 'Người gửi'

    def short_message(self, obj):
        msg = obj.message or ''
        return (msg[:80] + '...') if len(msg) > 80 else msg
    short_message.short_description = 'Nội dung'

    def has_add_permission(self, request):
        # Chat message tạo qua /api/chat/, không thêm thủ công
        return False
