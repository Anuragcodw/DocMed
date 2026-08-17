"""
Gemini AI client using the current google-genai SDK or legacy google-generativeai SDK.

CONFIGURE: Set GEMINI_API_KEY in .env
Get a free key from: https://aistudio.google.com/app/apikey
"""
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))
_genai = None  # Lazy-loaded module
_cached_client = None  # Reusable singleton client instance


def _get_genai():
    """Lazy-load the google.genai or google.generativeai SDK."""
    global _genai
    if _genai is not None:
        return _genai
    
    api_key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))
    if not api_key or api_key in ('YOUR_GEMINI_API_KEY', ''):
        return None
        
    try:
        # Modern SDK
        import google.genai as genai  # type: ignore[import]
        _genai = genai
    except ImportError:
        try:
            # Fallback legacy SDK
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', FutureWarning)
                import google.generativeai as genai  # type: ignore[import]
            _genai = genai
        except ImportError:
            logger.warning('Neither google-genai nor google-generativeai is installed.')
            return None
    return _genai


class GeminiClient:
    """Singleton-friendly wrapper around Google Gemini API with robust fallbacks."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or getattr(settings, 'GEMINI_MODEL', os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash'))
        self._client = None

    def get_client(self):
        """Retrieve or initialize the cached Gemini client instance (only once)."""
        global _cached_client
        if _cached_client is not None:
            return _cached_client
            
        genai = _get_genai()
        if genai is None:
            return None
            
        api_key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))
        if not api_key or api_key in ('YOUR_GEMINI_API_KEY', ''):
            return None

        try:
            if hasattr(genai, 'Client'):
                _cached_client = genai.Client(api_key=api_key)
            else:
                genai.configure(api_key=api_key)
                _cached_client = genai.GenerativeModel(self.model_name)
            return _cached_client
        except Exception as e:
            logger.error(f'Failed to initialize Gemini client: {e}')
            return None

    def _fallback_generate_content(self, prompt: str, context: str = '') -> str:
        """High-quality rule-based medical fallback when live API is unavailable."""
        prompt_lower = prompt.lower()
        
        # 1. Greetings & general chatbot questions
        if any(w in prompt_lower for w in ['hello', 'hi', 'hey', 'greetings', 'namaste']):
            return (
                "Hello! 👋 Welcome to DocMed's AI Healthcare Assistant. How can I help you today? "
                "I can help you understand symptoms, answer general health queries, "
                "or assist you with navigating our doctor appointment booking system.\n\n"
                "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
            )
        
        # 2. Who are you
        if any(w in prompt_lower for w in ['who are you', 'your name', 'what is your role', 'what are you']):
            return (
                "I am DocMed's AI Healthcare Assistant. 🏥 I am designed to assist you with medical inquiries, "
                "symptom checking, and appointment booking. Remember, I am an AI, so please consult a licensed doctor "
                "for clinical diagnosis and treatment.\n\n"
                "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
            )
            
        # 3. Symptoms checking / disease prediction
        symptoms_map = {
            'chest pain': "Chest pain can indicate a serious cardiac event (like Angina or Myocardial Infarction). Please seek emergency medical help immediately. Avoid physical exertion and stay calm.",
            'breathing': "Difficulty breathing or shortness of breath can point to conditions like Asthma, COPD, Pneumonia, or Heart Failure. This requires immediate medical evaluation.",
            'headache': "Headaches can be caused by tension, migraines, dehydration, or high blood pressure. Drink water, rest in a quiet dark room, and monitor your blood pressure. If it is sudden and severe, seek medical care.",
            'vision': "Blurry vision might be related to cataracts, refractive errors, or diabetic retinopathy. Please consult an ophthalmologist (Eye Care specialist) for a comprehensive eye exam.",
            'tooth': "Toothaches are typically due to dental cavities, pulpitis, or an abscess. Please schedule an appointment with a dentist (Dentistry) for proper treatment.",
            'sore throat': "A sore throat is commonly due to pharyngitis, tonsillitis, or laryngitis. Warm fluids, salt water gargles, and throat lozenges can help. Consult an ENT specialist if it persists.",
            'joint pain': "Joint pain can stem from arthritis, sprains, or gout. Resting the joint, applying cold/warm compresses, and gentle stretching can provide relief. Consult a Physical Therapy or Orthopedics specialist.",
            'fever': "Fever is often your body's response to an infection. Stay hydrated, rest, and use over-the-counter fever reducers if needed. Seek medical attention if it exceeds 103°F (39.4°C) or lasts more than 3 days.",
            'cough': "A persistent cough might indicate bronchitis, respiratory infection, or allergies. Keep hydrated and use throat lozenges. Consult a General Physician if accompanied by fever or breathing difficulty."
        }
        
        matched_symptoms = []
        for sym, advice in symptoms_map.items():
            if sym in prompt_lower:
                matched_symptoms.append(advice)
                
        if matched_symptoms:
            return "Based on your description:\n\n" + "\n\n".join(matched_symptoms) + "\n\nDisclaimer: This information is for educational purposes and does not replace professional medical advice."
            
        # 4. Appointments or booking
        if any(w in prompt_lower for w in ['book', 'appointment', 'schedule', 'doctor', 'visit', 'consult']):
            return (
                "To book an appointment, you can navigate to the 'Find Your Specialist' section on the homepage, "
                "select a department or search for a doctor, and click 'Book Appointment' or use the Booking Wizard. "
                "Our system allows you to select convenient slots, choose payment options, and manage your bookings.\n\n"
                "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
            )
            
        # 5. Generic medical/health question fallback
        return (
            "I understand you have a health-related query. While our live AI service is operating in safe fallback mode, "
            "I recommend consulting with a certified healthcare professional on DocMed for personalized medical advice. "
            "Please let me know if you would like me to help you find a doctor on our platform.\n\n"
            "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
        )

    def generate_content(self, prompt: str, context: str = '', system_instruction: str = '') -> str:
        """Generate text content with lazy client reuse and fallback safety."""
        if not prompt or not prompt.strip():
            return "Please provide a valid query."

        client = self.get_client()
        if client is None:
            return self._fallback_generate_content(prompt, context)

        try:
            genai_mod = _get_genai()
            if hasattr(genai_mod, 'Client'):
                # Modern google-genai SDK
                config = None
                if system_instruction:
                    try:
                        from google.genai import types
                        config = types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                    except Exception as cfg_err:
                        logger.debug(f"GenerateContentConfig note: {cfg_err}")

                prompt_content = f"{prompt.strip()}\n\nContext:\n{context.strip()}" if context else prompt.strip()

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_content,
                    config=config,
                )
                return response.text or self._fallback_generate_content(prompt, context)
            else:
                # Legacy google-generativeai SDK fallback
                full_prompt = prompt.strip()
                if system_instruction:
                    full_prompt = f'{system_instruction.strip()}\n\n{full_prompt}'
                if context:
                    full_prompt += f'\n\nContext:\n{context.strip()}'
                response = client.generate_content(full_prompt)
                return response.text or self._fallback_generate_content(prompt, context)
        except Exception as e:
            logger.error(f'Gemini generate_content API error: {e}')
            return self._fallback_generate_content(prompt, context)

    def translate_text(self, english_text: str, target_language_name: str) -> str:
        """
        Translates an already-generated English AI response into the specified target language using Gemini API.

        Args:
            english_text: The primary English AI response text.
            target_language_name: Full name of the target language (e.g., 'Hindi', 'Punjabi', 'French').

        Returns:
            The translated text string preserving medical disclaimers and safety warnings.
        """
        if not english_text or not english_text.strip():
            return ""

        if target_language_name.lower() in ('english', 'en'):
            return english_text

        translation_system_prompt = (
            f"You are a professional medical translator. Translate the following English medical response into {target_language_name}.\n"
            "STRICT RULES:\n"
            "1. Preserve the exact meaning of the original English text without adding, altering, or omitting details.\n"
            "2. Translate all medical disclaimers, emergency care warnings, and advice accurately into natural, clear "
            f"{target_language_name}.\n"
            "3. Do NOT claim to be a licensed doctor.\n"
            "4. Return ONLY the translated response text without extra conversational commentary."
        )

        try:
            translation = self.generate_content(
                prompt=f"Translate this text to {target_language_name}:\n\n{english_text}",
                system_instruction=translation_system_prompt
            )
            if translation and translation.strip():
                return translation.strip()
        except Exception as exc:
            logger.error(f"[GeminiClient] Translation error to {target_language_name}: {exc}")

        return english_text

    def get_embeddings(self, text: str, model: str = 'models/text-embedding-004') -> list:
        """Return embedding vector. Returns empty list if AI is unavailable."""
        genai_mod = _get_genai()
        if genai_mod is None:
            return []
        api_key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))
        if not api_key:
            return []
        try:
            if hasattr(genai_mod, 'Client'):
                client = genai_mod.Client(api_key=api_key)
                result = client.models.embed_content(model=model, contents=text)
                return result.embeddings[0].values if result.embeddings else []
            else:
                genai_mod.configure(api_key=api_key)
                result = genai_mod.embed_content(
                    model=model,
                    content=text,
                    task_type='retrieval_document',
                )
                return result['embedding']
        except Exception as e:
            logger.error(f'Embedding error: {e}')
            return []


# Global singleton instance for easy reuse
_gemini_instance = GeminiClient()

def generate_response(message: str) -> str:
    """Reusable top-level helper function to generate AI responses."""
    return _gemini_instance.generate_content(prompt=message)

