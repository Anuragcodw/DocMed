"""
NMC (National Medical Commission) Verification Service
=======================================================

This module provides a clean interface for verifying doctors against the
National Medical Commission (NMC) of India. Currently implemented as
manual-verification stubs; designed to be upgraded to live integrations:

  - NMC Public Registry API  (https://www.nmc.org.in)
  - DigiLocker Document Verification API
  - QR-code based medical license scanning
  - License auto-expiry monitoring

Usage:
    from accounts.nmc_service import NMCVerificationService

    result = NMCVerificationService.verify_registration_number("MH/12345/2020")
    if result['valid']:
        ...
"""
import re
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Regex pattern accepted by NMC for registration numbers.
# Format examples: MH/12345/2020  |  DL-56789-2019  |  123456
NMC_NUMBER_PATTERN = re.compile(
    r'^[A-Z]{2,5}[-/]?\d{4,10}[-/]?\d{0,4}$',
    re.IGNORECASE
)

# Supported state medical councils mapped to their abbreviation codes
STATE_MEDICAL_COUNCILS = {
    'Andhra Pradesh Medical Council': 'APMC',
    'Assam Medical Council': 'AMC',
    'Bihar Medical Council': 'BMC',
    'Chhattisgarh Medical Council': 'CGMC',
    'Delhi Medical Council': 'DMC',
    'Goa Medical Council': 'GMC',
    'Gujarat Medical Council': 'GUMC',
    'Haryana Medical Council': 'HMC',
    'Himachal Pradesh Medical Council': 'HPMC',
    'Jammu & Kashmir Medical Council': 'JKMC',
    'Jharkhand Medical Council': 'JKMC2',
    'Karnataka Medical Council': 'KMC',
    'Kerala Medical Council': 'KEMC',
    'Madhya Pradesh Medical Council': 'MPMC',
    'Maharashtra Medical Council': 'MMC',
    'Manipur Medical Council': 'MNMC',
    'Meghalaya Medical Council': 'MGMC',
    'Odisha Council of Medical Registration': 'OCMR',
    'Punjab Medical Council': 'PMC',
    'Rajasthan Medical Council': 'RMC',
    'Tamil Nadu Medical Council': 'TNMC',
    'Telangana State Medical Council': 'TSMC',
    'Uttar Pradesh Medical Council': 'UPMC',
    'Uttarakhand Medical Council': 'UKMC',
    'West Bengal Medical Council': 'WBMC',
    'Medical Council of India': 'MCI',
    'National Medical Commission': 'NMC',
}

VALID_REGISTRATION_YEAR_MIN = 1950
VALID_REGISTRATION_YEAR_MAX = 2030


# ---------------------------------------------------------------------------
# Service Class
# ---------------------------------------------------------------------------

class NMCVerificationService:
    """
    Stateless service for NMC credential validation.

    All public methods return a dict with at minimum:
        {
            'valid': bool,
            'message': str,
            'data': dict | None   # enriched data on success
        }
    """

    # ------------------------------------------------------------------ #
    # 1. FORMAT VALIDATION (client-side & server-side)                    #
    # ------------------------------------------------------------------ #

    @classmethod
    def validate_nmc_format(cls, nmc_number: str) -> dict:
        """
        Validate that the NMC registration number matches the expected
        format without making any external API call.

        Args:
            nmc_number: Raw string input from the doctor registration form.

        Returns:
            dict with keys: valid (bool), message (str)
        """
        if not nmc_number or not nmc_number.strip():
            return {
                'valid': False,
                'message': 'NMC Registration Number is required.',
            }

        nmc_clean = nmc_number.strip().upper()

        if len(nmc_clean) < 5:
            return {
                'valid': False,
                'message': 'NMC Registration Number is too short. Minimum 5 characters.',
            }

        if len(nmc_clean) > 50:
            return {
                'valid': False,
                'message': 'NMC Registration Number is too long. Maximum 50 characters.',
            }

        # Allow alphanumeric with optional separators (-, /)
        if not re.match(r'^[A-Za-z0-9/\-]+$', nmc_clean):
            return {
                'valid': False,
                'message': 'NMC Registration Number may only contain letters, digits, hyphens, and forward slashes.',
            }

        return {
            'valid': True,
            'message': 'NMC Registration Number format is valid.',
        }

    @classmethod
    def validate_registration_year(cls, year: int) -> dict:
        """
        Validate that the medical council registration year is within
        an acceptable range.
        """
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            return {
                'valid': False,
                'message': 'Registration year must be a 4-digit number.',
            }

        if year_int < VALID_REGISTRATION_YEAR_MIN or year_int > VALID_REGISTRATION_YEAR_MAX:
            return {
                'valid': False,
                'message': (
                    f'Registration year must be between {VALID_REGISTRATION_YEAR_MIN} '
                    f'and {VALID_REGISTRATION_YEAR_MAX}.'
                ),
            }

        return {'valid': True, 'message': 'Registration year is valid.'}

    # ------------------------------------------------------------------ #
    # 2. UNIQUENESS CHECK (database)                                      #
    # ------------------------------------------------------------------ #

    @classmethod
    def check_nmc_uniqueness(cls, nmc_number: str, exclude_profile_id: int = None) -> dict:
        """
        Check that the NMC Registration Number is not already used by another
        doctor in the database.

        Args:
            nmc_number:        The NMC number to check.
            exclude_profile_id: DoctorProfile pk to exclude (for edit flows).

        Returns:
            dict with keys: valid (bool), message (str)
        """
        from appointment.models import DoctorProfile  # late import to avoid circular deps

        nmc_clean = nmc_number.strip().upper() if nmc_number else ''
        if not nmc_clean:
            return {'valid': False, 'message': 'NMC Registration Number is required.'}

        qs = DoctorProfile.objects.filter(nmc_registration_number__iexact=nmc_clean)
        if exclude_profile_id:
            qs = qs.exclude(pk=exclude_profile_id)

        if qs.exists():
            return {
                'valid': False,
                'message': (
                    'This NMC Registration Number is already registered in our system. '
                    'If you believe this is an error, contact admin@docmed.in.'
                ),
            }

        return {
            'valid': True,
            'message': 'NMC Registration Number is available.',
        }

    # ------------------------------------------------------------------ #
    # 3. LIVE NMC REGISTRY LOOKUP (STUB — ready for API integration)     #
    # ------------------------------------------------------------------ #

    @classmethod
    def verify_with_nmc_registry(cls, nmc_number: str, council: str = None, year: int = None) -> dict:
        """
        [STUB] Verify NMC registration number against the live NMC public registry.

        This method is currently a stub that returns a 'pending manual review'
        result. Replace the body with a real HTTP call to the NMC API when the
        live endpoint becomes available (https://www.nmc.org.in/information-desk/
        for-medical-practitioners/nmc-registration/).

        Future integration options:
          - NMC REST API (OAuth2 token-based)
          - DigiLocker Issued Documents API (Aadhaar-linked)
          - NMC QR Code scanning for physical certificates

        Args:
            nmc_number: NMC registration number to verify.
            council:    State medical council (optional, improves lookup accuracy).
            year:       Registration year (optional).

        Returns:
            dict with keys:
                valid (bool):    True if doctor is found in registry,
                                 False if definitively not found.
                pending (bool):  True if the check is inconclusive / API unavailable.
                message (str):   Human-readable result.
                data (dict):     Doctor details from registry (if available).
        """
        logger.info(
            "NMC registry lookup requested for '%s' (council=%s, year=%s). "
            "Live API not yet integrated — returning pending-manual-review.",
            nmc_number, council, year,
        )

        # ----------------------------------------------------------------
        # TODO: Replace this stub with live NMC API call.
        #
        # Example implementation sketch:
        #
        #   import requests
        #   response = requests.post(
        #       'https://api.nmc.org.in/v1/verify',
        #       json={
        #           'registration_number': nmc_number,
        #           'council': council,
        #           'year': year,
        #       },
        #       headers={'Authorization': f'Bearer {settings.NMC_API_TOKEN}'},
        #       timeout=10,
        #   )
        #   if response.ok:
        #       data = response.json()
        #       return {
        #           'valid': data.get('status') == 'ACTIVE',
        #           'pending': False,
        #           'message': data.get('message', ''),
        #           'data': data,
        #       }
        # ----------------------------------------------------------------

        return {
            'valid': False,
            'pending': True,
            'message': (
                'NMC live registry integration is not yet active. '
                'This doctor\'s credentials will be verified manually by our admin team.'
            ),
            'data': None,
            'verification_method': 'manual',
        }

    # ------------------------------------------------------------------ #
    # 4. DIGILOCKER DOCUMENT VERIFICATION (STUB)                         #
    # ------------------------------------------------------------------ #

    @classmethod
    def verify_via_digilocker(cls, aadhaar_number: str, doc_type: str = 'MBBS') -> dict:
        """
        [STUB] Verify medical certificates via DigiLocker issued documents.

        Replace with DigiLocker Partner API integration when credentials
        are obtained from DigiLocker (https://partners.digitallocker.gov.in/).

        Args:
            aadhaar_number: 12-digit Aadhaar number (masked for PII safety).
            doc_type: Document type to verify ('MBBS', 'MD', 'Registration').

        Returns:
            dict with valid (bool), pending (bool), message (str), data (dict|None)
        """
        logger.info(
            "DigiLocker verification stub called for doc_type=%s. Not yet integrated.",
            doc_type,
        )
        return {
            'valid': False,
            'pending': True,
            'message': 'DigiLocker integration not yet active. Manual review will be performed.',
            'data': None,
            'verification_method': 'manual',
        }

    # ------------------------------------------------------------------ #
    # 5. COMPREHENSIVE VALIDATE-ALL (used in registration form)          #
    # ------------------------------------------------------------------ #

    @classmethod
    def run_all_validations(cls, nmc_number: str, council: str = None,
                             year: int = None, exclude_profile_id: int = None) -> dict:
        """
        Run all available validations and return a combined result.
        Designed to be called from the doctor registration form POST handler.

        Returns:
            dict with:
                all_valid (bool): True only if all checks pass.
                errors (list[str]): List of error messages.
                warnings (list[str]): Non-blocking warnings (e.g. live API unavailable).
                verification_method (str): 'manual', 'nmc_api', etc.
        """
        errors = []
        warnings = []

        # Step 1: Format check
        fmt = cls.validate_nmc_format(nmc_number)
        if not fmt['valid']:
            errors.append(fmt['message'])
            return {'all_valid': False, 'errors': errors, 'warnings': warnings, 'verification_method': 'manual'}

        # Step 2: Year check
        if year is not None:
            yr = cls.validate_registration_year(year)
            if not yr['valid']:
                errors.append(yr['message'])

        # Step 3: Uniqueness check
        uniq = cls.check_nmc_uniqueness(nmc_number, exclude_profile_id=exclude_profile_id)
        if not uniq['valid']:
            errors.append(uniq['message'])

        if errors:
            return {'all_valid': False, 'errors': errors, 'warnings': warnings, 'verification_method': 'manual'}

        # Step 4: Live registry lookup (stub — non-blocking)
        live = cls.verify_with_nmc_registry(nmc_number, council=council, year=year)
        if live.get('pending'):
            warnings.append(live['message'])

        return {
            'all_valid': True,
            'errors': [],
            'warnings': warnings,
            'verification_method': live.get('verification_method', 'manual'),
        }
