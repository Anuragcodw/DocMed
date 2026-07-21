import pyotp
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from accounts.models import PhoneOTP, User

class OTPService:
    @staticmethod
    def send_otp(phone_number):
        """
        Generate and send a 6-digit numeric OTP to the phone number.
        Returns (success, message).
        """
        # Ensure user exists for this phone number
        if not User.objects.filter(phone_number=phone_number).exists():
            return False, "This phone number is not registered to any account."

        # Get or create OTP record
        otp_record, created = PhoneOTP.objects.get_or_create(phone_number=phone_number)

        # Check if blocked
        if otp_record.is_blocked():
            remaining_seconds = int((otp_record.blocked_until - timezone.now()).total_seconds())
            remaining_minutes = max(1, remaining_seconds // 60)
            return False, f"Too many failed verification attempts. Blocked. Please try again in {remaining_minutes} minutes."

        # Check resend cooldown limit (60 seconds)
        if not created and otp_record.last_sent and timezone.now() < otp_record.last_sent + timedelta(seconds=60):
            seconds_left = int((otp_record.last_sent + timedelta(seconds=60) - timezone.now()).total_seconds())
            return False, f"Please wait {seconds_left} seconds before resending OTP."

        # Reset failed attempts count if it has been over 10 minutes since the last attempt
        if otp_record.last_sent and timezone.now() > otp_record.last_sent + timedelta(minutes=10):
            otp_record.attempts = 0

        # Generate TOTP using pyotp (interval is 300 seconds = 5 minutes validity)
        totp = pyotp.TOTP(otp_record.otp_secret, interval=300)
        otp = totp.now()

        # Update last_sent timestamp
        otp_record.last_sent = timezone.now()
        otp_record.save()

        # =====================================================================
        # SMS GATEWAY INTEGRATIONS (PLACEHOLDERS)
        # =====================================================================
        # ⚠️ Configure these in production. Do not hardcode API keys.
        #
        # 1. TWILIO INTEGRATION
        # ---------------------
        # from twilio.rest import Client
        # try:
        #     # settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER
        #     client = Client(
        #         getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
        #         getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        #     )
        #     client.messages.create(
        #         body=f"[DocMed] Your login verification OTP code is: {otp}. It will expire in 5 minutes.",
        #         from_=getattr(settings, 'TWILIO_PHONE_NUMBER', ''),
        #         to=phone_number
        #     )
        # except Exception as e:
        #     # Log connection error
        #     pass
        #
        # 2. MSG91 INTEGRATION
        # --------------------
        # import requests
        # try:
        #     # settings.MSG91_API_KEY
        #     payload = {
        #         "template_id": "YOUR_MSG91_TEMPLATE_ID",
        #         "mobile": phone_number,
        #         "authkey": getattr(settings, 'MSG91_API_KEY', ''),
        #         "otp": otp
        #     }
        #     requests.post("https://api.msg91.com/api/v5/otp", json=payload, timeout=10)
        # except Exception:
        #     pass
        #
        # 3. FAST2SMS INTEGRATION
        # -----------------------
        # import requests
        # try:
        #     # settings.FAST2SMS_API_KEY
        #     headers = {
        #         "authorization": getattr(settings, 'FAST2SMS_API_KEY', ''),
        #         "Content-Type": "application/x-www-form-urlencoded"
        #     }
        #     data = {
        #         "variables_values": otp,
        #         "route": "otp",
        #         "numbers": phone_number
        #     }
        #     requests.post("https://www.fast2sms.com/dev/bulkV2", headers=headers, data=data, timeout=10)
        # except Exception:
        #     pass

        # For development purposes, print OTP to console/terminal
        print(f"\n[SMS OTP SERVICE] OTP sent to {phone_number}: {otp}\n")

        return True, "Verification code sent successfully."

    @staticmethod
    def verify_otp(phone_number, otp_code):
        """
        Verify the OTP code for the phone number.
        Returns (success, message).
        """
        try:
            otp_record = PhoneOTP.objects.get(phone_number=phone_number)
        except PhoneOTP.DoesNotExist:
            return False, "OTP code was not requested for this phone number."

        # Check if number is blocked
        if otp_record.is_blocked():
            remaining_seconds = int((otp_record.blocked_until - timezone.now()).total_seconds())
            remaining_minutes = max(1, remaining_seconds // 60)
            return False, f"This number is blocked due to too many failed attempts. Try again in {remaining_minutes} minutes."

        # Initialize TOTP verify object
        totp = pyotp.TOTP(otp_record.otp_secret, interval=300)

        # Verify code (valid_window=1 allows clocks to drift +/- 5 minutes)
        if totp.verify(otp_code, valid_window=1):
            # Success! Reset failed attempts
            otp_record.attempts = 0
            otp_record.save(update_fields=['attempts'])
            return True, "Verification successful."
        else:
            # Increment failed attempts
            otp_record.attempts += 1
            max_attempts = 5
            remaining = max_attempts - otp_record.attempts

            if remaining <= 0:
                # Block phone number for 15 minutes
                otp_record.blocked_until = timezone.now() + timedelta(minutes=15)
                otp_record.save()
                return False, "Too many failed attempts. This phone number has been blocked for 15 minutes."
            else:
                otp_record.save(update_fields=['attempts'])
                return False, f"Invalid verification code. You have {remaining} attempts remaining."
