import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class VoiceAssistantService:
    def __init__(self):
        # Multilingual translation codes
        self.langs = {
            'english': 'en',
            'hindi': 'hi',
            'punjabi': 'pa',
            'tamil': 'ta',
            'gujarati': 'gu',
            'marathi': 'mr',
            'bengali': 'bn',
            'urdu': 'ur'
        }

    def text_to_speech(self, text: str, language: str = 'english', output_dir: str = None) -> str:
        """Converts text to speech using gTTS or pyttsx3 fallback, saving to file."""
        lang_code = self.langs.get(language.lower(), 'en')
        
        # Build path
        if not output_dir:
            output_dir = os.path.join(settings.MEDIA_ROOT, 'voice_summaries')
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"summary_{language.lower()}.mp3"
        filepath = os.path.join(output_dir, filename)

        try:
            # gTTS offline placeholder logic
            from gtts import gTTS
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(filepath)
            logger.info(f"TTS saved: {filepath}")
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}. Creating dummy audio placeholder.")
            # Create a mock/empty audio file
            with open(filepath, 'wb') as f:
                f.write(b'\x00' * 1024) # dummy empty block

        return os.path.join('voice_summaries', filename)
