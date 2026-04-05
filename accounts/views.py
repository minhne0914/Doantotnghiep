import os
import random
import string
from datetime import timedelta

from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Count, Min
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, FormView, RedirectView, UpdateView

from accounts.forms import DoctorProfileUpdateForm, DoctorRegistrationForm, PatientProfileUpdateForm, PatientRegistrationForm, UserLoginForm
from accounts.models import User
from appoinment.models import AppointmentChangeLog, TakeAppointment
from notifications.forms import NotificationPreferenceForm
from notifications.models import NotificationPreference
from notifications.realtime import push_realtime_notification

from .decorators import user_is_doctor, user_is_patient


def generate_random_number():
    return ''.join(random.choice(string.digits) for _ in range(4))


def generate_unique_image_name(filename):
    ext = os.path.splitext(filename)[-1]
    random_number = generate_random_number()
    return f'doctor_{random_number}{ext}'


class RegisterPatientView(CreateView):
    model = User
    form_class = PatientRegistrationForm
    template_name = 'accounts/patient/register.html'
    success_url = '/'
    extra_context = {'title': 'Register'}

    def form_valid(self, form):
        user = form.save(commit=False)
        password = form.cleaned_data.get("password1")
        user.set_password(password)
        user.save()
        return redirect('login')


class LoginView(FormView):
    success_url = '/'
    form_class = UserLoginForm
    template_name = 'accounts/login.html'
    extra_context = {'title': 'Login'}

    def get_success_url(self):
        if 'next' in self.request.GET and self.request.GET['next'] != '':
            return self.request.GET['next']
        return self.success_url

    def form_valid(self, form):
        auth.login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class LogoutView(RedirectView):
    url = '/'

    def get(self, request, *args, **kwargs):
        auth.logout(request)
        messages.success(request, 'You are now logged out')
        return super().get(request, *args, **kwargs)


class RegisterDoctorView(CreateView):
    model = User
    form_class = DoctorRegistrationForm
    template_name = 'accounts/doctor/register.html'
    success_url = '/'
    extra_context = {'title': 'Register'}

    def form_valid(self, form):
        user = form.save(commit=False)
        password = form.cleaned_data.get("password1")
        user.set_password(password)
        user.save()
        return redirect('login')


class EditPatientProfileView(UpdateView):
    model = User
    form_class = PatientProfileUpdateForm
    context_object_name = 'patient'
    template_name = 'accounts/patient/edit-profile.html'
    success_url = reverse_lazy('patient-profile-update')

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = self.request.user
        if obj is None:
            raise Http404("Patient doesn't exists")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preference, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        context['notification_form'] = kwargs.get('notification_form') or NotificationPreferenceForm(instance=preference)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        notification_form = NotificationPreferenceForm(request.POST, instance=preference)

        if form.is_valid() and notification_form.is_valid():
            form.save()
            notification_form.save()
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form, notification_form=notification_form))


class EditDoctorProfileView(UpdateView):
    model = User
    form_class = DoctorProfileUpdateForm
    context_object_name = 'doctor'
    template_name = 'accounts/doctor/profile.html'
    success_url = reverse_lazy('doctor-profile-update')

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = self.request.user
        if obj is None:
            raise Http404("Doctor doesn't exists")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_image'] = user.image.url if user.image else None
        return context

    def form_valid(self, form):
        if 'image' in self.request.FILES:
            image = self.request.FILES['image']
            image.name = generate_unique_image_name(image.name)
            form.instance.image = SimpleUploadedFile(image.name, image.read())
        return super().form_valid(form)


class Dashboard(View):
    template_name = 'accounts/doctor/dashboard.html'

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        user = request.user
        user_image = user.image.url if user.image else None
        context = {
            'user_image': user_image,
            'dashboard_api_url': reverse_lazy('doctor-dashboard-data'),
            'dashboard_status_url_template': reverse_lazy('doctor-dashboard-update-status', kwargs={'booking_id': 0}),
        }
        return render(request, self.template_name, context)


def _doctor_bookings_queryset(user):
    return (
        TakeAppointment.objects.filter(appointment__user=user)
        .select_related('appointment', 'user', 'emr_record')
    )


def _status_presentation(status):
    mapping = {
        'pending': {'label': 'Chờ xác nhận', 'badge': 'warning'},
        'confirmed': {'label': 'Đã xác nhận', 'badge': 'success'},
        'arrived': {'label': 'Đang khám', 'badge': 'info'},
        'completed': {'label': 'Đã xong', 'badge': 'primary'},
        'cancelled': {'label': 'Đã hủy', 'badge': 'secondary'},
    }
    return mapping.get(status, {'label': status, 'badge': 'secondary'})


def _build_chart_series(rows, start_date, end_date):
    rows_by_date = {row['day']: row['total'] for row in rows}
    labels = []
    data = []
    cursor = start_date
    while cursor <= end_date:
        labels.append(cursor.strftime('%d/%m'))
        data.append(rows_by_date.get(cursor, 0))
        cursor += timedelta(days=1)
    return {'labels': labels, 'data': data}


def _patient_mix(base_queryset, start_date, end_date):
    range_patient_ids = list(
        base_queryset.filter(date__range=(start_date, end_date))
        .exclude(status='cancelled')
        .values_list('user_id', flat=True)
        .distinct()
    )
    if not range_patient_ids:
        return {'new': 0, 'returning': 0}

    first_visits = {
        row['user_id']: row['first_date']
        for row in (
            base_queryset.exclude(status='cancelled')
            .values('user_id')
            .annotate(first_date=Min('date'))
        )
    }
    new_count = sum(
        1 for patient_id in range_patient_ids
        if first_visits.get(patient_id) and start_date <= first_visits[patient_id] <= end_date
    )
    return {'new': new_count, 'returning': max(len(range_patient_ids) - new_count, 0)}


def _doctor_dashboard_payload(user):
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)
    now_time = timezone.localtime().time()

    base_queryset = _doctor_bookings_queryset(user)
    today_queryset = base_queryset.filter(date=today)

    status_counts = {
        row['status']: row['total']
        for row in today_queryset.values('status').annotate(total=Count('id'))
    }

    today_appointments = []
    for booking in today_queryset.order_by('time', 'id'):
        presentation = _status_presentation(booking.status)
        today_appointments.append({
            'id': booking.id,
            'patient_name': booking.full_name,
            'phone_number': booking.phone_number,
            'message': booking.message,
            'time': booking.time.strftime('%H:%M'),
            'status': booking.status,
            'status_label': presentation['label'],
            'status_badge': presentation['badge'],
            'is_overdue': booking.status in ('pending', 'confirmed') and booking.time <= now_time,
            'has_emr': hasattr(booking, 'emr_record'),
            'summary_url': reverse('doctor-patient-summary', kwargs={'patient_id': booking.user_id, 'booking_id': booking.id}),
            'emr_url': reverse('doctor-emr-form', kwargs={'booking_id': booking.id}),
        })

    weekly_rows = list(
        base_queryset.filter(date__range=(week_start, today))
        .exclude(status='cancelled')
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )
    monthly_rows = list(
        base_queryset.filter(date__range=(month_start, today))
        .exclude(status='cancelled')
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

    latest_notifications = []
    change_logs = (
        AppointmentChangeLog.objects.filter(booking__appointment__user=user)
        .select_related('booking', 'booking__appointment', 'changed_by')
        .order_by('-created_at')[:6]
    )
    for item in change_logs:
        if item.action == AppointmentChangeLog.ACTION_BOOKED:
            title = 'Lịch hẹn mới'
            description = f"{item.booking.full_name} vừa đặt lịch lúc {item.new_time.strftime('%H:%M')} ngày {item.new_date.strftime('%d/%m/%Y')}."
        elif item.action == AppointmentChangeLog.ACTION_RESCHEDULED:
            title = 'Lịch hẹn được đổi'
            description = f"{item.booking.full_name} vừa đổi lịch sang {item.new_time.strftime('%H:%M')} ngày {item.new_date.strftime('%d/%m/%Y')}."
        else:
            title = 'Lịch hẹn bị hủy'
            description = f"{item.booking.full_name} vừa hủy lịch lúc {item.old_time.strftime('%H:%M') if item.old_time else '--:--'} ngày {item.old_date.strftime('%d/%m/%Y') if item.old_date else '--/--/----'}."
        latest_notifications.append({
            'id': item.id,
            'title': title,
            'description': description,
            'created_at': timezone.localtime(item.created_at).strftime('%d/%m/%Y %H:%M'),
            'status': item.action,
        })

    return {
        'generated_at': timezone.localtime().strftime('%d/%m/%Y %H:%M'),
        'summary': {
            'today_total': today_queryset.count(),
            'completed': status_counts.get('completed', 0),
            'remaining': (
                status_counts.get('pending', 0)
                + status_counts.get('confirmed', 0)
                + status_counts.get('arrived', 0)
            ),
            'cancelled': status_counts.get('cancelled', 0),
        },
        'today_appointments': today_appointments,
        'charts': {
            'weekly_visits': _build_chart_series(weekly_rows, week_start, today),
            'monthly_visits': _build_chart_series(monthly_rows, month_start, today),
            'weekly_patient_mix': _patient_mix(base_queryset, week_start, today),
            'monthly_patient_mix': _patient_mix(base_queryset, month_start, today),
        },
        'latest_notifications': latest_notifications,
    }


@login_required(login_url='login')
@user_is_doctor
def doctor_dashboard_data_api(request):
    return JsonResponse(_doctor_dashboard_payload(request.user))


@login_required(login_url='login')
@user_is_doctor
def doctor_dashboard_update_status_api(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    booking = (
        TakeAppointment.objects.filter(appointment__user=request.user)
        .select_related('appointment', 'user')
        .filter(pk=booking_id)
        .first()
    )
    if booking is None:
        return JsonResponse({'error': 'Không tìm thấy lịch hẹn.'}, status=404)

    action = request.POST.get('action', '').strip()
    if action == 'confirm_arrival':
        if booking.status not in ('pending', 'confirmed'):
            return JsonResponse({'error': 'Chỉ có thể xác nhận bệnh nhân đã đến khi lịch đang chờ hoặc đã xác nhận.'}, status=400)
        booking.status = 'arrived'
        booking.save(update_fields=['status'])
        push_realtime_notification(
            booking.user,
            title='Bác sĩ đã xác nhận bạn đã đến',
            message=f'Bạn đã được chuyển sang trạng thái đang khám cho lịch {booking.time.strftime("%H:%M")} ngày {booking.date.strftime("%d/%m/%Y")}.',
            level='info',
            category='appointment',
            link=reverse('patient-my-appointments'),
            payload={'booking_id': booking.id, 'status': booking.status},
        )
    elif action == 'mark_completed':
        if booking.status == 'cancelled':
            return JsonResponse({'error': 'Không thể hoàn thành một lịch đã hủy.'}, status=400)
        if not hasattr(booking, 'emr_record'):
            return JsonResponse({'error': 'Hãy lưu bệnh án điện tử trước khi đánh dấu khám xong.'}, status=400)
        booking.status = 'completed'
        booking.save(update_fields=['status'])
        push_realtime_notification(
            booking.user,
            title='Buổi khám đã hoàn thành',
            message=f'Bác sĩ vừa đánh dấu hoàn thành lịch khám lúc {booking.time.strftime("%H:%M")} ngày {booking.date.strftime("%d/%m/%Y")}.',
            level='success',
            category='appointment',
            link=reverse('patient-emr-timeline'),
            payload={'booking_id': booking.id, 'status': booking.status},
        )
    else:
        return JsonResponse({'error': 'Thao tác không hợp lệ.'}, status=400)

    payload = _doctor_dashboard_payload(request.user)
    payload['message'] = 'Cập nhật trạng thái thành công.'
    return JsonResponse(payload)
