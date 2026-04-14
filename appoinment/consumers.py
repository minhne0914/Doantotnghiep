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
        self.booking = await self._get_booking()
        if not self.booking:
            await self.close()
            return
            
        # Group name specific to this booking
        self.room_group_name = f'chat_booking_{self.booking_id}'

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
    def _get_booking(self):
        try:
            booking = TakeAppointment.objects.get(id=self.booking_id)
            # Ensure user is either patient or doctor for this booking
            if self.user.role == 'patient' and booking.user == self.user:
                return booking
            if self.user.role == 'doctor' and booking.appointment.user == self.user:
                return booking
            return None
        except TakeAppointment.DoesNotExist:
            return None

    @database_sync_to_async
    def _save_message(self, content):
        return DirectMessage.objects.create(
            booking=self.booking,
            sender=self.user,
            content=content
        )

    @database_sync_to_async
    def _push_chat_notification(self, msg_content):
        from notifications.realtime import push_realtime_notification
        other_user = self.booking.user if self.user.role == 'doctor' else self.booking.appointment.user
        sender_name = ("BS. " + self.user.last_name) if self.user.role == 'doctor' else self.booking.full_name
        
        if other_user.role == 'doctor':
             link = f"/doctor/inbox/{self.booking.id}/"
        else:
             link = f"/appointment/{self.booking.id}/chat/"
             
        push_realtime_notification(
            user=other_user,
            title="Tin nhắn mới từ " + sender_name,
            message=msg_content[:50] + ("..." if len(msg_content)>50 else ""),
            level="info",
            category="chat",
            link=link
        )
