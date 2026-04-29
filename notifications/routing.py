from django.urls import path

from .consumers import NotificationConsumer


from appoinment.consumers import DirectChatConsumer

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi()),
    path('ws/chat/<int:booking_id>/', DirectChatConsumer.as_asgi()),
]
