"""Views cho accounts: đăng ký/đăng nhập, hồ sơ, dashboard bác sĩ.

Refactor: tách helper image upload, helper tạo notification, gom logic dashboard
vào hàm riêng và đổi `except Exception` chung chung sang specific exceptions.
"""

import logging
import os
import random
import string
from datetime import timedelta

from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Count, Min
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, FormView, RedirectView, UpdateView

from accounts.forms import (
    DoctorExtendedProfileForm,
    DoctorProfileUpdateForm,
    DoctorRegistrationForm,
    PatientProfileUpdateForm,
    PatientRegistrationForm,
    UserLoginForm,
)
from accounts.models import DoctorProfile, User, UserRole
from appoinment.models import AppointmentChangeLog, TakeAppointment
from notifications.forms import NotificationPreferenceForm
from notifications.models import NotificationPreference
from notifications.realtime import push_realtime_notification

from .decorators import user_is_doctor, user_is_patient


logger = logging.getLogger(__name__)


# =============================================================================
# Helpers (file-private)
# =============================================================================

def _generate_unique_image_name(filename):
    """Tránh trùng tên ảnh upload (avatar): doctor_<4 chữ số>.<ext>."""
    ext = os.path.splitext(filename)[-1]
    rand = ''.join(random.choice(string.digits) for _ in range(4))
    return f'doctor_{rand}{ext}'


def _attach_uploaded_image(form_instance, uploaded_file):
    """Đổi tên file upload và gắn vào form.instance.image.

    Tách ra để hai EditProfile views không lặp 4 dòng giống nhau.
    """
    uploaded_file.name = _generate_unique_image_name(uploaded_file.name)
    form_instance.image = SimpleUploadedFile(
        uploaded_file.name,
        uploaded_file.read(),
        content_type=getattr(uploaded_file, 'content_type', None),
    )


def _create_user_with_password(form):
    """Lưu user kèm hashing password. Tái dùng cho cả register patient & doctor."""
    user = form.save(commit=False)
    user.set_password(form.cleaned_data.get('password1'))
    user.save()
    return user


# =============================================================================
# Auth: register / login / logout
# =============================================================================

class RegisterPatientView(CreateView):
    model = User
    form_class = PatientRegistrationForm
    template_name = 'accounts/patient/register.html'
    success_url = '/'
    extra_context = {'title': 'Register'}

    def form_valid(self, form):
        _create_user_with_password(form)
        return redirect('login')


class RegisterDoctorView(CreateView):
    model = User
    form_class = DoctorRegistrationForm
    template_name = 'accounts/doctor/register.html'
    success_url = '/'
    extra_context = {'title': 'Register'}

    def form_valid(self, form):
        _create_user_with_password(form)
        return redirect('login')


class LoginView(FormView):
    success_url = '/'
    form_class = UserLoginForm
    template_name = 'accounts/login.html'
    extra_context = {'title': 'Login'}

    def get_success_url(self):
        next_url = self.request.GET.get('next', '').strip()
        return next_url or self.success_url

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


# =============================================================================
# Edit profile (Patient & Doctor)
# =============================================================================

class _BaseEditProfileView(UpdateView):
    """Phần chung giữa EditPatientProfileView và EditDoctorProfileView."""

    model = User
    role_required = None  # phải override
    decorator_role = None  # phải override

    def get_object(self, queryset=None):
        user = self.request.user
        if user is None or not user.is_authenticated:
            raise Http404('User does not exist')
        return user


class EditPatientProfileView(_BaseEditProfileView):
    form_class = PatientProfileUpdateForm
    context_object_name = 'patient'
    template_name = 'accounts/patient/edit-profile.html'
    success_url = reverse_lazy('patient-profile-update')
    role_required = UserRole.PATIENT

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_patient)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preference, _created = NotificationPreference.objects.get_or_create(user=self.request.user)
        context['notification_form'] = (
            kwargs.get('notification_form') or NotificationPreferenceForm(instance=preference)
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        preference, _created = NotificationPreference.objects.get_or_create(user=request.user)
        notification_form = NotificationPreferenceForm(request.POST, instance=preference)

        if form.is_valid() and notification_form.is_valid():
            form.save()
            notification_form.save()
            return redirect(self.success_url)
        return self.render_to_response(
            self.get_context_data(form=form, notification_form=notification_form)
        )


class EditDoctorProfileView(_BaseEditProfileView):
    form_class = DoctorProfileUpdateForm
    context_object_name = 'doctor'
    template_name = 'accounts/doctor/profile.html'
    success_url = reverse_lazy('doctor-profile-update')
    role_required = UserRole.DOCTOR

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_image'] = user.image.url if user.image else None

        doctor_profile, _created = DoctorProfile.objects.get_or_create(user=user)
        if 'extended_form' not in context:
            context['extended_form'] = DoctorExtendedProfileForm(instance=doctor_profile)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        doctor_profile, _created = DoctorProfile.objects.get_or_create(user=request.user)
        extended_form = DoctorExtendedProfileForm(request.POST, instance=doctor_profile)

        if not (form.is_valid() and extended_form.is_valid()):
            return self.render_to_response(
                self.get_context_data(form=form, extended_form=extended_form)
            )

        if 'image' in request.FILES:
            _attach_uploaded_image(form.instance, request.FILES['image'])

        user_obj = form.save()
        profile_obj = extended_form.save()
        self._sync_future_appointments(user_obj, profile_obj, has_new_image='image' in request.FILES)

        messages.success(request, 'Hồ sơ đã được cập nhật thành công.')
        return redirect(self.success_url)

    @staticmethod
    def _sync_future_appointments(user, profile, *, has_new_image):
        """Cập nhật snapshot tên/khoa/bằng cấp/ảnh trên các slot khám tương lai."""
        # Import muộn để tránh circular import giữa accounts và appoinment.
        from appoinment.models import Appointment

        future_apps = Appointment.objects.filter(user=user, date__gte=timezone.localdate())
        future_apps.update(
            full_name=f'{user.first_name} {user.last_name}',
            department=profile.specialization or 'Chưa cập nhật',
            qualification_name=profile.qualifications or 'Chưa cập nhật',
        )
        if has_new_image:
            for app in future_apps:
                app.image = user.image
                app.save(update_fields=['image'])


# =============================================================================
# Doctor dashboard (HTML + JSON API)
# =============================================================================

class Dashboard(View):
    template_name = 'accounts/doctor/dashboard.html'

    @method_decorator(login_required(login_url=reverse_lazy('login')))
    @method_decorator(user_is_doctor)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        user = request.user
        context = {
            'user_image': user.image.url if user.image else None,
            'dashboard_api_url': reverse_lazy('doctor-dashboard-data'),
            'dashboard_status_url_template': reverse_lazy(
                'doctor-dashboard-update-status', kwargs={'booking_id': 0}
            ),
        }
        return render(request, self.template_name, context)


# Map status -> nhãn UI + class badge bootstrap
_STATUS_PRESENTATION = {
    'pending': {'label': 'Chờ xác nhận', 'badge': 'warning'},
    'confirmed': {'label': 'Đã xác nhận', 'badge': 'success'},
    'arrived': {'label': 'Đang khám', 'badge': 'info'},
    'completed': {'label': 'Đã xong', 'badge': 'primary'},
    'cancelled': {'label': 'Đã hủy', 'badge': 'secondary'},
}


def _doctor_bookings_queryset(user):
    return (
        TakeAppointment.objects.filter(appointment__user=user)
        .select_related('appointment', 'user', 'emr_record')
    )


def _status_presentation(status):
    return _STATUS_PRESENTATION.get(status, {'label': status, 'badge': 'secondary'})


def _build_chart_series(rows, start_date, end_date):
    rows_by_date = {row['date']: row['total'] for row in rows}
    labels, data = [], []
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
        1 for pid in range_patient_ids
        if first_visits.get(pid) and start_date <= first_visits[pid] <= end_date
    )
    return {
        'new': new_count,
        'returning': max(len(range_patient_ids) - new_count, 0),
    }


def _build_today_appointments(today_queryset, now_time):
    appointments = []
    for booking in today_queryset.order_by('time', 'id'):
        presentation = _status_presentation(booking.status)
        appointments.append({
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
            'summary_url': reverse(
                'doctor-patient-summary',
                kwargs={'patient_id': booking.user_id, 'booking_id': booking.id},
            ),
            'emr_url': reverse('doctor-emr-form', kwargs={'booking_id': booking.id}),
        })
    return appointments


def _build_latest_notifications(user):
    items = (
        AppointmentChangeLog.objects.filter(booking__appointment__user=user)
        .select_related('booking', 'booking__appointment', 'changed_by')
        .order_by('-created_at')[:6]
    )

    def _fmt_time(t):
        return t.strftime('%H:%M') if t else '--:--'

    def _fmt_date(d):
        return d.strftime('%d/%m/%Y') if d else '--/--/----'

    notifications = []
    for item in items:
        if item.action == AppointmentChangeLog.ACTION_BOOKED:
            title = 'Lịch hẹn mới'
            description = f"{item.booking.full_name} vừa đặt lịch lúc {_fmt_time(item.new_time)} ngày {_fmt_date(item.new_date)}."
        elif item.action == AppointmentChangeLog.ACTION_RESCHEDULED:
            title = 'Lịch hẹn được đổi'
            description = f"{item.booking.full_name} vừa đổi lịch sang {_fmt_time(item.new_time)} ngày {_fmt_date(item.new_date)}."
        else:
            title = 'Lịch hẹn bị hủy'
            description = f"{item.booking.full_name} vừa hủy lịch lúc {_fmt_time(item.old_time)} ngày {_fmt_date(item.old_date)}."
        notifications.append({
            'id': item.id,
            'title': title,
            'description': description,
            'created_at': timezone.localtime(item.created_at).strftime('%d/%m/%Y %H:%M'),
            'status': item.action,
        })
    return notifications


def _doctor_dashboard_payload(user):
    """Tổng hợp dữ liệu hiển thị Dashboard bác sĩ.

    Trả về dict có sẵn keys: generated_at, summary, today_appointments, charts,
    latest_notifications.
    """
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

    weekly_rows = list(
        base_queryset.filter(date__range=(week_start, today))
        .exclude(status='cancelled')
        .values('date')
        .annotate(total=Count('id'))
        .order_by('date')
    )
    monthly_rows = list(
        base_queryset.filter(date__range=(month_start, today))
        .exclude(status='cancelled')
        .values('date')
        .annotate(total=Count('id'))
        .order_by('date')
    )

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
        'today_appointments': _build_today_appointments(today_queryset, now_time),
        'charts': {
            'weekly_visits': _build_chart_series(weekly_rows, week_start, today),
            'monthly_visits': _build_chart_series(monthly_rows, month_start, today),
            'weekly_patient_mix': _patient_mix(base_queryset, week_start, today),
            'monthly_patient_mix': _patient_mix(base_queryset, month_start, today),
        },
        'latest_notifications': _build_latest_notifications(user),
    }


@login_required(login_url='login')
@user_is_doctor
def doctor_dashboard_data_api(request):
    return JsonResponse(_doctor_dashboard_payload(request.user))


# Map action -> (allowed_old_statuses, new_status, requires_emr, patient_notification)
_STATUS_TRANSITIONS = {
    'confirm_arrival': {
        'allowed_from': ('pending', 'confirmed'),
        'new_status': 'arrived',
        'requires_emr': False,
        'error_msg': 'Chỉ có thể xác nhận bệnh nhân đã đến khi lịch đang chờ hoặc đã xác nhận.',
        'patient_notification': {
            'title': 'Bác sĩ đã xác nhận bạn đã đến',
            'level': 'info',
            'link_name': 'patient-my-appointments',
            'message_tpl': 'Bạn đã được chuyển sang trạng thái đang khám cho lịch {time} ngày {date}.',
        },
    },
    'mark_completed': {
        'allowed_from': ('pending', 'confirmed', 'arrived'),
        'new_status': 'completed',
        'requires_emr': True,
        'error_msg': 'Không thể hoàn thành một lịch đã hủy.',
        'patient_notification': {
            'title': 'Buổi khám đã hoàn thành',
            'level': 'success',
            'link_name': 'patient-emr-timeline',
            'message_tpl': 'Bác sĩ vừa đánh dấu hoàn thành lịch khám lúc {time} ngày {date}.',
        },
    },
}


def _push_status_notification(booking, transition):
    cfg = transition['patient_notification']
    push_realtime_notification(
        booking.user,
        title=cfg['title'],
        message=cfg['message_tpl'].format(
            time=booking.time.strftime('%H:%M'),
            date=booking.date.strftime('%d/%m/%Y'),
        ),
        level=cfg['level'],
        category='appointment',
        link=reverse(cfg['link_name']),
        payload={'booking_id': booking.id, 'status': booking.status},
    )


@login_required(login_url='login')
@user_is_doctor
def doctor_dashboard_update_status_api(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    booking = (
        TakeAppointment.objects.filter(appointment__user=request.user, pk=booking_id)
        .select_related('appointment', 'user')
        .first()
    )
    if booking is None:
        return JsonResponse({'error': 'Không tìm thấy lịch hẹn.'}, status=404)

    action = request.POST.get('action', '').strip()
    transition = _STATUS_TRANSITIONS.get(action)
    if transition is None:
        return JsonResponse({'error': 'Thao tác không hợp lệ.'}, status=400)

    if booking.status not in transition['allowed_from']:
        return JsonResponse({'error': transition['error_msg']}, status=400)

    if transition['requires_emr'] and not hasattr(booking, 'emr_record'):
        return JsonResponse(
            {'error': 'Hãy lưu bệnh án điện tử trước khi đánh dấu khám xong.'},
            status=400,
        )

    booking.status = transition['new_status']
    booking.save(update_fields=['status'])
    try:
        _push_status_notification(booking, transition)
    except Exception:  # nosec - notification thất bại không nên chặn request chính
        logger.exception('Failed to push realtime notification for booking %s', booking.id)

    payload = _doctor_dashboard_payload(request.user)
    payload['message'] = 'Cập nhật trạng thái thành công.'
    return JsonResponse(payload)
