from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Q, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.views import View

from accounts.decorators import user_is_doctor, user_is_patient
from accounts.models import DoctorProfile, User
from home.models import MedicalHistory
from notifications.orchestrators import (
    schedule_booking_notifications,
    send_cancellation_notifications,
    send_reschedule_notifications,
)
from notifications.realtime import push_realtime_notification

from .forms import (
    CancellationAppointmentForm,
    CreateAppointmentForm,
    DoctorReviewForm,
    RescheduleAppointmentForm,
    TakeAppointmentForm,
)
from .models import Appointment, AppointmentChangeLog, TakeAppointment, DoctorReview


APPOINTMENT_CHANGE_DEADLINE_HOURS = getattr(settings, 'APPOINTMENT_CHANGE_DEADLINE_HOURS', 4)


def app(request):
    return render(request, 'b1.html')


def booking_datetime(booking):
    naive = datetime.combine(booking.date, booking.time)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def booking_can_be_modified(booking):
    if booking.status not in TakeAppointment.MODIFIABLE_STATUSES:
        return False, 'Chỉ có thể thay đổi lịch đang ở trạng thái chờ xác nhận hoặc đã xác nhận.'
    appointment_dt = booking_datetime(booking)
    if appointment_dt <= timezone.localtime():
        return False, 'Không thể thay đổi lịch đã diễn ra hoặc đã quá giờ khám.'
    deadline = appointment_dt - timedelta(hours=APPOINTMENT_CHANGE_DEADLINE_HOURS)
    if timezone.localtime() >= deadline:
        return False, f'Bạn chỉ có thể đổi hoặc hủy lịch trước tối thiểu {APPOINTMENT_CHANGE_DEADLINE_HOURS} giờ.'
    return True, ''


def status_badge(status):
    mapping = {
        TakeAppointment.STATUS_PENDING: ('warning', 'Chờ xác nhận'),
        TakeAppointment.STATUS_CONFIRMED: ('success', 'Đã xác nhận'),
        TakeAppointment.STATUS_ARRIVED: ('info', 'Đã đến khám'),
        TakeAppointment.STATUS_CANCELLED: ('secondary', 'Đã hủy'),
        TakeAppointment.STATUS_COMPLETED: ('primary', 'Đã hoàn thành'),
    }
    return mapping.get(status, ('secondary', status))


def create_change_log(booking, action, changed_by, reason='', old_appointment=None, old_date=None, old_time=None):
    AppointmentChangeLog.objects.create(
        booking=booking,
        action=action,
        changed_by=changed_by,
        old_appointment=old_appointment,
        new_appointment=booking.appointment,
        old_date=old_date,
        old_time=old_time,
        new_date=booking.date,
        new_time=booking.time,
        reason=reason or '',
    )


def notify_patient_booking_updated(booking, title, message, level='info'):
    push_realtime_notification(
        booking.user,
        title=title,
        message=message,
        level=level,
        category='appointment',
        link=reverse('patient-my-appointments'),
        payload={
            'booking_id': booking.id,
            'status': booking.status,
        },
    )


def notify_doctor_booking_updated(booking, title, message, level='info'):
    push_realtime_notification(
        booking.appointment.user,
        title=title,
        message=message,
        level=level,
        category='appointment',
        link=reverse('doctor-dashboard'),
        payload={
            'booking_id': booking.id,
            'status': booking.status,
        },
    )


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
        form.instance.user = self.request.user
        return super().form_valid(form)


class AppointmentListView(ListView):
    model = Appointment
    template_name = 'appointment/appointment.html'
    context_object_name = 'appointment'

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user, is_active=True).order_by('-id')


class DoctorPageView(ListView):
    paginate_by = 9
    model = Appointment
    context_object_name = 'doctor'
    template_name = 'doctor.html'

    def get_queryset(self):
        today = timezone.localdate()
        now_time = timezone.localtime().time()
        queryset = self.model.objects.filter(is_active=True).select_related('user').order_by('-id')
        
        doctor_ids = {app.user_id for app in queryset}
        reviews_data = DoctorReview.objects.filter(doctor_id__in=doctor_ids).values('doctor_id').annotate(avg_rating=Avg('rating'))
        ratings_map = {item['doctor_id']: round(item['avg_rating'], 1) for item in reviews_data}
        
        results = []
        for appointment in queryset:
            if appointment.date is not None:
                if not (appointment.date < today or (appointment.date == today and appointment.end_time <= now_time)):
                    appointment.avg_rating = ratings_map.get(appointment.user_id, 0)
                    results.append(appointment)
        return results


class TakeAppointmentView(CreateView):
    template_name = 'appointment/take_appointment.html'
    form_class = TakeAppointmentForm
    success_url = reverse_lazy('patient-my-appointments')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_context = {'title': 'Take Appointment'}

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'patient':
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_appointment(self):
        return get_object_or_404(Appointment, pk=self.kwargs.get('pk'), is_active=True)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        appointment = self.get_appointment()
        form.fields['appointment'].queryset = Appointment.objects.filter(pk=appointment.pk, is_active=True)
        form.fields['appointment'].initial = appointment
        self.extra_context.update({
            'appointment_date': appointment.date,
            'appointment_name': appointment.full_name,
            'appointment_department': appointment.department,
        })
        return form

    def form_valid(self, form):
        appointment = self.get_appointment()
        submitted_appointment = form.cleaned_data.get('appointment')
        selected_time = form.cleaned_data.get('time')

        if submitted_appointment != appointment:
            form.add_error('appointment', 'Lịch khám không hợp lệ.')
            return self.form_invalid(form)
        if selected_time is None:
            form.add_error('time', 'Vui lòng chọn giờ khám.')
            return self.form_invalid(form)
        if appointment.date == timezone.localdate() and selected_time <= timezone.localtime().time():
            form.add_error('time', 'Giờ khám phải lớn hơn thời điểm hiện tại.')
            return self.form_invalid(form)
        if not (appointment.start_time <= selected_time <= appointment.end_time):
            form.add_error('time', 'Giờ đã chọn nằm ngoài khung khám của bác sĩ.')
            return self.form_invalid(form)

        with transaction.atomic():
            locked_appointment = Appointment.objects.select_for_update().get(pk=appointment.pk)
            duplicated = TakeAppointment.objects.select_for_update().filter(
                appointment=locked_appointment,
                date=locked_appointment.date,
                time=selected_time,
                status__in=TakeAppointment.ACTIVE_STATUSES,
            )
            if duplicated.exists():
                form.add_error('time', 'Khung giờ này đã được đặt. Vui lòng chọn giờ khác.')
                return self.form_invalid(form)

            form.instance.user = self.request.user
            form.instance.appointment = locked_appointment
            form.instance.date = locked_appointment.date
            form.instance.time = selected_time
            form.instance.status = TakeAppointment.STATUS_CONFIRMED
            response = super().form_valid(form)
            create_change_log(
                self.object,
                AppointmentChangeLog.ACTION_BOOKED,
                changed_by=self.request.user,
                reason='Bệnh nhân tạo lịch hẹn mới.',
            )

        schedule_booking_notifications(self.object)
        notify_doctor_booking_updated(
            self.object,
            title='Có lịch hẹn mới',
            message=f'{self.object.full_name} vừa đặt lịch lúc {self.object.time.strftime("%H:%M")} ngày {self.object.date.strftime("%d/%m/%Y")}.',
            level='success',
        )
        messages.success(self.request, 'Đặt lịch khám thành công.')
        return response


class PatientOwnAppointmentListView(ListView):
    model = TakeAppointment
    context_object_name = 'appointments'
    template_name = 'appointment/patient_my_appointments.html'

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'patient':
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

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
        if request.user.role != 'patient':
            return redirect('login')
        self.object = self.get_object()
        can_modify, reason = booking_can_be_modified(self.object)
        if not can_modify:
            messages.error(request, reason)
            return redirect('patient-my-appointments')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects.filter(user=self.request.user, status__in=TakeAppointment.MODIFIABLE_STATUSES)
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
        booking = self.get_object()
        target_appointment = form.cleaned_data['appointment']
        new_time = form.cleaned_data['time']
        reason = form.cleaned_data.get('reason', '').strip()
        new_message = form.cleaned_data.get('message', '').strip()
        old_appointment = booking.appointment
        old_date = booking.date
        old_time = booking.time

        can_modify, message = booking_can_be_modified(booking)
        if not can_modify:
            form.add_error(None, message)
            return self.form_invalid(form)

        with transaction.atomic():
            locked_booking = TakeAppointment.objects.select_for_update().select_related('appointment', 'appointment__user', 'user').get(pk=booking.pk)
            current_slot = Appointment.objects.select_for_update().get(pk=locked_booking.appointment_id)
            new_slot = Appointment.objects.select_for_update().get(pk=target_appointment.pk)

            if not new_slot.is_active or new_slot.date < timezone.localdate():
                form.add_error('appointment', 'Lịch mới không còn khả dụng.')
                return self.form_invalid(form)
            if new_slot.date == timezone.localdate() and new_time <= timezone.localtime().time():
                form.add_error('time', 'Giờ mới phải lớn hơn thời điểm hiện tại.')
                return self.form_invalid(form)
            if not (new_slot.start_time <= new_time <= new_slot.end_time):
                form.add_error('time', 'Giờ mới phải nằm trong khung khám của bác sĩ.')
                return self.form_invalid(form)

            duplicated = TakeAppointment.objects.select_for_update().filter(
                appointment=new_slot,
                date=new_slot.date,
                time=new_time,
                status__in=TakeAppointment.ACTIVE_STATUSES,
            ).exclude(pk=locked_booking.pk)
            if duplicated.exists():
                form.add_error('time', 'Khung giờ mới đã có người khác chọn. Vui lòng thử giờ khác.')
                return self.form_invalid(form)

            locked_booking.appointment = new_slot
            locked_booking.date = new_slot.date
            locked_booking.time = new_time
            locked_booking.message = new_message or locked_booking.message
            locked_booking.status = TakeAppointment.STATUS_CONFIRMED
            locked_booking.notification_version += 1
            locked_booking.save(update_fields=['appointment', 'date', 'time', 'message', 'status', 'notification_version'])

            create_change_log(
                locked_booking,
                AppointmentChangeLog.ACTION_RESCHEDULED,
                changed_by=self.request.user,
                reason=reason,
                old_appointment=current_slot if current_slot.pk != new_slot.pk else old_appointment,
                old_date=old_date,
                old_time=old_time,
            )

        send_reschedule_notifications(locked_booking, old_date, old_time, previous_appointment=old_appointment)
        notify_doctor_booking_updated(
            locked_booking,
            title='Bệnh nhân vừa đổi lịch',
            message=f'{locked_booking.full_name} đã đổi sang {locked_booking.time.strftime("%H:%M")} ngày {locked_booking.date.strftime("%d/%m/%Y")}.',
            level='warning',
        )
        if old_appointment.user_id != locked_booking.appointment.user_id:
            push_realtime_notification(
                old_appointment.user,
                title='Bệnh nhân đã chuyển sang lịch khác',
                message=f'{locked_booking.full_name} không còn ở lịch khám của bạn lúc {old_time.strftime("%H:%M")} ngày {old_date.strftime("%d/%m/%Y")}.',
                level='warning',
                category='appointment',
                link=reverse('doctor-dashboard'),
                payload={'booking_id': locked_booking.id, 'status': locked_booking.status},
            )
        notify_patient_booking_updated(
            locked_booking,
            title='Đổi lịch thành công',
            message=f'Lịch khám của bạn đã chuyển sang {locked_booking.time.strftime("%H:%M")} ngày {locked_booking.date.strftime("%d/%m/%Y")}.',
            level='success',
        )
        messages.success(self.request, 'Đổi lịch thành công. Slot cũ đã được giải phóng.')
        return redirect(self.success_url)


class PatientCancelView(DeleteView):
    model = TakeAppointment
    success_url = reverse_lazy('patient-my-appointments')
    template_name = 'appointment/patient_delete.html'
    form_class = CancellationAppointmentForm

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'patient':
            return redirect('login')
        self.object = self.get_object()
        can_modify, reason = booking_can_be_modified(self.object)
        if request.method.lower() == 'get' and not can_modify:
            messages.error(request, reason)
            return redirect('patient-my-appointments')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects.filter(user=self.request.user, status__in=TakeAppointment.MODIFIABLE_STATUSES)
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
        can_modify, reason = booking_can_be_modified(self.object)
        if not can_modify:
            messages.error(request, reason)
            return redirect(self.success_url)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        cancellation_reason = form.cleaned_data.get('reason', '').strip()
        with transaction.atomic():
            booking = TakeAppointment.objects.select_for_update().select_related('appointment', 'appointment__user').get(pk=self.object.pk)
            can_modify, reason = booking_can_be_modified(booking)
            if not can_modify:
                messages.error(request, reason)
                return redirect(self.success_url)
            booking.status = TakeAppointment.STATUS_CANCELLED
            booking.cancelled_at = timezone.now()
            booking.notification_version += 1
            booking.save(update_fields=['status', 'cancelled_at', 'notification_version'])
            create_change_log(
                booking,
                AppointmentChangeLog.ACTION_CANCELLED,
                changed_by=request.user,
                reason=cancellation_reason,
                old_appointment=booking.appointment,
                old_date=booking.date,
                old_time=booking.time,
            )

        send_cancellation_notifications(booking, cancelled_by='patient')
        notify_doctor_booking_updated(
            booking,
            title='Bệnh nhân vừa hủy lịch',
            message=f'{booking.full_name} đã hủy lịch khám ngày {booking.date.strftime("%d/%m/%Y")} lúc {booking.time.strftime("%H:%M")}.',
            level='warning',
        )
        notify_patient_booking_updated(
            booking,
            title='Bạn đã hủy lịch khám',
            message=f'Lịch khám ngày {booking.date.strftime("%d/%m/%Y")} lúc {booking.time.strftime("%H:%M")} đã được hủy.',
            level='info',
        )
        messages.success(request, 'Hủy lịch thành công. Khung giờ cũ đã được mở lại cho bệnh nhân khác.')
        return redirect(self.success_url)


class PatientListView(ListView):
    model = TakeAppointment
    context_object_name = 'patients'
    template_name = 'appointment/patient_list.html'

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
            patient.histories = MedicalHistory.objects.filter(user=patient.user).order_by('-created_at')
        return context

    def get_queryset(self):
        queryset = self.model.objects.filter(
            appointment__user=self.request.user,
            status__in=[TakeAppointment.STATUS_PENDING, TakeAppointment.STATUS_CONFIRMED, TakeAppointment.STATUS_ARRIVED],
        ).order_by('date', 'time')
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
            status__in=[TakeAppointment.STATUS_PENDING, TakeAppointment.STATUS_CONFIRMED, TakeAppointment.STATUS_ARRIVED],
        ).select_related('appointment', 'appointment__user')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        with transaction.atomic():
            booking = TakeAppointment.objects.select_for_update().select_related('appointment', 'appointment__user').get(pk=self.object.pk)
            booking.status = TakeAppointment.STATUS_CANCELLED
            booking.cancelled_at = timezone.now()
            booking.notification_version += 1
            booking.save(update_fields=['status', 'cancelled_at', 'notification_version'])
            create_change_log(
                booking,
                AppointmentChangeLog.ACTION_CANCELLED,
                changed_by=request.user,
                reason='Bác sĩ hủy lịch khám.',
                old_appointment=booking.appointment,
                old_date=booking.date,
                old_time=booking.time,
            )
        send_cancellation_notifications(booking, cancelled_by='doctor')
        notify_patient_booking_updated(
            booking,
            title='Bác sĩ đã hủy lịch khám',
            message=f'Lịch khám ngày {booking.date.strftime("%d/%m/%Y")} lúc {booking.time.strftime("%H:%M")} đã bị bác sĩ hủy. Vui lòng đặt lịch mới.',
            level='danger',
        )
        return redirect(self.success_url)


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
        with transaction.atomic():
            active_bookings = list(
                TakeAppointment.objects.select_for_update().filter(
                    appointment=self.object,
                    status__in=TakeAppointment.ACTIVE_STATUSES,
                ).select_related('appointment', 'appointment__user')
            )
            for booking in active_bookings:
                booking.status = TakeAppointment.STATUS_CANCELLED
                booking.cancelled_at = timezone.now()
                booking.notification_version += 1
                booking.save(update_fields=['status', 'cancelled_at', 'notification_version'])
                create_change_log(
                    booking,
                    AppointmentChangeLog.ACTION_CANCELLED,
                    changed_by=request.user,
                    reason='Bác sĩ xóa ca khám đã đăng.',
                    old_appointment=booking.appointment,
                    old_date=booking.date,
                    old_time=booking.time,
                )
            self.object.is_active = False
            self.object.save(update_fields=['is_active'])

        for booking in active_bookings:
            send_cancellation_notifications(booking, cancelled_by='doctor')
            notify_patient_booking_updated(
                booking,
                title='Ca khám đã bị hủy',
                message=f'Lịch với bác sĩ {booking.appointment.full_name} ngày {booking.date.strftime("%d/%m/%Y")} lúc {booking.time.strftime("%H:%M")} đã bị hủy.',
                level='danger',
            )
        return redirect(self.success_url)


class DoctorDetailView(View):
    template_name = 'appointment/doctor_detail.html'

    def get(self, request, doctor_id):
        doctor = get_object_or_404(User, id=doctor_id, role='doctor')
        
        try:
            profile = doctor.doctor_profile
        except DoctorProfile.DoesNotExist:
            profile = None
            
        appointments = Appointment.objects.filter(
            user=doctor,
            is_active=True,
            date__gte=timezone.localdate()
        ).order_by('date', 'start_time')
        
        reviews = DoctorReview.objects.filter(doctor=doctor).select_related('patient')
        review_stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        context = {
            'doctor': doctor,
            'profile': profile,
            'appointments': appointments,
            'reviews': reviews,
            'avg_rating': round(review_stats['avg_rating'] or 0, 1),
            'total_reviews': review_stats['total_reviews'],
        }
        return render(request, self.template_name, context)


class SubmitReviewView(View):
    template_name = 'appointment/submit_review.html'
    
    @method_decorator(login_required(login_url='login'))
    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        booking = get_object_or_404(TakeAppointment, pk=pk, user=request.user, status=TakeAppointment.STATUS_COMPLETED)
        if hasattr(booking, 'review'):
            messages.info(request, "Bạn đã đánh giá lịch khám này rồi.")
            return redirect('patient-my-appointments')
            
        form = DoctorReviewForm()
        return render(request, self.template_name, {'form': form, 'booking': booking})

    def post(self, request, pk):
        booking = get_object_or_404(TakeAppointment, pk=pk, user=request.user, status=TakeAppointment.STATUS_COMPLETED)
        if hasattr(booking, 'review'):
            messages.info(request, "Bạn đã đánh giá lịch khám này rồi.")
            return redirect('patient-my-appointments')

        form = DoctorReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.doctor = booking.appointment.user
            review.patient = request.user
            review.booking = booking
            review.save()
            messages.success(request, "Cảm ơn bạn đã gửi đánh giá!")
            return redirect('patient-my-appointments')
        return render(request, self.template_name, {'form': form, 'booking': booking})


class ChatRoomView(View):
    template_name = 'appointment/chat_room.html'

    @method_decorator(login_required(login_url='login'))
    def dispatch(self, request, *args, **kwargs):
        self.booking_id = kwargs.get('booking_id')
        self.booking = get_object_or_404(TakeAppointment, id=self.booking_id)

        if request.user.role == 'patient' and self.booking.user != request.user:
            messages.error(request, 'Bạn không có quyền truy cập đoạn chat này.')
            return redirect('home')
            
        if request.user.role == 'doctor' and self.booking.appointment.user != request.user:
            messages.error(request, 'Bạn không có quyền truy cập đoạn chat này.')
            return redirect('home')

        # Check if chat is allowed (only pending, confirmed)
        if self.booking.status in ['completed', 'cancelled']:
            self.chat_enabled = False
        else:
            self.chat_enabled = True

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        from .models import DirectMessage
        if request.user.role == 'doctor':
            doctor = request.user
            patient = self.booking.user
            other_user = patient
        else:
            doctor = self.booking.appointment.user
            patient = request.user
            other_user = doctor

        messages_queryset = DirectMessage.objects.filter(
            booking__appointment__user=doctor,
            booking__user=patient
        ).order_by('created_at')
        
        context = {
            'booking': self.booking,
            'chat_messages': messages_queryset,
            'chat_enabled': self.chat_enabled,
            'other_user': other_user,
        }
        return render(request, self.template_name, context)


class DoctorInboxView(View):
    template_name = 'appointment/doctor_inbox.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, booking_id=None, *args, **kwargs):
        from .models import DirectMessage

        active_statuses = [TakeAppointment.STATUS_PENDING, TakeAppointment.STATUS_CONFIRMED, TakeAppointment.STATUS_ARRIVED]
        
        all_bookings = TakeAppointment.objects.filter(
            appointment__user=request.user
        ).annotate(
            last_msg_time=Max('messages__created_at')
        ).filter(
            Q(status__in=active_statuses) | Q(last_msg_time__isnull=False)
        ).select_related('user').order_by('-last_msg_time', '-date', '-time')

        seen_users = set()
        unique_bookings = []
        for b in all_bookings:
            if b.user_id not in seen_users:
                seen_users.add(b.user_id)
                unique_bookings.append(b)

        active_booking = None
        messages_queryset = None
        chat_enabled = False

        if booking_id:
            active_booking = get_object_or_404(TakeAppointment, id=booking_id, appointment__user=request.user)
            messages_queryset = DirectMessage.objects.filter(
                booking__appointment__user=request.user,
                booking__user=active_booking.user
            ).order_by('created_at')
            chat_enabled = active_booking.status in active_statuses

        context = {
            'bookings': unique_bookings,
            'active_booking': active_booking,
            'chat_messages': messages_queryset,
            'chat_enabled': chat_enabled,
            'user_image': request.user.image.url if request.user.image else None,
        }
        return render(request, self.template_name, context)
