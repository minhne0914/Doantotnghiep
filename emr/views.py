import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from accounts.decorators import user_is_doctor
from appoinment.models import TakeAppointment
from .forms import EMRRecordForm, PrescriptionFormSet, VitalSignForm
from .models import EMRRecord, PrescriptionItem, VitalSign


def load_json_body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def serialize_record(record):
    return {
        'id': record.id,
        'appointment_id': record.appointment_id,
        'patient_id': record.patient_id,
        'doctor_id': record.doctor_id,
        'symptoms': record.symptoms,
        'diagnosis': record.diagnosis,
        'clinical_notes': record.clinical_notes,
        'follow_up_plan': record.follow_up_plan,
        'created_at': record.created_at.isoformat(),
        'updated_at': record.updated_at.isoformat(),
        'vital_sign': {
            'weight_kg': str(record.vital_sign.weight_kg),
            'height_cm': str(record.vital_sign.height_cm),
            'blood_pressure_systolic': record.vital_sign.blood_pressure_systolic,
            'blood_pressure_diastolic': record.vital_sign.blood_pressure_diastolic,
            'heart_rate': record.vital_sign.heart_rate,
            'temperature_c': str(record.vital_sign.temperature_c),
            'bmi': record.vital_sign.bmi,
        } if hasattr(record, 'vital_sign') else None,
        'prescriptions': [
            {
                'id': item.id,
                'medicine_name': item.medicine_name,
                'dosage': item.dosage,
                'frequency': item.frequency,
                'duration': item.duration,
                'instructions': item.instructions,
                'order': item.order,
            }
            for item in record.prescriptions.all()
        ],
    }


def doctor_owns_booking(user, booking):
    return user.role == 'doctor' and booking.appointment.user_id == user.id


def patient_owns_record(user, record):
    return user.role == 'patient' and record.patient_id == user.id


def booking_is_emr_ready(booking):
    if booking.status in (TakeAppointment.STATUS_CANCELLED, TakeAppointment.STATUS_PENDING):
        return False
    if booking.status in (TakeAppointment.STATUS_ARRIVED, TakeAppointment.STATUS_COMPLETED):
        return True
    if not booking.date or not booking.time:
        return False
    appointment_dt = timezone.make_aware(
        datetime.combine(booking.date, booking.time),
        timezone.get_current_timezone(),
    )
    return appointment_dt <= timezone.localtime()


@method_decorator(login_required(login_url=reverse_lazy('login')), name='dispatch')
class DoctorEMRCreateUpdateView(View):
    template_name = 'emr/doctor_emr_form.html'

    def get_booking(self, booking_id):
        return get_object_or_404(
            TakeAppointment.objects.select_related('appointment', 'appointment__user', 'user'),
            pk=booking_id,
        )

    def get(self, request, booking_id):
        booking = self.get_booking(booking_id)
        if not doctor_owns_booking(request.user, booking):
            return redirect('login')
        if not booking_is_emr_ready(booking):
            return HttpResponseForbidden('EMR can only be created for arrived or finished appointments.')

        record = getattr(booking, 'emr_record', None)
        record_form = EMRRecordForm(instance=record)
        vital_form = VitalSignForm(instance=getattr(record, 'vital_sign', None))
        prescription_formset = PrescriptionFormSet(instance=record)

        patient_history = EMRRecord.objects.filter(patient=booking.user).exclude(pk=getattr(record, 'pk', None))[:5]
        context = {
            'booking': booking,
            'record': record,
            'record_form': record_form,
            'vital_form': vital_form,
            'prescription_formset': prescription_formset,
            'patient_history': patient_history,
        }
        return render(request, self.template_name, context)

    def post(self, request, booking_id):
        booking = self.get_booking(booking_id)
        if not doctor_owns_booking(request.user, booking):
            return redirect('login')
        if not booking_is_emr_ready(booking):
            return HttpResponseForbidden('EMR can only be created for arrived or finished appointments.')

        record = getattr(booking, 'emr_record', None)
        record_form = EMRRecordForm(request.POST, instance=record)
        vital_form = VitalSignForm(request.POST, instance=getattr(record, 'vital_sign', None))
        prescription_formset = PrescriptionFormSet(request.POST, instance=record)

        if record_form.is_valid() and vital_form.is_valid() and prescription_formset.is_valid():
            emr_record = record_form.save(commit=False)
            emr_record.appointment = booking
            emr_record.patient = booking.user
            emr_record.doctor = booking.appointment.user
            emr_record.save()

            vital_sign = vital_form.save(commit=False)
            vital_sign.emr_record = emr_record
            vital_sign.save()

            prescription_formset.instance = emr_record
            prescription_formset.save()

            booking.status = 'completed'
            booking.save(update_fields=['status'])
            return redirect('doctor-emr-form', booking_id=booking.id)

        patient_history = EMRRecord.objects.filter(patient=booking.user).exclude(pk=getattr(record, 'pk', None))[:5]
        return render(request, self.template_name, {
            'booking': booking,
            'record': record,
            'record_form': record_form,
            'vital_form': vital_form,
            'prescription_formset': prescription_formset,
            'patient_history': patient_history,
        })


@method_decorator(login_required(login_url=reverse_lazy('login')), name='dispatch')
class PatientEMRTimelineView(ListView):
    model = EMRRecord
    context_object_name = 'records'
    template_name = 'emr/patient_timeline.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'patient':
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects.filter(patient=self.request.user)
            .select_related('appointment', 'appointment__appointment', 'doctor')
            .prefetch_related('prescriptions')
        )


@method_decorator(login_required(login_url=reverse_lazy('login')), name='dispatch')
class DoctorPatientSummaryView(View):
    template_name = 'emr/doctor_patient_summary.html'

    def get(self, request, patient_id, booking_id):
        booking = get_object_or_404(
            TakeAppointment.objects.select_related('appointment', 'appointment__user', 'user'),
            pk=booking_id,
            user_id=patient_id,
        )
        if not doctor_owns_booking(request.user, booking):
            return redirect('login')

        records = (
            EMRRecord.objects.filter(patient_id=patient_id)
            .select_related('vital_sign', 'doctor', 'appointment')
            .prefetch_related('prescriptions')[:10]
        )
        return render(request, self.template_name, {
            'booking': booking,
            'patient_records': records,
        })


@login_required(login_url='login')
def emr_record_list_api(request):
    if request.user.role == 'doctor':
        records = EMRRecord.objects.filter(doctor=request.user).prefetch_related('prescriptions').select_related('vital_sign')
    else:
        records = EMRRecord.objects.filter(patient=request.user).prefetch_related('prescriptions').select_related('vital_sign')
    return JsonResponse({'results': [serialize_record(record) for record in records]})


@login_required(login_url='login')
def emr_record_detail_api(request, record_id):
    record = get_object_or_404(EMRRecord.objects.prefetch_related('prescriptions').select_related('vital_sign', 'appointment', 'doctor', 'patient'), pk=record_id)
    if not (patient_owns_record(request.user, record) or doctor_owns_booking(request.user, record.appointment)):
        return HttpResponseForbidden('Forbidden')
    return JsonResponse(serialize_record(record))


@login_required(login_url='login')
def emr_record_create_api(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    booking = get_object_or_404(TakeAppointment.objects.select_related('appointment', 'appointment__user', 'user'), pk=booking_id)
    if not doctor_owns_booking(request.user, booking):
        return HttpResponseForbidden('Forbidden')
    if not booking_is_emr_ready(booking):
        return JsonResponse({'error': 'EMR is only available when the appointment has started.'}, status=400)

    data = load_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    record, _ = EMRRecord.objects.update_or_create(
        appointment=booking,
        defaults={
            'patient': booking.user,
            'doctor': booking.appointment.user,
            'symptoms': data.get('symptoms', ''),
            'diagnosis': data.get('diagnosis', ''),
            'clinical_notes': data.get('clinical_notes', ''),
            'follow_up_plan': data.get('follow_up_plan', ''),
        },
    )

    vital_data = data.get('vital_sign', {})
    VitalSign.objects.update_or_create(
        emr_record=record,
        defaults={
            'weight_kg': vital_data.get('weight_kg', 0),
            'height_cm': vital_data.get('height_cm', 0),
            'blood_pressure_systolic': vital_data.get('blood_pressure_systolic', 0),
            'blood_pressure_diastolic': vital_data.get('blood_pressure_diastolic', 0),
            'heart_rate': vital_data.get('heart_rate', 0),
            'temperature_c': vital_data.get('temperature_c', 36.5),
        },
    )

    record.prescriptions.all().delete()
    for index, item in enumerate(data.get('prescriptions', []), start=1):
        PrescriptionItem.objects.create(
            emr_record=record,
            medicine_name=item.get('medicine_name', ''),
            dosage=item.get('dosage', ''),
            frequency=item.get('frequency', ''),
            duration=item.get('duration', ''),
            instructions=item.get('instructions', ''),
            order=item.get('order', index),
        )

    booking.status = 'completed'
    booking.save(update_fields=['status'])
    return JsonResponse(serialize_record(record), status=201)


@login_required(login_url='login')
def emr_record_update_api(request, record_id):
    if request.method not in ('PUT', 'PATCH', 'POST'):
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    record = get_object_or_404(EMRRecord.objects.select_related('appointment', 'appointment__appointment', 'appointment__appointment__user'), pk=record_id)
    if not doctor_owns_booking(request.user, record.appointment):
        return HttpResponseForbidden('Forbidden')
    if not booking_is_emr_ready(record.appointment):
        return JsonResponse({'error': 'EMR can only be edited for appointments that have started.'}, status=400)

    data = load_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    for field in ['symptoms', 'diagnosis', 'clinical_notes', 'follow_up_plan']:
        if field in data:
            setattr(record, field, data[field])
    record.save()

    if 'vital_sign' in data:
        vital_data = data['vital_sign']
        VitalSign.objects.update_or_create(
            emr_record=record,
            defaults={
                'weight_kg': vital_data.get('weight_kg', 0),
                'height_cm': vital_data.get('height_cm', 0),
                'blood_pressure_systolic': vital_data.get('blood_pressure_systolic', 0),
                'blood_pressure_diastolic': vital_data.get('blood_pressure_diastolic', 0),
                'heart_rate': vital_data.get('heart_rate', 0),
                'temperature_c': vital_data.get('temperature_c', 36.5),
            },
        )

    if 'prescriptions' in data:
        record.prescriptions.all().delete()
        for index, item in enumerate(data['prescriptions'], start=1):
            PrescriptionItem.objects.create(
                emr_record=record,
                medicine_name=item.get('medicine_name', ''),
                dosage=item.get('dosage', ''),
                frequency=item.get('frequency', ''),
                duration=item.get('duration', ''),
                instructions=item.get('instructions', ''),
                order=item.get('order', index),
            )

    return JsonResponse(serialize_record(record))


@login_required(login_url='login')
def emr_record_delete_api(request, record_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    record = get_object_or_404(EMRRecord.objects.select_related('appointment', 'appointment__appointment', 'appointment__appointment__user'), pk=record_id)
    if not doctor_owns_booking(request.user, record.appointment):
        return HttpResponseForbidden('Forbidden')

    booking = record.appointment
    record.delete()
    booking.status = TakeAppointment.STATUS_ARRIVED
    booking.save(update_fields=['status'])
    return JsonResponse({'deleted': True})
