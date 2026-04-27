from django.contrib import admin
from .models import MedicalHistory, ChatMessage

@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'disease_type', 'prediction_result', 'created_at')
    list_filter = ('disease_type', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'disease_type', 'prediction_result')
    readonly_fields = ('created_at',)

    def user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name} ({obj.user.email})"
    user_name.short_description = 'Bệnh nhân'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'sender', 'short_message', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('user__first_name', 'user__email', 'message')
    readonly_fields = ('created_at',)

    def user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_name.short_description = 'Người dùng'
    
    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Nội dung chat'
