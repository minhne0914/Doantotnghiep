from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('appoinment', '0010_appointment_is_active'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_enabled', models.BooleanField(default=True)),
                ('sms_enabled', models.BooleanField(default=False)),
                ('reminder_24h_enabled', models.BooleanField(default=True)),
                ('reminder_1h_enabled', models.BooleanField(default=True)),
                ('booking_updates_enabled', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preference', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AppointmentNotificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(choices=[('email', 'Email'), ('sms', 'SMS')], max_length=20)),
                ('event', models.CharField(choices=[('booking_confirmed', 'Booking Confirmed'), ('doctor_new_booking', 'Doctor New Booking'), ('reminder_24h', 'Reminder 24 Hours'), ('reminder_1h', 'Reminder 1 Hour'), ('booking_cancelled', 'Booking Cancelled'), ('booking_rescheduled', 'Booking Rescheduled')], max_length=50)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=20)),
                ('booking_version', models.PositiveIntegerField(default=1)),
                ('provider_message_id', models.CharField(blank=True, max_length=255)),
                ('error_message', models.TextField(blank=True)),
                ('scheduled_for', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('appointment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_logs', to='appoinment.takeappointment')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
