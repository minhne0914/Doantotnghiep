from django.urls import path
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

]
