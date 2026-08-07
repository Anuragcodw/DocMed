"""
Google Translate API + Multi-Language Support for DocMed.

Provides a Django REST API endpoint for on-demand text translation,
plus utilities for the language selector UI.

Supports 12 languages for the DocMed healthcare platform:
  English, Hindi, Bengali, Telugu, Marathi, Tamil, Gujarati,
  Kannada, Malayalam, Punjabi, Urdu, and Odia.

HOW TO CONFIGURE:
  1. Go to Google Cloud Console → APIs & Services → Enable "Cloud Translation API".
  2. Create an API Key and restrict it to the Cloud Translation API.
  3. Set in .env:
     - GOOGLE_TRANSLATE_API_KEY=your_api_key_here
  4. Set GOOGLE_TRANSLATE_ENABLED=True in .env.

Without credentials, the view returns the original text unchanged (graceful fallback).
"""

import logging
from typing import Optional

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


# ============================================================================
# Supported Languages
# ============================================================================

SUPPORTED_LANGUAGES = [
    {'code': 'en', 'name': 'English',    'native': 'English',    'flag': '🇬🇧'},
    {'code': 'hi', 'name': 'Hindi',      'native': 'हिन्दी',     'flag': '🇮🇳'},
    {'code': 'bn', 'name': 'Bengali',    'native': 'বাংলা',       'flag': '🇧🇩'},
    {'code': 'te', 'name': 'Telugu',     'native': 'తెలుగు',      'flag': '🇮🇳'},
    {'code': 'mr', 'name': 'Marathi',    'native': 'मराठी',       'flag': '🇮🇳'},
    {'code': 'ta', 'name': 'Tamil',      'native': 'தமிழ்',       'flag': '🇮🇳'},
    {'code': 'gu', 'name': 'Gujarati',   'native': 'ગુજરાતી',     'flag': '🇮🇳'},
    {'code': 'kn', 'name': 'Kannada',    'native': 'ಕನ್ನಡ',       'flag': '🇮🇳'},
    {'code': 'ml', 'name': 'Malayalam',  'native': 'മലയാളം',      'flag': '🇮🇳'},
    {'code': 'pa', 'name': 'Punjabi',    'native': 'ਪੰਜਾਬੀ',      'flag': '🇮🇳'},
    {'code': 'ur', 'name': 'Urdu',       'native': 'اردو',        'flag': '🇵🇰'},
    {'code': 'or', 'name': 'Odia',       'native': 'ଓଡ଼ିଆ',       'flag': '🇮🇳'},
]

SUPPORTED_LANGUAGE_CODES = {lang['code'] for lang in SUPPORTED_LANGUAGES}


# ============================================================================
# Core Translation Function
# ============================================================================

def translate_text(text: str, target_lang: str, source_lang: str = 'en') -> Optional[str]:
    """
    Translate text using the Google Cloud Translation API (v2 / Basic).

    Args:
        text: Text to translate.
        target_lang: Target language code (e.g. 'hi', 'ta').
        source_lang: Source language code. Defaults to 'en'.

    Returns:
        Translated text string, or None on failure.
    """
    if not getattr(settings, 'GOOGLE_TRANSLATE_ENABLED', False):
        logger.info('[Translate DISABLED] Set GOOGLE_TRANSLATE_ENABLED=True in .env')
        return None

    api_key = getattr(settings, 'GOOGLE_TRANSLATE_API_KEY', '')
    if not api_key or api_key in ('', 'YOUR_GOOGLE_TRANSLATE_API_KEY'):
        logger.warning('[Translate] API key not configured. Set GOOGLE_TRANSLATE_API_KEY in .env')
        return None

    if target_lang == source_lang:
        return text  # No translation needed

    if not text or not text.strip():
        return text

    try:
        import requests as req

        url = 'https://translation.googleapis.com/language/translate/v2'
        params = {
            'q': text,
            'source': source_lang,
            'target': target_lang,
            'format': 'text',
            'key': api_key,
        }

        response = req.post(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            translated = data['data']['translations'][0]['translatedText']
            return translated
        elif response.status_code == 400:
            logger.error(f'[Translate] Bad request (400): {response.text[:200]}')
        elif response.status_code == 403:
            logger.error('[Translate] API key invalid or Translation API not enabled (403).')
        else:
            logger.error(f'[Translate] API error {response.status_code}: {response.text[:200]}')

        return None

    except ImportError:
        logger.error('[Translate] requests library not available.')
        return None
    except Exception as exc:
        logger.error(f'[Translate] Unexpected error: {exc}', exc_info=True)
        return None


# ============================================================================
# Django API View
# ============================================================================

@method_decorator(csrf_protect, name='dispatch')
class TranslateTextView(View):
    """
    POST /api/translate/

    Accepts JSON { "text": "...", "target_lang": "hi" }
    Returns { "translated_text": "...", "target_lang": "hi", "original": "..." }

    No authentication required (translation is a public utility).
    """

    def post(self, request, *args, **kwargs):
        import json as json_mod

        try:
            body = json_mod.loads(request.body)
        except (json_mod.JSONDecodeError, AttributeError):
            body = {}

        text = (body.get('text') or request.POST.get('text', '')).strip()
        target_lang = (body.get('target_lang') or request.POST.get('target_lang', 'en')).strip()
        source_lang = (body.get('source_lang') or request.POST.get('source_lang', 'en')).strip()

        if not text:
            return JsonResponse({'error': 'No text provided.'}, status=400)

        if target_lang not in SUPPORTED_LANGUAGE_CODES:
            return JsonResponse(
                {'error': f'Unsupported target language: {target_lang}'},
                status=400
            )

        # Return original if same language or Translation disabled
        if target_lang == 'en' or target_lang == source_lang:
            return JsonResponse({
                'translated_text': text,
                'target_lang': target_lang,
                'original': text,
                'fallback': True,
            })

        translated = translate_text(text, target_lang, source_lang)

        if translated:
            return JsonResponse({
                'translated_text': translated,
                'target_lang': target_lang,
                'original': text,
                'fallback': False,
            })
        else:
            # Graceful fallback — return original text unchanged
            return JsonResponse({
                'translated_text': text,
                'target_lang': target_lang,
                'original': text,
                'fallback': True,
                'note': 'Translation service unavailable. Showing original text.',
            })


class LanguageListView(View):
    """
    GET /api/languages/

    Returns the list of supported languages for the language selector UI.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'languages': SUPPORTED_LANGUAGES,
            'default': 'en',
        })
