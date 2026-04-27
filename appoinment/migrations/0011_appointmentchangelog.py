from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appoinment', '0010_appointment_is_active'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AppointmentChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('booked', 'Booked'), ('rescheduled', 'Rescheduled'), ('cancelled', 'Cancelled')], max_length=20)),
                ('old_date', models.DateField(blank=True, null=True)),
                ('old_time', models.TimeField(blank=True, null=True)),
                ('new_date', models.DateField(blank=True, null=True)),
                ('new_time', models.TimeField(blank=True, null=True)),
                ('reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_logs', to='appoinment.takeappointment')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointment_change_logs', to=settings.AUTH_USER_MODEL)),
                ('new_appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='new_change_logs', to='appoinment.appointment')),
                ('old_appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='old_change_logs', to='appoinment.appointment')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
