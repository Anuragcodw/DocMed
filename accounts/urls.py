from django.urls import path
from accounts.views import (
    LoginView,
    LogoutView,
    RegisterView,
    AdminLoginView,
    DoctorLoginView,
    PatientLoginView,
    RegisterDoctorView,
    RegisterPatientView,
    RequestOTPView,
    VerifyOTPView,
    CheckUsernameView,
    CheckEmailView,
    VerifyEmailView,
    ForgotPasswordView,
    PasswordResetVerifyPhoneView,
    PasswordResetPhoneNewView,
    ResetPasswordConfirmCustomView,
    ResendVerificationView,
    DismissVerifyBannerView,
    DismissRegSuccessView,
    CompleteSocialRegistrationView,
    FirebaseAuthView,
    DoctorPendingVerificationView,
    DoctorDocumentDownloadView,
    SaveFCMTokenView,
)
from appointment.views import EditDoctorProfileView, EditPatientProfileView


app_name = 'accounts'

urlpatterns = [
    # Unified Registration
    path('register', RegisterView.as_view(), name='register'),
    path('register/', RegisterView.as_view(), name='register-slash'),
    path('doctor/pending-verification/', DoctorPendingVerificationView.as_view(), name='doctor_pending_verification'),
    path('patient/register', RegisterPatientView.as_view(), name='patient-register'),
    path('doctor/register', RegisterDoctorView.as_view(), name='doctor-register'),

    # Profile updates
    path('patient/profile/update/', EditPatientProfileView.as_view(), name='patient-profile-update'),
    path('doctor/profile/update/', EditDoctorProfileView.as_view(), name='doctor-profile-update'),

    # Unified Authentication
    path('login', LoginView.as_view(), name='login'),
    path('login/', LoginView.as_view(), name='login-slash'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('logout/', LogoutView.as_view(), name='logout-slash'),

    # Legacy redirects
    path('admin-login/', AdminLoginView.as_view(), name='admin-login'),
    path('doctor-login/', DoctorLoginView.as_view(), name='doctor-login'),
    path('patient-login/', PatientLoginView.as_view(), name='patient-login'),

    # SMS/Phone OTP Login
    path('otp/login', RequestOTPView.as_view(), name='otp-login'),
    path('otp/verify', VerifyOTPView.as_view(), name='otp-verify'),

    # Live AJAX Checks
    path('check-username/', CheckUsernameView.as_view(), name='check-username'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),

    # Custom Email Verification Link
    path('verify-email/<uuid:token>/', VerifyEmailView.as_view(), name='verify-email'),

    # Custom Password Reset (Email & Phone OTP paths)
    path('password-reset/', ForgotPasswordView.as_view(), name='password_reset'),
    path('password-reset/verify-phone/', PasswordResetVerifyPhoneView.as_view(), name='password_reset_verify_phone'),
    path('password-reset/phone-new/', PasswordResetPhoneNewView.as_view(), name='password_reset_phone_new'),
    path('reset/<uidb64>/<token>/', ResetPasswordConfirmCustomView.as_view(), name='password_reset_confirm_custom'),
    path('reset/<uidb64>/<token>/confirm/', ResetPasswordConfirmCustomView.as_view(), name='password_reset_confirm'),

    # Session UX dismiss helpers
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('dismiss-verify-banner/', DismissVerifyBannerView.as_view(), name='dismiss-verify-banner'),
    path('dismiss-reg-success/', DismissRegSuccessView.as_view(), name='dismiss-reg-success'),

    # Social registration completion (role selection for first-time Google users)
    path('complete-social-registration/', CompleteSocialRegistrationView.as_view(), name='complete_social_registration'),

    # Firebase Authentication API (Google Popup & Phone OTP backend token verification)
    path('api/firebase-login/', FirebaseAuthView.as_view(), name='firebase_login'),

    # Firebase Cloud Messaging Token Registration
    path('api/save-fcm-token/', SaveFCMTokenView.as_view(), name='api-save-fcm-token'),

    # Secure Doctor Document Download (owner + admin only)
    path(
        'doctor/document/<int:profile_id>/<str:doc_type>/',
        DoctorDocumentDownloadView.as_view(),
        name='doctor_document_download',
    ),
]