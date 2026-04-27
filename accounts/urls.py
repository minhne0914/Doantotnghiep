from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import *

urlpatterns = [
    path('patient/register', RegisterPatientView.as_view(), name='patient-register'),
    path('login', LoginView.as_view(), name='login'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('doctor/register', RegisterDoctorView.as_view(), name='doctor-register'),
    path('patient/profile/update/', EditPatientProfileView.as_view(), name='patient-profile-update'),
    path('doctor/profile/update/', EditDoctorProfileView.as_view(), name='doctor-profile-update'),
    path('doctor/dashboard/', Dashboard.as_view(), name='doctor-dashboard'),
    path('doctor/dashboard/profile', EditDoctorProfileView.as_view(), name='doctor-profile'),
    path('doctor/dashboard/data/', doctor_dashboard_data_api, name='doctor-dashboard-data'),
    path('doctor/dashboard/appointments/<int:booking_id>/status/', doctor_dashboard_update_status_api, name='doctor-dashboard-update-status'),

    # Password Reset URLs
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(template_name='accounts/password_reset/password_reset_form.html',
                                              email_template_name='accounts/password_reset/password_reset_email.html',
                                              success_url=reverse_lazy('password_reset_done')), 
         name='password_reset'),
         
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset/password_reset_done.html'), 
         name='password_reset_done'),
         
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset/password_reset_confirm.html',
                                                     success_url=reverse_lazy('password_reset_complete')), 
         name='password_reset_confirm'),
         
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset/password_reset_complete.html'), 
         name='password_reset_complete'),
]
