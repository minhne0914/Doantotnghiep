from django.urls import path
from .views import *


urlpatterns = [
    path('',app),
    path('doctor/appointment/create', AppointmentCreateView.as_view(), name='doctor-appointment-create'),
    path('doctor/appointment/', AppointmentListView.as_view(), name='doctor-appointment'),
    path('doctor/', DoctorPageView.as_view(), name='doctor'),
    path('patient-take-appointment/<pk>/', TakeAppointmentView.as_view(), name='take-appointment'),
    path('patient/my-appointments/', PatientOwnAppointmentListView.as_view(), name='patient-my-appointments'),
    path('patient/my-appointments/<pk>/reschedule/', PatientRescheduleView.as_view(), name='patient-reschedule-appointment'),
    path('patient/my-appointments/<pk>/cancel/', PatientCancelView.as_view(), name='patient-cancel-appointment'),
    path('doctor/dashboard/patient', PatientListView.as_view(), name='patient-list'),
    path('<pk>/patient/delete/', PatientDeleteView.as_view(), name='delete-patient'),
    path('<pk>/view/', AppointmentDeleteView.as_view(), name='delete-appointment'),
    path('doctor/<int:doctor_id>/profile/', DoctorDetailView.as_view(), name='doctor-profile-detail'),
    path('appointment/<pk>/review/', SubmitReviewView.as_view(), name='submit-doctor-review'),
    path('appointment/<int:booking_id>/chat/', ChatRoomView.as_view(), name='chat-room'),
    path('doctor/inbox/', DoctorInboxView.as_view(), name='doctor-inbox'),
    path('doctor/inbox/<int:booking_id>/', DoctorInboxView.as_view(), name='doctor-inbox-detail'),
]
