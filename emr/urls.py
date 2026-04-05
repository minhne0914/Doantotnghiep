from django.urls import path

from .views import (
    DoctorEMRCreateUpdateView,
    DoctorPatientSummaryView,
    PatientEMRTimelineView,
    emr_record_create_api,
    emr_record_delete_api,
    emr_record_detail_api,
    emr_record_list_api,
    emr_record_update_api,
)


urlpatterns = [
    path('doctor/booking/<int:booking_id>/record/', DoctorEMRCreateUpdateView.as_view(), name='doctor-emr-form'),
    path('doctor/patient/<int:patient_id>/booking/<int:booking_id>/summary/', DoctorPatientSummaryView.as_view(), name='doctor-patient-summary'),
    path('patient/timeline/', PatientEMRTimelineView.as_view(), name='patient-emr-timeline'),
    path('api/records/', emr_record_list_api, name='emr-record-list-api'),
    path('api/records/<int:record_id>/', emr_record_detail_api, name='emr-record-detail-api'),
    path('api/bookings/<int:booking_id>/records/create/', emr_record_create_api, name='emr-record-create-api'),
    path('api/records/<int:record_id>/update/', emr_record_update_api, name='emr-record-update-api'),
    path('api/records/<int:record_id>/delete/', emr_record_delete_api, name='emr-record-delete-api'),
]
