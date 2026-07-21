"""
Gemini AI client using the current google-genai SDK.

CONFIGURE: Set GEMINI_API_KEY in .env
Get a free key from: https://aistudio.google.com/app/apikey
"""
import os
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))
_genai = None  # Lazy-loaded so missing key never crashes startup


def _get_genai():
    """Lazy-load the google.genai SDK only when we have a key."""
    global _genai
    if _genai is not None:
        return _genai
    if not GEMINI_API_KEY or GEMINI_API_KEY in ('YOUR_GEMINI_API_KEY', ''):
        return None
    try:
        # Use the modern google-genai package (not the deprecated google.generativeai)
        import google.genai as genai  # type: ignore[import]
        _genai = genai
    except ImportError:
        try:
            # Fallback: suppress FutureWarning from legacy package
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', FutureWarning)
                import google.generativeai as genai  # type: ignore[import]  # noqa: F811
            _genai = genai
        except ImportError:
            logger.warning('Neither google-genai nor google-generativeai is installed.')
            return None
    return _genai


class GeminiClient:
    """Thin wrapper around Google Gemini API with graceful fallback."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')

    def _make_model(self):
        genai = _get_genai()
        if genai is None:
            return None
        try:
            if hasattr(genai, 'Client'):
                # New SDK: google-genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                return client
            else:
                # Legacy SDK: google-generativeai
                genai.configure(api_key=GEMINI_API_KEY)
                return genai.GenerativeModel(self.model_name)
        except Exception as e:
            logger.error(f'Failed to initialise Gemini model: {e}')
            return None

    def _fallback_generate_content(self, prompt: str, context: str = '') -> str:
        prompt_lower = prompt.lower()
        
        # 1. Greetings & general chatbot questions
        if any(w in prompt_lower for w in ['hello', 'hi', 'hey', 'greetings', 'namaste']):
            return (
                "Hello! I am DocMed's AI Healthcare Assistant. How can I help you today? "
                "I can help you understand symptoms, answer general health queries, "
                "or assist you with navigating our doctor appointment booking system.\n\n"
                "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
            )
        
        # 2. Who are you
        if "who are you" in prompt_lower or "your name" in prompt_lower or "what is your role" in prompt_lower:
            return (
                "I am DocMed's AI Healthcare Assistant. I am designed to assist you with medical inquiries, "
                "symptom checking, and booking navigation. Remember, I am an AI, so please consult a licensed doctor "
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
            "I understand you have a health-related query. While I am training to analyze complex medical questions, "
            "I recommend sharing more details or checking our RAG Medical Knowledge Base. For any specific symptoms, "
            "it is always best to consult with a certified healthcare professional. "
            "Please let me know if you would like me to help you find a doctor in our platform.\n\n"
            "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
        )

    def generate_content(self, prompt: str, context: str = '', system_instruction: str = '') -> str:
        """Generate text content. Returns high-quality fallback if AI is unavailable."""
        full_prompt = prompt
        if system_instruction:
            full_prompt = f'{system_instruction}\n\n{full_prompt}'
        if context:
            full_prompt += f'\n\nContext:\n{context}'

        model = self._make_model()
        if model is None:
            return self._fallback_generate_content(prompt, context)

        try:
            genai_mod = _get_genai()
            if hasattr(genai_mod, 'Client'):
                # New SDK path
                response = model.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                )
                return response.text or self._fallback_generate_content(prompt, context)
            else:
                # Legacy SDK path
                response = model.generate_content(full_prompt)
                return response.text or self._fallback_generate_content(prompt, context)
        except Exception as e:
            logger.error(f'Gemini generate_content error: {e}')
            return self._fallback_generate_content(prompt, context)

    def get_embeddings(self, text: str, model: str = 'models/text-embedding-004') -> list:
        """Return embedding vector.  Returns empty list if AI is unavailable."""
        genai_mod = _get_genai()
        if genai_mod is None:
            return []
        try:
            if hasattr(genai_mod, 'Client'):
                client = genai_mod.Client(api_key=GEMINI_API_KEY)
                result = client.models.embed_content(model=model, contents=text)
                return result.embeddings[0].values if result.embeddings else []
            else:
                genai_mod.configure(api_key=GEMINI_API_KEY)
                result = genai_mod.embed_content(
                    model=model,
                    content=text,
                    task_type='retrieval_document',
                )
                return result['embedding']
        except Exception as e:
            logger.error(f'Embedding error: {e}')
            return []
