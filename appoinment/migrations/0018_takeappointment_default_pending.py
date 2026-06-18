from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appoinment', '0017_alter_appointment_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointmentchangelog',
            name='action',
            field=models.CharField(
                choices=[
                    ('booked', 'Booked'),
                    ('confirmed', 'Confirmed'),
                    ('rescheduled', 'Rescheduled'),
                    ('cancelled', 'Cancelled'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='takeappointment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('confirmed', 'Confirmed'),
                    ('arrived', 'Arrived'),
                    ('cancelled', 'Cancelled'),
                    ('completed', 'Completed'),
                ],
                db_index=True,
                default='pending',
                max_length=20,
            ),
        ),
    ]
