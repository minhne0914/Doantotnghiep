import base64
import binascii
import os

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils.text import get_valid_filename

from accounts.models import UserRole
from accounts.validators import DEFAULT_ATTACHMENT_MAX_BYTES

from .models import DirectMessage, TakeAppointment


MAX_CHAT_MESSAGE_CHARS = 2000
MAX_CHAT_ATTACHMENT_BYTES = int(
    getattr(settings, 'MAX_CHAT_ATTACHMENT_BYTES', DEFAULT_ATTACHMENT_MAX_BYTES)
)
MAX_CHAT_ATTACHMENT_BASE64_CHARS = ((MAX_CHAT_ATTACHMENT_BYTES + 2) // 3) * 4 + 128
ALLOWED_CHAT_ATTACHMENT_CONTENT_TYPES = set(getattr(
    settings,
    'ALLOWED_CHAT_ATTACHMENT_CONTENT_TYPES',
    ('image/jpeg', 'image/png', 'image/webp', 'application/pdf', 'text/plain'),
))
ALLOWED_CHAT_ATTACHMENT_EXTENSIONS = set(getattr(
    settings,
    'ALLOWED_CHAT_ATTACHMENT_EXTENSIONS',
    ('.jpg', '.jpeg', '.png', '.webp', '.pdf', '.txt'),
))


class DirectChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if self.user is None or self.user.is_anonymous:
            await self.close()
            return

        self.booking_id = self.scope['url_route']['kwargs']['booking_id']
        self.booking, doctor_id, patient_id = await self._get_booking_details()
        if not self.booking:
            await self.close()
            return

        self.room_group_name = f'chat_doc{doctor_id}_pat{patient_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive_json(self, content, **kwargs):
        message = (content.get('message') or '').strip()
        attachment_data = content.get('attachment_data')
        attachment_name = content.get('attachment_name')

        if not message and not attachment_data:
            return
        if len(message) > MAX_CHAT_MESSAGE_CHARS:
            await self.send_json({
                'type': 'error',
                'error': 'Tin nhan vuot qua gioi han cho phep.',
            })
            return
        if not await self._chat_can_accept_messages():
            await self.send_json({
                'type': 'error',
                'error': 'Doan chat da dong vi lich hen da hoan tat hoac bi huy.',
            })
            return

        saved_message, error = await self._save_message(
            message,
            attachment_data,
            attachment_name,
        )
        if error:
            await self.send_json({'type': 'error', 'error': error})
            return

        await self._push_chat_notification(message if message else '[File dinh kem]')
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': saved_message['id'],
                'message': saved_message['content'],
                'attachment_url': saved_message['attachment_url'],
                'sender_id': self.user.id,
                'sender_name': self.user.full_name,
                'timestamp': saved_message['timestamp'],
            },
        )

    async def chat_message(self, event):
        await self.send_json({
            'id': event['id'],
            'message': event['message'],
            'attachment_url': event.get('attachment_url'),
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
        })

    @database_sync_to_async
    def _get_booking_details(self):
        try:
            booking = (
                TakeAppointment.objects
                .select_related('appointment', 'appointment__user')
                .get(id=self.booking_id)
            )
            if self.user.role == UserRole.PATIENT and booking.user_id == self.user.id:
                return booking, booking.appointment.user_id, booking.user_id
            if self.user.role == UserRole.DOCTOR and booking.appointment.user_id == self.user.id:
                return booking, booking.appointment.user_id, booking.user_id
            return None, None, None
        except TakeAppointment.DoesNotExist:
            return None, None, None

    @database_sync_to_async
    def _chat_can_accept_messages(self):
        return TakeAppointment.objects.filter(
            id=self.booking_id,
            status__in=TakeAppointment.ACTIVE_STATUSES,
        ).exists()

    @staticmethod
    def _decode_attachment(attachment_data, attachment_name):
        if not attachment_data or not attachment_name:
            return None, None
        if not isinstance(attachment_data, str) or ';base64,' not in attachment_data:
            return None, 'File dinh kem khong dung dinh dang.'

        header, b64_str = attachment_data.split(';base64,', 1)
        if len(b64_str) > MAX_CHAT_ATTACHMENT_BASE64_CHARS:
            return None, 'File dinh kem vuot qua gioi han dung luong cho phep.'

        content_type = ''
        if header.startswith('data:'):
            content_type = header[5:].split(';', 1)[0].lower()
        if content_type not in ALLOWED_CHAT_ATTACHMENT_CONTENT_TYPES:
            return None, 'Loai file dinh kem khong duoc ho tro.'

        safe_name = get_valid_filename(os.path.basename(str(attachment_name)).strip())
        if not safe_name:
            return None, 'Ten file dinh kem khong hop le.'

        extension = os.path.splitext(safe_name)[1].lower()
        if extension not in ALLOWED_CHAT_ATTACHMENT_EXTENSIONS:
            return None, 'Phan mo rong file dinh kem khong duoc ho tro.'

        try:
            decoded = base64.b64decode(b64_str, validate=True)
        except (binascii.Error, ValueError):
            return None, 'File dinh kem khong phai base64 hop le.'

        if len(decoded) > MAX_CHAT_ATTACHMENT_BYTES:
            return None, 'File dinh kem vuot qua gioi han dung luong cho phep.'

        return ContentFile(decoded, name=safe_name), None

    @database_sync_to_async
    def _save_message(self, content, attachment_data=None, attachment_name=None):
        msg = DirectMessage.objects.create(
            booking_id=self.booking_id,
            sender_id=self.user.id,
            content=content,
            is_read=False,
        )

        if attachment_data and attachment_name:
            attachment, error = self._decode_attachment(attachment_data, attachment_name)
            if error:
                msg.delete()
                return None, error
            msg.attachments = attachment
            msg.save(update_fields=['attachments'])

        return {
            'id': msg.id,
            'content': msg.content,
            'attachment_url': msg.attachments.url if msg.attachments else None,
            'timestamp': msg.created_at.strftime('%H:%M %d/%m/%Y'),
        }, None

    @database_sync_to_async
    def _push_chat_notification(self, msg_content):
        from notifications.realtime import push_realtime_notification

        booking = (
            TakeAppointment.objects
            .select_related('user', 'appointment__user')
            .get(id=self.booking_id)
        )
        other_user = booking.user if self.user.role == UserRole.DOCTOR else booking.appointment.user
        sender_name = f'BS. {self.user.last_name}' if self.user.role == UserRole.DOCTOR else booking.full_name
        link = (
            reverse('doctor-inbox-detail', args=[booking.id])
            if other_user.role == UserRole.DOCTOR
            else reverse('chat-room', args=[booking.id])
        )

        push_realtime_notification(
            user=other_user,
            title='Tin nhan moi tu ' + sender_name,
            message=msg_content[:50] + ('...' if len(msg_content) > 50 else ''),
            level='info',
            category='chat',
            link=link,
        )
