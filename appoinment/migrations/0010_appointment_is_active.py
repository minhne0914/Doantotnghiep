from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appoinment', '0009_takeappointment_status_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
