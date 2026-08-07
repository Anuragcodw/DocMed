"""
ElevenLabs Text-to-Speech (TTS) Service and Django View for DocMed.

Converts prescription instructions, medicine details, and medical notes
into natural speech audio using ElevenLabs API, making them accessible
to patients who prefer listening over reading.

HOW TO CONFIGURE:
  1. Sign up at https://elevenlabs.io/
  2. Get your API key from Profile → API Keys.
  3. Choose a voice ID from the Voices library (or use the default).
  4. Set in .env:
     - ELEVENLABS_API_KEY=your_api_key_here
     - ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM   (Rachel — clear, professional)
     - ELEVENLABS_MODEL_ID=eleven_multilingual_v2   (supports Hindi and other languages)
  5. Set ELEVENLABS_ENABLED=True in .env.

The view returns a base64-encoded MP3 audio string that the frontend plays
directly in the browser without requiring a file download.
"""

import base64
import logging
from typing import Optional

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


# ============================================================================
# ElevenLabs TTS Core Function
# ============================================================================

def text_to_speech(text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
    """
    Convert text to speech audio using ElevenLabs API.

    Args:
        text: The text to convert to speech (max ~2500 chars recommended).
        voice_id: Override the default voice. If None, uses settings.ELEVENLABS_VOICE_ID.

    Returns:
        Audio bytes (MP3 format) if successful, None on failure or when disabled.
    """
    if not getattr(settings, 'ELEVENLABS_ENABLED', False):
        logger.info('[TTS DISABLED] Set ELEVENLABS_ENABLED=True and ELEVENLABS_API_KEY in .env')
        return None

    api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
    if not api_key or api_key in ('', 'YOUR_ELEVENLABS_API_KEY'):
        logger.warning('[TTS] ElevenLabs API key not configured. Set ELEVENLABS_API_KEY in .env')
        return None

    # Default to Rachel voice — clear, professional, suitable for medical context
    effective_voice_id = voice_id or getattr(
        settings, 'ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM'
    )
    model_id = getattr(settings, 'ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2')

    # Sanitize text: strip excessive whitespace and limit length
    text = ' '.join(text.split())
    if len(text) > 5000:
        text = text[:5000] + '...'

    try:
        import requests as req

        url = f'https://api.elevenlabs.io/v1/text-to-speech/{effective_voice_id}'
        headers = {
            'Accept': 'audio/mpeg',
            'Content-Type': 'application/json',
            'xi-api-key': api_key,
        }
        payload = {
            'text': text,
            'model_id': model_id,
            'voice_settings': {
                'stability': 0.6,
                'similarity_boost': 0.8,
                'style': 0.2,
                'use_speaker_boost': True,
            },
        }

        response = req.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            logger.info(f'[TTS] Audio generated successfully ({len(response.content)} bytes).')
            return response.content
        elif response.status_code == 401:
            logger.error('[TTS] ElevenLabs API key invalid (401 Unauthorized).')
        elif response.status_code == 429:
            logger.warning('[TTS] ElevenLabs rate limit hit (429). Try again later.')
        else:
            logger.error(f'[TTS] API error {response.status_code}: {response.text[:200]}')

        return None

    except ImportError:
        logger.error('[TTS] requests library not available.')
        return None
    except Exception as exc:
        logger.error(f'[TTS] Unexpected error: {exc}', exc_info=True)
        return None


# ============================================================================
# Django API View
# ============================================================================

@method_decorator(csrf_protect, name='dispatch')
class TextToSpeechView(LoginRequiredMixin, View):
    """
    POST /api/tts/
    
    Accepts JSON { "text": "..." } and returns base64-encoded MP3 audio
    for in-browser playback. Requires authentication.

    Response (success):
        { "audio_base64": "<base64_mp3_data>", "format": "audio/mpeg" }

    Response (disabled/error):
        { "error": "...", "fallback": true }
    """

    login_url = '/login'

    def post(self, request, *args, **kwargs):
        import json as json_mod

        # Parse JSON body
        try:
            body = json_mod.loads(request.body)
        except (json_mod.JSONDecodeError, AttributeError):
            body = {}

        text = (body.get('text') or request.POST.get('text', '')).strip()

        if not text:
            return JsonResponse({'error': 'No text provided.'}, status=400)

        if len(text) > 5000:
            return JsonResponse(
                {'error': 'Text is too long. Maximum 5000 characters.'}, status=400
            )

        if not getattr(settings, 'ELEVENLABS_ENABLED', False):
            return JsonResponse(
                {
                    'error': 'Text-to-speech is not enabled on this server.',
                    'fallback': True,
                    'tip': 'Set ELEVENLABS_ENABLED=True and ELEVENLABS_API_KEY in .env',
                },
                status=503
            )

        audio_bytes = text_to_speech(text)

        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            return JsonResponse({
                'audio_base64': audio_b64,
                'format': 'audio/mpeg',
                'length_bytes': len(audio_bytes),
            })
        else:
            return JsonResponse(
                {
                    'error': 'Failed to generate audio. Check server logs.',
                    'fallback': True,
                },
                status=500
            )


# ============================================================================
# Prescription Read-Aloud Helper
# ============================================================================

def build_prescription_tts_text(prescription) -> str:
    """
    Build a clean, readable TTS script from a Prescription model instance.

    Args:
        prescription: Prescription model instance with items.

    Returns:
        A formatted string suitable for TTS narration.
    """
    lines = []

    # Header
    try:
        doctor_name = prescription.booking.appointment.full_name
        patient_name = prescription.booking.full_name
        lines.append(f"Prescription for {patient_name}. Doctor: {doctor_name}.")
    except AttributeError:
        lines.append("Prescription details:")

    # Diagnosis
    if hasattr(prescription, 'diagnosis') and prescription.diagnosis:
        lines.append(f"Diagnosis: {prescription.diagnosis}.")

    # Chief complaint
    if hasattr(prescription, 'chief_complaint') and prescription.chief_complaint:
        lines.append(f"Chief complaint: {prescription.chief_complaint}.")

    # Medicines
    items = getattr(prescription, 'items', None)
    if items:
        medicine_items = items.all() if hasattr(items, 'all') else items
        if medicine_items:
            lines.append("Medicines prescribed:")
            for i, item in enumerate(medicine_items, 1):
                med_name = getattr(item, 'medicine_name', 'Unknown Medicine')
                dosage = getattr(item, 'dosage', '')
                frequency = getattr(item, 'frequency', '')
                duration = getattr(item, 'duration', '')
                instructions = getattr(item, 'instructions', '')

                med_line = f"{i}. {med_name}"
                if dosage:
                    med_line += f", {dosage}"
                if frequency:
                    med_line += f", {frequency}"
                if duration:
                    med_line += f" for {duration}"
                if instructions:
                    med_line += f". Instructions: {instructions}"
                lines.append(med_line + ".")

    # Doctor notes
    if hasattr(prescription, 'notes') and prescription.notes:
        lines.append(f"Doctor's notes: {prescription.notes}.")

    # Follow-up
    if hasattr(prescription, 'follow_up_date') and prescription.follow_up_date:
        lines.append(f"Follow-up appointment: {prescription.follow_up_date.strftime('%B %d, %Y')}.")

    return ' '.join(lines)
