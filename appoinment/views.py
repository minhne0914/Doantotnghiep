"""Views appoinment đã được làm thin - chỉ điều phối form và service.

Toàn bộ business logic (lock slot, change log, notification) nằm ở services.py.
"""

import datetime
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.decorators import user_is_doctor, user_is_patient
from accounts.models import DoctorProfile, User, UserRole
from home.models import MedicalHistory

from .forms import (
    CancellationAppointmentForm,
    CreateAppointmentForm,
    DoctorReviewForm,
    RescheduleAppointmentForm,
    TakeAppointmentForm,
)
from .models import Appointment, DoctorReview, TakeAppointment
from .services import (
    APPOINTMENT_CHANGE_DEADLINE_HOURS,
    BookingService,
    SLOT_GAP_SECONDS,
    booking_can_be_modified,
    booking_datetime,
    has_slot_conflict,
    status_badge,
)


logger = logging.getLogger(__name__)


# Default page size cho các ListView
DEFAULT_PAGE_SIZE = 20


def app(request):
    """Trang nội bộ '/appointment/' (giữ tương thích với template b1.html)."""
    return render(request, 'b1.html')


# =============================================================================
# Doctor: tạo / liệt kê / xóa khung khám
# =============================================================================

class AppointmentCreateView(CreateView):
    template_name = 'appointment/appointment_create.html'
    form_class = CreateAppointmentForm
    success_url = reverse_lazy('doctor-appointment')
    extra_context = {'title': 'Post New Appointment'}

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.full_name = f'{user.first_name} {user.last_name}'
        form.instance.image = user.image

        try:
            profile = user.doctor_profile
        except DoctorProfile.DoesNotExist:
            logger.info('Doctor %s has no DoctorProfile, using default placeholders.', user.id)
            profile = None

        form.instance.department = (profile.specialization if profile else None) or 'Chưa cập nhật'
        form.instance.qualification_name = (profile.qualifications if profile else None) or 'Chưa cập nhật'
        form.instance.institute_name = form.instance.hospital_name
        return super().form_valid(form)


class AppointmentListView(ListView):
    model = Appointment
    template_name = 'appointment/calendar.html'
    context_object_name = 'appointment'
    paginate_by = DEFAULT_PAGE_SIZE

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(
            user=self.request.user,
            is_active=True,
            date__gte=timezone.localdate(),
        ).order_by('-id')


class AppointmentDeleteView(DeleteView):
    model = Appointment
    success_url = reverse_lazy('doctor-appointment')
    template_name = 'appointment/appointment_delete.html'

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user, is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor'] = self.object.user
        context['user_image'] = self.object.user.image.url if self.object.user.image else None
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        BookingService.cancel_all_for_appointment(
            appointment=self.object, changed_by=request.user
        )
        return redirect(self.success_url)


# =============================================================================
# Doctor: trang danh sách bác sĩ (cho bệnh nhân tìm kiếm)
# =============================================================================

DEPARTMENT_CHOICES_VI = [
    ('Heart Disease', 'Bệnh tim mạch'),
    ('Diabetes Disease', 'Bệnh tiểu đường'),
    ('Breast Cancer', 'Ung thư vú'),
    ('Dentistry', 'Nha khoa'),
    ('Cardiology', 'Khoa Nội tim mạch'),
    ('ENT Specialists', 'Tai Mũi Họng'),
    ('Astrology', 'Tâm lý / Chiêm tinh học'),
    ('Neuroanatomy', 'Nội thần kinh'),
    ('Blood Screening', 'Xét nghiệm huyết học'),
    ('Eye Care', 'Nhãn khoa / Mắt'),
    ('Physical Therapy', 'Vật lý trị liệu'),
]


class DoctorPageView(ListView):
    paginate_by = 9
    model = Appointment
    context_object_name = 'doctor'
    template_name = 'doctor.html'

    def _parse_filter_date(self, raw_value, fallback):
        if not raw_value:
            return fallback
        try:
            return datetime.datetime.strptime(raw_value, '%Y-%m-%d').date()
        except ValueError:
            logger.debug('Invalid date filter %r, fall back to today', raw_value)
            return fallback

    def get_queryset(self):
        today = timezone.localdate()
        now_time = timezone.localtime().time()

        request_get = self.request.GET
        dept = request_get.get('department', '').strip()
        search = request_get.get('search', '').strip()
        target_date = self._parse_filter_date(request_get.get('date', '').strip(), today)

        queryset = (
            self.model.objects.filter(is_active=True, date=target_date)
            .select_related('user')
            .order_by('-id')
        )
        if dept:
            queryset = queryset.filter(department=dept)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) | Q(hospital_name__icontains=search)
            )

        # Annotate avg rating qua subquery thay vì 1 query thủ công bên ngoài
        queryset = queryset.annotate(avg_rating=Avg('user__doctor_reviews__rating'))

        # Lọc bỏ slot đã quá giờ trong ngày hôm nay
        results = []
        for appt in queryset:
            if appt.date == today and appt.end_time <= now_time:
                continue
            appt.avg_rating = round(appt.avg_rating, 1) if appt.avg_rating else 0
            results.append(appt)
        return results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.utils.translation import gettext_lazy as _

        context['search_val'] = self.request.GET.get('search', '').strip()
        context['dept_val'] = self.request.GET.get('department', '').strip()
        context['date_val'] = self.request.GET.get('date', '').strip()

        context['departments'] = [(code, _(label)) for code, label in DEPARTMENT_CHOICES_VI]

        # Xây query string giữ filter khi pagination
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['filter_qs'] = f'&{query_params.urlencode()}' if query_params else ''
        return context


# =============================================================================
# Patient: đặt lịch khám
# =============================================================================

class _PatientRequiredMixin:
    """Mixin yêu cầu user đã login và role = patient."""

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_patient', False):
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


def _build_available_slots(appointment, active_booking_times):
    """Sinh danh sách 30 phút slot trong khung khám (loại break trưa & quá khứ)."""
    start_dt = datetime.datetime.combine(appointment.date, appointment.start_time)
    end_dt = datetime.datetime.combine(appointment.date, appointment.end_time)

    break_start = datetime.time(11, 30)
    break_end = datetime.time(13, 0)
    now_local = timezone.localtime()

    slots = []
    current_dt = start_dt
    while current_dt + datetime.timedelta(minutes=30) <= end_dt:
        slot_time = current_dt.time()
        if break_start <= slot_time < break_end:
            current_dt += datetime.timedelta(minutes=30)
            continue

        is_taken = any(
            abs(
                (datetime.datetime.combine(appointment.date, b_time) - current_dt).total_seconds()
            ) < SLOT_GAP_SECONDS
            for b_time in active_booking_times
        )

        is_past = (
            appointment.date < now_local.date()
            or (appointment.date == now_local.date() and current_dt.time() <= now_local.time())
        )

        slots.append({
            'time_str': slot_time.strftime('%H:%M'),
            'is_taken': is_taken,
            'is_past': is_past,
        })
        current_dt += datetime.timedelta(minutes=30)
    return slots


class TakeAppointmentView(_PatientRequiredMixin, CreateView):
    template_name = 'appointment/take_appointment.html'
    form_class = TakeAppointmentForm
    success_url = reverse_lazy('patient-my-appointments')
    extra_context = {'title': 'Take Appointment'}

    def get_appointment(self):
        return get_object_or_404(Appointment, pk=self.kwargs.get('pk'), is_active=True)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        appointment = self.get_appointment()
        form.fields['appointment'].queryset = Appointment.objects.filter(pk=appointment.pk, is_active=True)
        form.fields['appointment'].initial = appointment
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.get_appointment()

        active_booking_times = list(
            TakeAppointment.objects.filter(
                appointment=appointment,
                date=appointment.date,
                status__in=TakeAppointment.ACTIVE_STATUSES,
            ).values_list('time', flat=True)
        )
        context['available_slots'] = _build_available_slots(appointment, active_booking_times)
        context['appointment_date'] = appointment.date

        doctor = appointment.user
        context['appointment_name'] = f'BS. {doctor.first_name} {doctor.last_name}'
        try:
            specialization = doctor.doctor_profile.specialization or appointment.department
        except DoctorProfile.DoesNotExist:
            specialization = appointment.department
        context['appointment_department'] = specialization
        return context

    def form_valid(self, form):
        appointment = self.get_appointment()
        submitted = form.cleaned_data.get('appointment')
        selected_time = form.cleaned_data.get('time')

        # Validation chung (mức form-level)
        if submitted != appointment:
            form.add_error('appointment', 'Lịch khám không hợp lệ.')
            return self.form_invalid(form)
        if selected_time is None:
            form.add_error('time', 'Vui lòng chọn giờ khám.')
            return self.form_invalid(form)
        if appointment.date < timezone.localdate():
            form.add_error('appointment', 'Lịch này đã ở trong quá khứ, không thể đăng ký.')
            return self.form_invalid(form)
        if appointment.date == timezone.localdate() and selected_time <= timezone.localtime().time():
            form.add_error('time', 'Giờ khám phải lớn hơn thời điểm hiện tại.')
            return self.form_invalid(form)
        if not (appointment.start_time <= selected_time <= appointment.end_time):
            form.add_error('time', 'Giờ đã chọn nằm ngoài khung khám của bác sĩ.')
            return self.form_invalid(form)

        result = BookingService.create_booking(
            user=self.request.user,
            appointment=appointment,
            full_name=form.cleaned_data.get('full_name'),
            phone_number=form.cleaned_data.get('phone_number'),
            message=form.cleaned_data.get('message') or '',
            selected_time=selected_time,
        )
        if result.error:
            form.add_error('time', result.error)
            return self.form_invalid(form)

        self.object = result.booking
        messages.success(self.request, 'Đặt lịch khám thành công.')
        return redirect(self.get_success_url())


# =============================================================================
# Patient: danh sách lịch của tôi / đổi / hủy
# =============================================================================

class PatientOwnAppointmentListView(_PatientRequiredMixin, ListView):
    model = TakeAppointment
    context_object_name = 'appointments'
    template_name = 'appointment/patient_my_appointments.html'
    paginate_by = DEFAULT_PAGE_SIZE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['change_deadline_hours'] = APPOINTMENT_CHANGE_DEADLINE_HOURS
        return context

    def get_queryset(self):
        queryset = (
            self.model.objects.filter(user=self.request.user)
            .select_related('appointment', 'appointment__user')
            .prefetch_related('change_logs')
            .order_by('date', 'time')
        )
        for booking in queryset:
            can_modify, reason = booking_can_be_modified(booking)
            badge_class, badge_label = status_badge(booking.status)
            booking.can_modify = can_modify
            booking.modify_reason = reason
            booking.badge_class = badge_class
            booking.badge_label = badge_label
            booking.change_history = booking.change_logs.all()[:5]
            booking.has_review = hasattr(booking, 'review')
        return queryset


class PatientRescheduleView(UpdateView):
    model = TakeAppointment
    form_class = RescheduleAppointmentForm
    template_name = 'appointment/patient_reschedule.html'
    success_url = reverse_lazy('patient-my-appointments')

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_patient', False):
            return redirect('login')
        self.object = self.get_object()
        can_modify, reason = booking_can_be_modified(self.object)
        if not can_modify:
            messages.error(request, reason)
            return redirect('patient-my-appointments')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects.filter(
                user=self.request.user,
                status__in=TakeAppointment.MODIFIABLE_STATUSES,
            )
            .select_related('appointment', 'appointment__user')
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_booking'] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['change_deadline_hours'] = APPOINTMENT_CHANGE_DEADLINE_HOURS
        context['current_appointment_dt'] = booking_datetime(self.object)
        return context

    def form_valid(self, form):
        booking, errors = BookingService.reschedule_booking(
            booking=self.get_object(),
            new_appointment=form.cleaned_data['appointment'],
            new_time=form.cleaned_data['time'],
            reason=form.cleaned_data.get('reason', '').strip(),
            new_message=form.cleaned_data.get('message', '').strip(),
            changed_by=self.request.user,
        )
        if errors:
            for field, msg in errors.items():
                form.add_error(field if field != '__all__' else None, msg)
            return self.form_invalid(form)

        messages.success(self.request, 'Đổi lịch thành công. Slot cũ đã được giải phóng.')
        return redirect(self.success_url)


class PatientCancelView(DeleteView):
    model = TakeAppointment
    success_url = reverse_lazy('patient-my-appointments')
    template_name = 'appointment/patient_delete.html'
    form_class = CancellationAppointmentForm

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_patient', False):
            return redirect('login')
        self.object = self.get_object()
        can_modify, reason = booking_can_be_modified(self.object)
        if request.method.lower() == 'get' and not can_modify:
            messages.error(request, reason)
            return redirect('patient-my-appointments')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects.filter(
                user=self.request.user,
                status__in=TakeAppointment.MODIFIABLE_STATUSES,
            )
            .select_related('appointment', 'appointment__user')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = kwargs.get('form') or CancellationAppointmentForm()
        context['change_deadline_hours'] = APPOINTMENT_CHANGE_DEADLINE_HOURS
        can_modify, reason = booking_can_be_modified(self.object)
        context['can_modify'] = can_modify
        context['modify_reason'] = reason
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CancellationAppointmentForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        booking, error_message = BookingService.cancel_by_patient(
            booking=self.object,
            reason=form.cleaned_data.get('reason', '').strip(),
            changed_by=request.user,
        )
        if error_message:
            messages.error(request, error_message)
            return redirect(self.success_url)

        messages.success(request, 'Hủy lịch thành công. Khung giờ cũ đã được mở lại cho bệnh nhân khác.')
        return redirect(self.success_url)


# =============================================================================
# Doctor: danh sách bệnh nhân
# =============================================================================

class PatientListView(ListView):
    model = TakeAppointment
    context_object_name = 'patients'
    template_name = 'appointment/patient_list.html'
    paginate_by = DEFAULT_PAGE_SIZE

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_image'] = user.image.url if user.image else None
        context['search'] = self.request.GET.get('search', '').strip()
        for patient in context.get('patients', []):
            patient.histories = MedicalHistory.objects.filter(
                user=patient.user
            ).order_by('-created_at')
        return context

    def get_queryset(self):
        queryset = (
            self.model.objects.filter(
                appointment__user=self.request.user,
                status__in=[
                    TakeAppointment.STATUS_PENDING,
                    TakeAppointment.STATUS_CONFIRMED,
                    TakeAppointment.STATUS_ARRIVED,
                ],
                date__gte=timezone.localdate(),
            )
            .select_related('user', 'appointment')
            .order_by('date', 'time')
        )
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(full_name__icontains=search)
        return queryset


class PatientDeleteView(DeleteView):
    model = TakeAppointment
    success_url = reverse_lazy('patient-list')
    template_name = 'appointment/doctor_patient_delete.html'

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(
            appointment__user=self.request.user,
            status__in=[
                TakeAppointment.STATUS_PENDING,
                TakeAppointment.STATUS_CONFIRMED,
                TakeAppointment.STATUS_ARRIVED,
            ],
        ).select_related('appointment', 'appointment__user')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        BookingService.cancel_by_doctor(
            booking=self.object,
            reason='Bác sĩ hủy lịch khám.',
            changed_by=request.user,
        )
        return redirect(self.success_url)


# =============================================================================
# Doctor profile public + Reviews
# =============================================================================

class DoctorDetailView(View):
    template_name = 'appointment/doctor_detail.html'

    def get(self, request, doctor_id):
        doctor = get_object_or_404(User, id=doctor_id, role=UserRole.DOCTOR)
        try:
            profile = doctor.doctor_profile
        except DoctorProfile.DoesNotExist:
            profile = None

        appointments = Appointment.objects.filter(
            user=doctor, is_active=True, date__gte=timezone.localdate()
        ).order_by('date', 'start_time')

        reviews = DoctorReview.objects.filter(doctor=doctor).select_related('patient')
        review_stats = reviews.aggregate(
            avg_rating=Avg('rating'), total_reviews=Count('id')
        )

        return render(request, self.template_name, {
            'doctor': doctor,
            'profile': profile,
            'appointments': appointments,
            'reviews': reviews,
            'avg_rating': round(review_stats['avg_rating'] or 0, 1),
            'total_reviews': review_stats['total_reviews'],
        })


class SubmitReviewView(View):
    template_name = 'appointment/submit_review.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def _get_completed_booking(self, request, pk):
        return get_object_or_404(
            TakeAppointment,
            pk=pk,
            user=request.user,
            status=TakeAppointment.STATUS_COMPLETED,
        )

    def get(self, request, pk):
        booking = self._get_completed_booking(request, pk)
        if hasattr(booking, 'review'):
            messages.info(request, 'Bạn đã đánh giá lịch khám này rồi.')
            return redirect('patient-my-appointments')
        return render(request, self.template_name, {'form': DoctorReviewForm(), 'booking': booking})

    def post(self, request, pk):
        booking = self._get_completed_booking(request, pk)
        if hasattr(booking, 'review'):
            messages.info(request, 'Bạn đã đánh giá lịch khám này rồi.')
            return redirect('patient-my-appointments')

        form = DoctorReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.doctor = booking.appointment.user
            review.patient = request.user
            review.booking = booking
            review.save()
            messages.success(request, 'Cảm ơn bạn đã gửi đánh giá!')
            return redirect('patient-my-appointments')
        return render(request, self.template_name, {'form': form, 'booking': booking})


# =============================================================================
# Chat / Inbox
# =============================================================================

class ChatRoomView(View):
    template_name = 'appointment/chat_room.html'

    @method_decorator(login_required(login_url='login'))
    def dispatch(self, request, *args, **kwargs):
        self.booking_id = kwargs.get('booking_id')
        self.booking = get_object_or_404(TakeAppointment, id=self.booking_id)

        # Phân quyền: chỉ chủ booking (patient) hoặc bác sĩ phụ trách được vào
        if request.user.role == UserRole.PATIENT and self.booking.user != request.user:
            messages.error(request, 'Bạn không có quyền truy cập đoạn chat này.')
            return redirect('home')
        if request.user.role == UserRole.DOCTOR and self.booking.appointment.user != request.user:
            messages.error(request, 'Bạn không có quyền truy cập đoạn chat này.')
            return redirect('home')

        self.chat_enabled = self.booking.status not in ('completed', 'cancelled')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        from .models import DirectMessage

        if request.user.role == UserRole.DOCTOR:
            doctor = request.user
            patient = self.booking.user
            other_user = patient
        else:
            doctor = self.booking.appointment.user
            patient = request.user
            other_user = doctor

        chat_qs = DirectMessage.objects.filter(
            booking__appointment__user=doctor, booking__user=patient,
        ).order_by('created_at')

        # Mark as read
        DirectMessage.objects.filter(
            booking__appointment__user=doctor,
            booking__user=patient,
            sender=other_user,
            is_read=False,
        ).update(is_read=True)

        return render(request, self.template_name, {
            'booking': self.booking,
            'chat_messages': chat_qs,
            'chat_enabled': self.chat_enabled,
            'other_user': other_user,
        })


class DoctorInboxView(View):
    template_name = 'appointment/doctor_inbox.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, booking_id=None, *args, **kwargs):
        from .models import DirectMessage

        active_statuses = (
            TakeAppointment.STATUS_PENDING,
            TakeAppointment.STATUS_CONFIRMED,
            TakeAppointment.STATUS_ARRIVED,
        )

        all_bookings = (
            TakeAppointment.objects.filter(appointment__user=request.user)
            .annotate(last_msg_time=Max('messages__created_at'))
            .filter(Q(status__in=active_statuses) | Q(last_msg_time__isnull=False))
            .select_related('user')
            .order_by('-last_msg_time', '-date', '-time')
        )

        seen_users = set()
        unique_bookings = []
        for b in all_bookings:
            if b.user_id in seen_users:
                continue
            seen_users.add(b.user_id)
            b.latest_msg = (
                DirectMessage.objects.filter(
                    booking__user=b.user, booking__appointment__user=request.user
                )
                .order_by('-created_at')
                .first()
            )
            b.has_unread = DirectMessage.objects.filter(
                booking__user=b.user,
                booking__appointment__user=request.user,
                sender=b.user,
                is_read=False,
            ).exists()
            unique_bookings.append(b)

        active_booking = None
        chat_qs = None
        chat_enabled = False
        if booking_id:
            active_booking = get_object_or_404(
                TakeAppointment, id=booking_id, appointment__user=request.user
            )
            chat_qs = DirectMessage.objects.filter(
                booking__appointment__user=request.user,
                booking__user=active_booking.user,
            ).order_by('created_at')
            chat_enabled = active_booking.status in active_statuses

            DirectMessage.objects.filter(
                booking__appointment__user=request.user,
                booking__user=active_booking.user,
                sender=active_booking.user,
                is_read=False,
            ).update(is_read=True)

        return render(request, self.template_name, {
            'bookings': unique_bookings,
            'active_booking': active_booking,
            'chat_messages': chat_qs,
            'chat_enabled': chat_enabled,
            'user_image': request.user.image.url if request.user.image else None,
        })


# =============================================================================
# Calendar API
# =============================================================================

class DoctorCalendarEventsAPI(View):
    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _parse_iso_date(raw, fallback):
        if not raw:
            return fallback
        try:
            return datetime.datetime.fromisoformat(raw.split('T')[0]).date()
        except (ValueError, AttributeError):
            return fallback

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        start_date = self._parse_iso_date(request.GET.get('start'), today)
        end_date = self._parse_iso_date(
            request.GET.get('end'), today + datetime.timedelta(days=30)
        )

        events = []

        # 1. Background events: ca làm việc
        doctor_shifts = Appointment.objects.filter(
            user=request.user,
            is_active=True,
            date__gte=start_date,
            date__lte=end_date,
        )
        for shift in doctor_shifts:
            events.append({
                'id': f'shift_{shift.id}',
                'start': f'{shift.date.isoformat()}T{shift.start_time.isoformat()}',
                'end': f'{shift.date.isoformat()}T{shift.end_time.isoformat()}',
                'display': 'background',
                'backgroundColor': '#e2e8f0',
            })

        # 2. Booking events
        color_map = {
            TakeAppointment.STATUS_PENDING: '#f59e0b',
            TakeAppointment.STATUS_CONFIRMED: '#10b981',
            TakeAppointment.STATUS_ARRIVED: '#3b82f6',
            TakeAppointment.STATUS_COMPLETED: '#6b7280',
            TakeAppointment.STATUS_CANCELLED: '#ef4444',
        }

        bookings = TakeAppointment.objects.filter(
            appointment__user=request.user,
            date__gte=start_date,
            date__lte=end_date,
        ).select_related('user', 'appointment')

        for booking in bookings:
            start_dt = datetime.datetime.combine(booking.date, booking.time)
            end_dt = start_dt + datetime.timedelta(minutes=30)
            title_prefix = '[Đã Hủy] ' if booking.status == TakeAppointment.STATUS_CANCELLED else ''

            events.append({
                'id': f'booking_{booking.id}',
                'title': f'{title_prefix}{booking.user.first_name} {booking.user.last_name}',
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
                'backgroundColor': color_map.get(booking.status, '#3788d8'),
                'borderColor': 'transparent',
                'textColor': '#fff',
                'extendedProps': {
                    'booking_id': booking.id,
                    'patient_name': f'{booking.user.first_name} {booking.user.last_name}',
                    'phone': booking.phone_number or 'Chưa cập nhật',
                    'message': booking.message or 'Không có',
                    'status': booking.get_status_display(),
                    'raw_status': booking.status,
                },
            })

        return JsonResponse(events, safe=False)
