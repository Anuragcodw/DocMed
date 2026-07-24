"""
Appointment URL configuration.
Includes all payment, report center, prescription, video consultation,
doctor management, patient management, booking wizard, and admin routes.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from appointment.views import (
    AppointmentCreateView, AppointmentDeleteView, DoctorDashboardView,
    HomePageView, PatientDeleteView, PatientListView, SearchView, ServiceView,
    AboutView, ContactView,
    TakeAppointmentView, ApproveBookingView, CancelBookingView,
    RescheduleBookingView, PatientBookingsListView, PatientCancelBookingView,
    PatientRescheduleBookingView, CompleteBookingView, RejectBookingView,
    MarkMissedBookingView, ToggleAvailabilityView, AdminDashboardView, AdminDashboardStatsAPIView,
    VerifyDoctorView, ApproveReviewView, RejectReviewView,
    CreateMeetingView, JoinMeetingView, AdminExportCSVView,
    MeetingChatAPIView, MeetingFileAPIView, UpdateMeetingStatusView, SaveMeetingNotesView,
)
from appointment.api_views import DoctorsNearbyAPIView

from appointment.payment_views import (
    InitiatePaymentView, RazorpayOrderView, RazorpayCallbackView,
    StripeCheckoutView, StripeSuccessView, stripe_webhook,
    UPIPaymentConfirmView, PaymentSuccessView, PaymentFailedView,
    PaymentPendingView, PaymentHistoryView, InvoicePDFView,
    RequestRefundView, AdminRefundActionView
)
from appointment.prescription_views import (
    CreatePrescriptionView, PrescriptionDetailView, PrescriptionPDFView,
    PrescriptionHistoryView
)
from appointment.report_views import (
    MedicalReportCenterView, UploadReportView, ReportDetailView,
    AnalyzeReportView, AskReportAIView, DeleteReportView, DownloadReportView,
)
from appointment.doctor_views import (
    DoctorListView, DoctorPublicProfileView, DoctorProfileEditView,
    DoctorQualificationDeleteView, DoctorExperienceDeleteView,
    DoctorClinicDeleteView, DoctorDocumentDeleteView,
    DoctorVacationDeleteView, DoctorSlotDeleteView,
    DoctorSlotAvailabilityAPIView,
)
from appointment.patient_views import (
    PatientProfileView, PatientProfileEditView,
    PatientEmergencyContactDeleteView, PatientInsuranceDeleteView,
)
from appointment.booking_views import (
    BookingWizardView, SubmitReviewView, BookingDetailView,
    LikeReviewView, DoctorReplyReviewView, UpdateReviewView, DeleteReviewView
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from appointment.ai_views import AIChatView, AIRiskAssessmentView

app_name = 'appointment'

urlpatterns = [
    # ── Public Pages ──────────────────────────────────────────────────────────
    path('', HomePageView.as_view(), name='home'),
    path('service', ServiceView.as_view(), name='service'),
    path('about/', AboutView.as_view(), name='about'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('search/', SearchView.as_view(), name='search'),

    # ── JWT API ───────────────────────────────────────────────────────────────
    path('api/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/doctors/nearby/', DoctorsNearbyAPIView.as_view(), name='api-doctors-nearby'),
    path('api/doctors/<int:pk>/slots/', DoctorSlotAvailabilityAPIView.as_view(), name='api-doctor-slots'),
    path('api/ai/chat/', AIChatView.as_view(), name='api-ai-chat'),
    path('api/chatbot/', AIChatView.as_view(), name='api-chatbot'),
    path('api/ai/risk-assessment/', AIRiskAssessmentView.as_view(), name='api-ai-risk-assessment'),

    # ── Doctor Directory & Public Profile ─────────────────────────────────────
    path('doctors/', DoctorListView.as_view(), name='doctor-list'),
    path('doctors/<int:pk>/', DoctorPublicProfileView.as_view(), name='doctor-public-profile'),
    path('doctors/profile/edit/', DoctorProfileEditView.as_view(), name='doctor-profile-edit'),
    path('doctors/qualifications/<int:pk>/delete/', DoctorQualificationDeleteView.as_view(), name='doctor-qualification-delete'),
    path('doctors/experience/<int:pk>/delete/', DoctorExperienceDeleteView.as_view(), name='doctor-experience-delete'),
    path('doctors/clinics/<int:pk>/delete/', DoctorClinicDeleteView.as_view(), name='doctor-clinic-delete'),
    path('doctors/documents/<int:pk>/delete/', DoctorDocumentDeleteView.as_view(), name='doctor-document-delete'),
    path('doctors/vacations/<int:pk>/delete/', DoctorVacationDeleteView.as_view(), name='doctor-vacation-delete'),
    path('doctors/slots/<int:pk>/delete/', DoctorSlotDeleteView.as_view(), name='doctor-slot-delete'),

    # ── Patient Profile ───────────────────────────────────────────────────────
    path('patient/profile/', PatientProfileView.as_view(), name='patient-profile'),
    path('patient/profile/edit/', PatientProfileEditView.as_view(), name='patient-profile-edit'),
    path('patient/contacts/<int:pk>/delete/', PatientEmergencyContactDeleteView.as_view(), name='patient-contact-delete'),
    path('patient/insurance/<int:pk>/delete/', PatientInsuranceDeleteView.as_view(), name='patient-insurance-delete'),

    # ── Booking Wizard & Detail ───────────────────────────────────────────────
    path('booking/wizard/', BookingWizardView.as_view(), name='booking-wizard'),
    path('booking/<int:pk>/detail/', BookingDetailView.as_view(), name='booking-detail'),
    path('booking/<int:booking_id>/review/', SubmitReviewView.as_view(), name='submit-review'),
    path('review/<int:pk>/like/', LikeReviewView.as_view(), name='like-review'),
    path('review/<int:pk>/reply/', DoctorReplyReviewView.as_view(), name='reply-review'),
    path('review/<int:pk>/edit/', UpdateReviewView.as_view(), name='update-review'),
    path('review/<int:pk>/delete/', DeleteReviewView.as_view(), name='delete-review'),

    # ── Doctor Endpoints ──────────────────────────────────────────────────────
    path('doctor/appointment/create', AppointmentCreateView.as_view(), name='doctor-appointment-create'),
    path('doctor/appointment/', DoctorDashboardView.as_view(), name='doctor-appointment'),
    path('doctor/dashboard/', DoctorDashboardView.as_view(), name='doctor-dashboard'),
    path('<pk>/delete/', AppointmentDeleteView.as_view(), name='delete-appointment'),
    path('doctor/availability/toggle/', ToggleAvailabilityView.as_view(), name='doctor-toggle-availability'),

    # ── Patient Endpoints ─────────────────────────────────────────────────────
    path('patient-take-appointment/<pk>', TakeAppointmentView.as_view(), name='take-appointment'),
    path('patient/', PatientListView.as_view(), name='patient-list'),
    path('<pk>/patient/delete', PatientDeleteView.as_view(), name='delete-patient'),

    # ── Booking Management ────────────────────────────────────────────────────
    path('patient/bookings/', PatientBookingsListView.as_view(), name='patient-bookings'),
    path('patient/dashboard/', PatientBookingsListView.as_view(), name='patient-dashboard'),
    path('patient/booking/<pk>/cancel/', PatientCancelBookingView.as_view(), name='patient-cancel-booking'),
    path('patient/booking/<pk>/reschedule/', PatientRescheduleBookingView.as_view(), name='patient-reschedule-booking'),

    # ── Booking Status Actions ────────────────────────────────────────────────
    path('booking/<pk>/approve/', ApproveBookingView.as_view(), name='approve-booking'),
    path('booking/<pk>/cancel/', CancelBookingView.as_view(), name='cancel-booking'),
    path('booking/<pk>/reschedule/', RescheduleBookingView.as_view(), name='reschedule-booking'),
    path('booking/<pk>/complete/', CompleteBookingView.as_view(), name='complete-booking'),
    path('booking/<pk>/reject/', RejectBookingView.as_view(), name='reject-booking'),
    path('booking/<pk>/missed/', MarkMissedBookingView.as_view(), name='missed-booking'),

    # ── Admin Dashboard ───────────────────────────────────────────────────────
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin-dashboard/stats-api/', AdminDashboardStatsAPIView.as_view(), name='admin-dashboard-stats-api'),
    path('admin-dashboard/export/csv/', AdminExportCSVView.as_view(), name='admin-export-csv'),
    path('admin/doctor/<pk>/verify/', VerifyDoctorView.as_view(), name='admin-verify-doctor'),
    path('admin/review/<pk>/approve/', ApproveReviewView.as_view(), name='admin-approve-review'),
    path('admin/review/<pk>/reject/', RejectReviewView.as_view(), name='admin-reject-review'),

    # ── Payment ───────────────────────────────────────────────────────────────
    path('payment/<int:booking_id>/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('payment/<int:booking_id>/razorpay/order/', RazorpayOrderView.as_view(), name='razorpay-order'),
    path('payment/razorpay/callback/', RazorpayCallbackView.as_view(), name='razorpay-callback'),
    path('payment/<int:booking_id>/stripe/checkout/', StripeCheckoutView.as_view(), name='stripe-checkout'),
    path('payment/<int:booking_id>/stripe/success/', StripeSuccessView.as_view(), name='stripe-success'),
    path('payment/stripe/webhook/', stripe_webhook, name='stripe-webhook'),
    path('payment/<int:booking_id>/upi/confirm/', UPIPaymentConfirmView.as_view(), name='upi-confirm'),
    path('payment/success/<int:payment_id>/', PaymentSuccessView.as_view(), name='payment-success'),
    path('payment/failed/<int:booking_id>/', PaymentFailedView.as_view(), name='payment-failed'),
    path('payment/pending/<int:booking_id>/', PaymentPendingView.as_view(), name='payment-pending'),
    path('payment/history/', PaymentHistoryView.as_view(), name='payment-history'),
    path('payment/<int:payment_id>/invoice/', InvoicePDFView.as_view(), name='invoice-pdf'),
    path('payment/<int:payment_id>/refund/request/', RequestRefundView.as_view(), name='refund-request'),
    path('payment/<int:payment_id>/refund/action/', AdminRefundActionView.as_view(), name='admin-refund-action'),

    # ── Prescriptions ─────────────────────────────────────────────────────────
    path('booking/<int:booking_id>/prescription/create/', CreatePrescriptionView.as_view(), name='create-prescription'),
    path('booking/<int:booking_id>/prescription/', PrescriptionDetailView.as_view(), name='prescription-detail'),
    path('booking/<int:booking_id>/prescription/pdf/', PrescriptionPDFView.as_view(), name='prescription-pdf'),
    path('prescriptions/history/', PrescriptionHistoryView.as_view(), name='prescription-history'),

    # ── Medical Report Center ─────────────────────────────────────────────────
    path('reports/', MedicalReportCenterView.as_view(), name='report-center'),
    path('reports/upload/', UploadReportView.as_view(), name='upload-report'),
    path('reports/<int:pk>/', ReportDetailView.as_view(), name='report-detail'),
    path('reports/<int:pk>/analyze/', AnalyzeReportView.as_view(), name='analyze-report'),
    path('reports/<int:pk>/ask/', AskReportAIView.as_view(), name='ask-report-ai'),
    path('reports/<int:pk>/delete/', DeleteReportView.as_view(), name='delete-report'),
    path('reports/<int:pk>/download/', DownloadReportView.as_view(), name='download-report'),

    # ── Video Consultation ────────────────────────────────────────────────────
    path('booking/<pk>/meeting/create/', CreateMeetingView.as_view(), name='create-meeting'),
    path('booking/<pk>/meeting/join/', JoinMeetingView.as_view(), name='join-meeting'),

    # ── Meeting AJAX APIs ─────────────────────────────────────────────────────
    path('booking/<int:pk>/meeting/chat/', MeetingChatAPIView.as_view(), name='meeting-chat'),
    path('booking/<int:pk>/meeting/files/', MeetingFileAPIView.as_view(), name='meeting-files'),
    path('booking/<int:pk>/meeting/status/', UpdateMeetingStatusView.as_view(), name='meeting-status'),
    path('booking/<int:pk>/meeting/notes/', SaveMeetingNotesView.as_view(), name='meeting-notes'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
