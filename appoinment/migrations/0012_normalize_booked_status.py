from django.db import migrations, models


def normalize_booked_to_confirmed(apps, schema_editor):
    TakeAppointment = apps.get_model('appoinment', 'TakeAppointment')
    TakeAppointment.objects.filter(status='booked').update(status='confirmed')


def revert_confirmed_to_booked(apps, schema_editor):
    TakeAppointment = apps.get_model('appoinment', 'TakeAppointment')
    TakeAppointment.objects.filter(status='confirmed').update(status='booked')


class Migration(migrations.Migration):

    dependencies = [
        ('appoinment', '0011_appointmentchangelog'),
    ]

    operations = [
        migrations.RunPython(normalize_booked_to_confirmed, reverse_code=revert_confirmed_to_booked),
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
                default='confirmed',
                max_length=20,
            ),
        ),
    ]
