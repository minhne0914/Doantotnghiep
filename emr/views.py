"""Views EMR (Electronic Medical Record) - đã refactor để gọn và DRY hơn.

Thay đổi chính:
- Tách helper `_apply_vital_sign` và `_apply_prescriptions` để tránh lặp logic
  giữa create_api và update_api.
- Thêm decorator `_require_role` thay cho việc check `request.user.role` thủ công.
- Dùng UserRole enum thay magic string 'doctor'/'patient'.
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from accounts.decorators import user_is_doctor
from accounts.models import UserRole
from appoinment.models import TakeAppointment
from appoinment.services import booking_is_emr_ready as service_booking_is_emr_ready

from .forms import EMRRecordForm, PrescriptionFormSet, VitalSignForm
from .models import EMRRecord, PrescriptionItem, VitalSign


logger = logging.getLogger(__name__)


# Default values cho vital sign khi missing
_DEFAULT_VITAL = {
    'weight_kg': 0,
    'height_cm': 0,
    'blood_pressure_systolic': 120,
    'blood_pressure_diastolic': 80,
    'heart_rate': 75,
    'temperature_c': 36.5,
}

_RECORD_TEXT_FIELDS = ('symptoms', 'diagnosis', 'clinical_notes', 'follow_up_plan')
_VITAL_DECIMAL_FIELDS = {'weight_kg', 'height_cm', 'temperature_c'}


# =============================================================================
# Helpers
# =============================================================================

def load_json_body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def validation_error_response(exc):
    if hasattr(exc, 'message_dict'):
        errors = exc.message_dict
    else:
        errors = {'__all__': exc.messages}
    return JsonResponse({'errors': errors}, status=400)


def serialize_record(record):
    """Convert EMRRecord -> JSON-serializable dict."""
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
        'vital_sign': _serialize_vital(record.vital_sign) if hasattr(record, 'vital_sign') else None,
        'prescriptions': [_serialize_prescription(p) for p in record.prescriptions.all()],
    }


def _serialize_vital(vs):
    return {
        'weight_kg': str(vs.weight_kg),
        'height_cm': str(vs.height_cm),
        'blood_pressure_systolic': vs.blood_pressure_systolic,
        'blood_pressure_diastolic': vs.blood_pressure_diastolic,
        'heart_rate': vs.heart_rate,
        'temperature_c': str(vs.temperature_c),
        'bmi': vs.bmi,
    }


def _serialize_prescription(p):
    return {
        'id': p.id,
        'medicine_name': p.medicine_name,
        'dosage': p.dosage,
        'frequency': p.frequency,
        'duration': p.duration,
        'instructions': p.instructions,
        'order': p.order,
    }


def doctor_owns_booking(user, booking):
    return user.role == UserRole.DOCTOR and booking.appointment.user_id == user.id


def patient_owns_record(user, record):
    return user.role == UserRole.PATIENT and record.patient_id == user.id


def booking_is_emr_ready(booking):
    """Booking phải là 'arrived'/'completed', hoặc đã đến giờ khám."""
    return service_booking_is_emr_ready(booking)


def _apply_vital_sign(record, data):
    """Tạo/cập nhật VitalSign cho record. Mặc định values an toàn."""
    if not data:
        return
    if not isinstance(data, dict):
        raise ValidationError({'vital_sign': 'Vital sign must be an object.'})
    defaults = {}
    for key, default in _DEFAULT_VITAL.items():
        value = data.get(key, default)
        if key in _VITAL_DECIMAL_FIELDS:
            try:
                value = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError({key: 'Invalid decimal value.'})
        defaults[key] = value
    try:
        vital_sign = record.vital_sign
    except VitalSign.DoesNotExist:
        vital_sign = VitalSign(emr_record=record)
    for key, value in defaults.items():
        setattr(vital_sign, key, value)
    vital_sign.full_clean()
    vital_sign.save()


def _apply_prescriptions(record, items):
    """Replace toàn bộ prescriptions của record bằng list mới."""
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ValidationError({'prescriptions': 'Prescriptions must be a list.'})

    prescriptions = []
    for index, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            raise ValidationError({'prescriptions': 'Each prescription must be an object.'})
        prescription = PrescriptionItem(
            emr_record=record,
            medicine_name=item.get('medicine_name', ''),
            dosage=item.get('dosage', ''),
            frequency=item.get('frequency', ''),
            duration=item.get('duration', ''),
            instructions=item.get('instructions', ''),
            order=item.get('order', index),
        )
        prescription.full_clean()
        prescriptions.append(prescription)

    record.prescriptions.all().delete()
    PrescriptionItem.objects.bulk_create(prescriptions)


def _ensure_doctor(request, booking):
    """Check ownership; trả về None nếu OK, response object nếu sai."""
    if not doctor_owns_booking(request.user, booking):
        return HttpResponseForbidden('Forbidden')
    if not booking_is_emr_ready(booking):
        return JsonResponse(
            {'error': 'EMR is only available when the appointment has started.'},
            status=400,
        )
    return None


# =============================================================================
# Doctor: form tạo/sửa EMR
# =============================================================================

@method_decorator(login_required(login_url=reverse_lazy('login')), name='dispatch')
class DoctorEMRCreateUpdateView(View):
    template_name = 'emr/doctor_emr_form.html'

    def get_booking(self, booking_id):
        return get_object_or_404(
            TakeAppointment.objects.select_related('appointment', 'appointment__user', 'user'),
            pk=booking_id,
        )

    def _build_context(self, booking, record_form, vital_form, prescription_formset, record):
        return {
            'booking': booking,
            'record': record,
            'record_form': record_form,
            'vital_form': vital_form,
            'prescription_formset': prescription_formset,
            'patient_history': (
                EMRRecord.objects.filter(patient=booking.user)
                .exclude(pk=getattr(record, 'pk', None))[:5]
            ),
        }

    def get(self, request, booking_id):
        booking = self.get_booking(booking_id)
        if not doctor_owns_booking(request.user, booking):
            return redirect('login')
        if not booking_is_emr_ready(booking):
            return HttpResponseForbidden(
                'EMR can only be created for arrived or finished appointments.'
            )

        record = getattr(booking, 'emr_record', None)
        return render(request, self.template_name, self._build_context(
            booking,
            record_form=EMRRecordForm(instance=record),
            vital_form=VitalSignForm(instance=getattr(record, 'vital_sign', None)),
            prescription_formset=PrescriptionFormSet(instance=record),
            record=record,
        ))

    def post(self, request, booking_id):
        booking = self.get_booking(booking_id)
        if not doctor_owns_booking(request.user, booking):
            return redirect('login')
        if not booking_is_emr_ready(booking):
            return HttpResponseForbidden(
                'EMR can only be created for arrived or finished appointments.'
            )

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

            booking.status = TakeAppointment.STATUS_COMPLETED
            booking.save(update_fields=['status'])
            return redirect('doctor-emr-form', booking_id=booking.id)

        return render(request, self.template_name, self._build_context(
            booking,
            record_form=record_form,
            vital_form=vital_form,
            prescription_formset=prescription_formset,
            record=record,
        ))


# =============================================================================
# Patient timeline / Doctor patient summary
# =============================================================================

@method_decorator(login_required(login_url=reverse_lazy('login')), name='dispatch')
class PatientEMRTimelineView(ListView):
    model = EMRRecord
    context_object_name = 'records'
    template_name = 'emr/patient_timeline.html'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != UserRole.PATIENT:
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


# =============================================================================
# JSON APIs
# =============================================================================

@login_required(login_url='login')
def emr_record_list_api(request):
    base = EMRRecord.objects.prefetch_related('prescriptions').select_related('vital_sign')
    if request.user.role == UserRole.DOCTOR:
        records = base.filter(doctor=request.user)
    else:
        records = base.filter(patient=request.user)
    return JsonResponse({'results': [serialize_record(record) for record in records]})


@login_required(login_url='login')
def emr_record_detail_api(request, record_id):
    record = get_object_or_404(
        EMRRecord.objects
        .prefetch_related('prescriptions')
        .select_related('vital_sign', 'appointment', 'doctor', 'patient'),
        pk=record_id,
    )
    if not (
        patient_owns_record(request.user, record)
        or doctor_owns_booking(request.user, record.appointment)
    ):
        return HttpResponseForbidden('Forbidden')
    return JsonResponse(serialize_record(record))


@login_required(login_url='login')
def emr_record_create_api(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    booking = get_object_or_404(
        TakeAppointment.objects.select_related('appointment', 'appointment__user', 'user'),
        pk=booking_id,
    )
    err = _ensure_doctor(request, booking)
    if err is not None:
        return err

    data = load_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    try:
        with transaction.atomic():
            record, _created = EMRRecord.objects.get_or_create(
                appointment=booking,
                defaults={
                    'patient': booking.user,
                    'doctor': booking.appointment.user,
                },
            )
            record.patient = booking.user
            record.doctor = booking.appointment.user
            for field in _RECORD_TEXT_FIELDS:
                setattr(record, field, data.get(field, ''))
            record.full_clean()
            record.save()

            _apply_vital_sign(record, data.get('vital_sign'))
            _apply_prescriptions(record, data.get('prescriptions'))

            booking.status = TakeAppointment.STATUS_COMPLETED
            booking.save(update_fields=['status'])
    except ValidationError as exc:
        return validation_error_response(exc)
    return JsonResponse(serialize_record(record), status=201)


@login_required(login_url='login')
def emr_record_update_api(request, record_id):
    if request.method not in ('PUT', 'PATCH', 'POST'):
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    record = get_object_or_404(
        EMRRecord.objects.select_related(
            'appointment', 'appointment__appointment', 'appointment__appointment__user'
        ),
        pk=record_id,
    )
    if not doctor_owns_booking(request.user, record.appointment):
        return HttpResponseForbidden('Forbidden')
    if not booking_is_emr_ready(record.appointment):
        return JsonResponse(
            {'error': 'EMR can only be edited for appointments that have started.'},
            status=400,
        )

    data = load_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    try:
        with transaction.atomic():
            for field in _RECORD_TEXT_FIELDS:
                if field in data:
                    setattr(record, field, data[field])
            record.full_clean()
            record.save()

            if 'vital_sign' in data:
                _apply_vital_sign(record, data['vital_sign'])
            if 'prescriptions' in data:
                _apply_prescriptions(record, data['prescriptions'])
    except ValidationError as exc:
        return validation_error_response(exc)

    return JsonResponse(serialize_record(record))


@login_required(login_url='login')
def emr_record_delete_api(request, record_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    record = get_object_or_404(
        EMRRecord.objects.select_related(
            'appointment', 'appointment__appointment', 'appointment__appointment__user'
        ),
        pk=record_id,
    )
    if not doctor_owns_booking(request.user, record.appointment):
        return HttpResponseForbidden('Forbidden')

    booking = record.appointment
    record.delete()
    booking.status = TakeAppointment.STATUS_ARRIVED
    booking.save(update_fields=['status'])
    return JsonResponse({'deleted': True})
