from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appoinment', '0018_takeappointment_default_pending'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='appointment',
            constraint=models.CheckConstraint(
                check=models.Q(('end_time__gt', models.F('start_time'))),
                name='appointment_end_time_after_start_time',
            ),
        ),
    ]
