"""
Firebase Admin SDK Service Module for DocMed

Provides token verification and user lookup helpers.
"""

import json
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_initialized = False

def initialize_firebase():
    """
    Initialize Firebase Admin SDK lazily.
    Supports FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH.
    """
    global _firebase_initialized
    if _firebase_initialized:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check if already initialized in app registry
        if firebase_admin._apps:
            _firebase_initialized = True
            return True

        service_account_json = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', '').strip()
        service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_PATH', '').strip()

        cred = None
        if service_account_json:
            try:
                cert_dict = json.loads(service_account_json)
                cred = credentials.Certificate(cert_dict)
            except Exception as e:
                logger.error(f"[FIREBASE] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

        if not cred and service_account_path and os.path.exists(service_account_path):
            try:
                cred = credentials.Certificate(service_account_path)
            except Exception as e:
                logger.error(f"[FIREBASE] Failed to load FIREBASE_SERVICE_ACCOUNT_PATH: {e}")

        if cred:
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("[FIREBASE] Admin SDK initialized successfully with credentials.")
            return True
        else:
            # Fallback initialization for default environment or uncredentialed verification
            try:
                firebase_admin.initialize_app()
                _firebase_initialized = True
                logger.info("[FIREBASE] Admin SDK initialized with default application credentials.")
                return True
            except Exception as e:
                logger.warning(f"[FIREBASE] Admin SDK initialization pending credentials: {e}")
                return False

    except ImportError:
        logger.error("[FIREBASE] firebase-admin package is not installed.")
        return False
    except Exception as e:
        logger.error(f"[FIREBASE] Unexpected initialization error: {e}")
        return False


def verify_firebase_id_token(id_token):
    """
    Verify Firebase ID Token signature and payload.

    Returns:
        dict: {
            'success': True/False,
            'uid': str,
            'email': str or None,
            'phone_number': str or None,
            'name': str or None,
            'picture': str or None,
            'error': str or None
        }
    """
    if not id_token or not isinstance(id_token, str):
        return {'success': False, 'error': 'Missing or invalid token format.'}

    initialized = initialize_firebase()

    try:
        import firebase_admin
        from firebase_admin import auth

        # If Firebase Admin SDK is initialized, verify ID Token cryptographically
        if initialized and firebase_admin._apps:
            decoded_token = auth.verify_id_token(id_token, check_revoked=False)
            uid = decoded_token.get('uid')
            email = decoded_token.get('email')
            phone_number = decoded_token.get('phone_number')
            name = decoded_token.get('name')
            picture = decoded_token.get('picture')

            # Extract firebase user info if available
            firebase_info = decoded_token.get('firebase', {})
            identities = firebase_info.get('identities', {})

            if not email and 'email' in identities and identities['email']:
                email = identities['email'][0]
            if not phone_number and 'phone' in identities and identities['phone']:
                phone_number = identities['phone'][0]

            return {
                'success': True,
                'uid': uid,
                'email': email.lower() if email else None,
                'phone_number': phone_number,
                'name': name,
                'picture': picture,
                'decoded_token': decoded_token,
            }
        else:
            # Development / Mock Fallback mode when Firebase Service Account is not configured in local environment
            if settings.DEBUG:
                logger.warning("[FIREBASE] Service Account credentials not provided. Attempting dev token parsing.")
                # Attempt unverified payload decoding for local testing if valid JWT format
                try:
                    import jwt
                    unverified_payload = jwt.decode(id_token, options={"verify_signature": False})
                    uid = unverified_payload.get('user_id') or unverified_payload.get('uid') or unverified_payload.get('sub')
                    email = unverified_payload.get('email')
                    phone_number = unverified_payload.get('phone_number')
                    name = unverified_payload.get('name')
                    picture = unverified_payload.get('picture')

                    if uid:
                        return {
                            'success': True,
                            'uid': uid,
                            'email': email.lower() if email else None,
                            'phone_number': phone_number,
                            'name': name,
                            'picture': picture,
                            'decoded_token': unverified_payload,
                        }
                except Exception as parse_err:
                    logger.error(f"[FIREBASE] Unverified payload parse failed: {parse_err}")

            return {
                'success': False,
                'error': 'Firebase Admin SDK credentials not configured on server. Please set FIREBASE_SERVICE_ACCOUNT_JSON.'
            }

    except Exception as exc:
        logger.error(f"[FIREBASE] ID token verification failed: {exc}")
        return {
            'success': False,
            'error': f'Firebase authentication failed: {str(exc)}'
        }
