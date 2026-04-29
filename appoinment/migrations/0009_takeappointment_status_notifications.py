from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appoinment', '0008_alter_appointment_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='takeappointment',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='takeappointment',
            name='notification_version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='takeappointment',
            name='status',
            field=models.CharField(choices=[('booked', 'Booked'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='booked', max_length=20),
        ),
    ]
