from django.urls import path
from .views import *

urlpatterns = [
    path('',index,name='home'),
    path('diabetes/',diabetes,name='diabetes'),
    path('breast/',breast,name='breast'),
    path('heart/',heart,name='heart'),
    path('kidney/',kidney,name='kidney'),
    path('pneumonia_detector/', pneumonia_detector, name='pneumonia_detector'),
    path('history/', history_view, name='history'),
    path('history/download/', export_health_history, name='export_health_history'),
    path('api/chat/', chat_api, name='chat_api'),
    path('api/chat/history/', chat_history_api, name='chat_history_api'),
    path('api/chat/clear/', clear_chat_api, name='clear_chat_api'),
]
