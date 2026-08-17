"""
ElevenLabs Text-to-Speech (TTS) Service for DocMed AI Assistant.

Handles natural voice synthesis for multilingual AI responses using the ElevenLabs HTTP API v1.
If ELEVENLABS_API_KEY is not configured or an error occurs, returns None so that
the frontend seamlessly falls back to the browser's native Web Speech API.
"""

import os
import logging
import requests
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = getattr(settings, 'ELEVENLABS_API_KEY', os.environ.get('ELEVENLABS_API_KEY', ''))
ELEVENLABS_VOICE_ID = getattr(settings, 'ELEVENLABS_VOICE_ID', os.environ.get('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM'))  # Default Rachel voice

# Standard language code to ElevenLabs model mapping
# eleven_multilingual_v2 supports English, Hindi, French, German, Spanish, Portuguese, Chinese, Japanese, etc.
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


class ElevenLabsService:
    """
    Service wrapper for ElevenLabs TTS API v1.
    Backend-only: API key is never exposed to the frontend.
    """

    def __init__(self, voice_id: Optional[str] = None):
        self.api_key = getattr(settings, 'ELEVENLABS_API_KEY', os.environ.get('ELEVENLABS_API_KEY', ''))
        self.voice_id = voice_id or getattr(settings, 'ELEVENLABS_VOICE_ID', os.environ.get('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM'))
        self.api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"

    def generate_speech(self, text: str, language_code: str = 'en') -> Optional[bytes]:
        """
        Synthesizes text into MP3 audio bytes using ElevenLabs.

        Args:
            text: The text string to speak.
            language_code: Language code (e.g. 'en', 'hi', 'pa', 'ur', 'fr', 'es').

        Returns:
            MP3 audio bytes if successful, or None if unavailable/error.
        """
        if not self.api_key or self.api_key in ('YOUR_ELEVENLABS_API_KEY', ''):
            logger.debug("[ElevenLabs] API key not configured. Standing by for browser SpeechSynthesis fallback.")
            return None

        if not text or not text.strip():
            return None

        # Clean markdown formatting characters before sending to TTS
        clean_text = (
            text.replace('**', '')
                .replace('*', '')
                .replace('#', '')
                .replace('_', '')
                .replace('`', '')
                .strip()
        )
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000]  # Limit length for speed & quota safety

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        payload = {
            "text": clean_text,
            "model_id": DEFAULT_MODEL_ID,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200 and response.content:
                logger.info(f"[ElevenLabs] Generated {len(response.content)} bytes of MP3 audio for lang '{language_code}'.")
                return response.content
            else:
                logger.warning(f"[ElevenLabs] HTTP {response.status_code}: {response.text[:200]}")
                return None
        except Exception as exc:
            logger.error(f"[ElevenLabs] Exception generating speech: {exc}")
            return None
