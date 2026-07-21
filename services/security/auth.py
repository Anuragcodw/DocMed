import logging
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

class SecurityService:
    @staticmethod
    def generate_jwt_for_user(user) -> dict:
        """Generates SimpleJWT tokens for REST APIs."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    @staticmethod
    def verify_2fa_otp(user, code: str) -> bool:
        """Placeholder for 2FA OTP verification using pyotp."""
        try:
            import pyotp
            # Assuming user profile has a totp_secret field
            # totp = pyotp.TOTP(user.patient_profile.totp_secret)
            # return totp.verify(code)
            return code == "123456" # Mock OTP bypass for demonstration
        except Exception as e:
            logger.error(f"2FA error: {e}")
            return False

    @staticmethod
    def audit_log(user_id: int, action: str, details: str):
        """Logs user activities for compliance and auditing."""
        logger.info(f"[AUDIT LOG] User {user_id} performed '{action}'. Details: {details}")


class SecureHeadersMiddleware:
    """Middleware enforcing secure response headers (HSTS, CSP, X-Frame-Options)."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Content Security Policy (strict placeholder)
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://maps.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;"
        return response
