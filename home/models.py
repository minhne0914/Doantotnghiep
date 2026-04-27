from django.db import models

from accounts.models import User


class MedicalHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    disease_type = models.CharField(max_length=100)
    prediction_result = models.CharField(max_length=100)
    input_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.disease_type} - {self.created_at}"


class ChatMessage(models.Model):
    SENDER_USER = 'user'
    SENDER_BOT = 'bot'
    SENDER_CHOICES = (
        (SENDER_USER, 'Người dùng'),
        (SENDER_BOT, 'Medic AI'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} - {self.sender} - {self.created_at}"
