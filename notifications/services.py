from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_email_message(subject, template_name, context, recipient_email):
    html_body = render_to_string(template_name, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )
    message.attach_alternative(html_body, 'text/html')
    return message.send()


def send_sms_message(message, phone_number):
    provider = getattr(settings, 'SMS_PROVIDER', 'twilio').lower()
    if provider == 'twilio':
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        sms = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number,
        )
        return sms.sid

    raise NotImplementedError('SMS provider is not configured.')
