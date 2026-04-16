import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import TakeAppointment, DirectMessage
from accounts.models import User

class DirectChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if self.user is None or self.user.is_anonymous:
            await self.close()
            return

        self.booking_id = self.scope['url_route']['kwargs']['booking_id']
        
        # Verify access
        self.booking, doctor_id, patient_id = await self._get_booking_details()
        if not self.booking:
            await self.close()
            return
            
        self.room_group_name = f'chat_doc{doctor_id}_pat{patient_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive_json(self, content, **kwargs):
        message = content.get('message')
        if not message:
            return

        # Save to DB
        new_msg = await self._save_message(message)
        
        # Push realtime notification to the other user
        await self._push_chat_notification(message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': new_msg.id,
                'message': new_msg.content,
                'sender_id': self.user.id,
                'sender_name': self.user.first_name + " " + self.user.last_name,
                'timestamp': new_msg.created_at.strftime("%H:%M %d/%m/%Y")
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send_json({
            'id': event['id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp']
        })

    @database_sync_to_async
    def _get_booking_details(self):
        try:
            booking = TakeAppointment.objects.select_related('appointment', 'appointment__user').get(id=self.booking_id)
            # Ensure user is either patient or doctor for this booking
            if self.user.role == 'patient' and booking.user_id == self.user.id:
                return booking, booking.appointment.user_id, booking.user_id
            if self.user.role == 'doctor' and booking.appointment.user_id == self.user.id:
                return booking, booking.appointment.user_id, booking.user_id
            return None, None, None
        except TakeAppointment.DoesNotExist:
            return None, None, None

    @database_sync_to_async
    def _save_message(self, content):
        return DirectMessage.objects.create(
            booking_id=self.booking_id,
            sender_id=self.user.id,
            content=content
        )

    @database_sync_to_async
    def _push_chat_notification(self, msg_content):
        from notifications.realtime import push_realtime_notification
        booking = TakeAppointment.objects.select_related('user', 'appointment__user').get(id=self.booking_id)
        other_user = booking.user if self.user.role == 'doctor' else booking.appointment.user
        sender_name = ("BS. " + self.user.last_name) if self.user.role == 'doctor' else booking.full_name
        
        if other_user.role == 'doctor':
             link = f"/doctor/inbox/{booking.id}/"
        else:
             link = f"/appointment/{booking.id}/chat/"
             
        push_realtime_notification(
            user=other_user,
            title="Tin nhắn mới từ " + sender_name,
            message=msg_content[:50] + ("..." if len(msg_content)>50 else ""),
            level="info",
            category="chat",
            link=link
        )
