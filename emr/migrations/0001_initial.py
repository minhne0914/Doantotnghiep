from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('appoinment', '0010_appointment_is_active'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EMRRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symptoms', models.TextField()),
                ('diagnosis', models.TextField()),
                ('clinical_notes', models.TextField(blank=True)),
                ('follow_up_plan', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('appointment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='emr_record', to='appoinment.takeappointment')),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_emr_records', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_emr_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='VitalSign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight_kg', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('height_cm', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('blood_pressure_systolic', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(40), django.core.validators.MaxValueValidator(300)])),
                ('blood_pressure_diastolic', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(30), django.core.validators.MaxValueValidator(200)])),
                ('heart_rate', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(20), django.core.validators.MaxValueValidator(250)])),
                ('temperature_c', models.DecimalField(decimal_places=1, max_digits=4, validators=[django.core.validators.MinValueValidator(30), django.core.validators.MaxValueValidator(45)])),
                ('emr_record', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='vital_sign', to='emr.emrrecord')),
            ],
        ),
        migrations.CreateModel(
            name='PrescriptionItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('medicine_name', models.CharField(max_length=255)),
                ('dosage', models.CharField(max_length=255)),
                ('frequency', models.CharField(max_length=255)),
                ('duration', models.CharField(max_length=255)),
                ('instructions', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('emr_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prescriptions', to='emr.emrrecord')),
            ],
            options={'ordering': ['order', 'id']},
        ),
    ]
