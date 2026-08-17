import base64
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views import View

from appointment.models import AIChatSession, AIChatMessage
from ai.chatbot.conversation import MedicalChatbot
from ai.services.gemini import GeminiClient
from ai.services.elevenlabs import ElevenLabsService
from ai.ml.risk_evaluator import RiskEvaluator

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000  # Step 8 Security rule: reject messages over 2000 chars

LANGUAGE_MAP = {
    'en': 'English',
    'hi': 'Hindi',
    'pa': 'Punjabi',
    'ur': 'Urdu',
    'bn': 'Bengali',
    'gu': 'Gujarati',
    'mr': 'Marathi',
    'ta': 'Tamil',
    'te': 'Telugu',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'fr': 'French',
    'es': 'Spanish',
    'de': 'German',
    'ar': 'Arabic',
    'pt': 'Portuguese',
    'ja': 'Japanese',
    'zh': 'Chinese',
}


def authenticate_user(request):
    """
    Authenticates user via standard Django Session cookies or JWT Bearer header.
    Guarantees seamless authentication for both web sessions and JWT API clients.
    """
    if getattr(request, 'user', None) and request.user.is_authenticated:
        return request.user
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        jwt_auth = JWTAuthentication()
        auth_result = jwt_auth.authenticate(request)
        if auth_result is not None:
            request.user, _ = auth_result
            return request.user
    except Exception as exc:
        logger.debug(f"[ai_views] JWT bearer token authentication check: {exc}")
    return request.user


class AIChatView(View):
    """
    AI Chat endpoint — processes user messages safely,
    generates primary English response via Gemini, performs translation if requested,
    synthesizes speech via ElevenLabs TTS, and returns structured response.
    """

    def dispatch(self, request, *args, **kwargs):
        user = authenticate_user(request)
        if not user.is_authenticated:
            return JsonResponse(
                {'error': 'Authentication required. Please log in to access the AI assistant.'},
                status=401
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # 1. Parse JSON body or form payload safely
        try:
            if request.body:
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST
        except Exception as e:
            logger.warning(f"[AIChatView] Invalid JSON format received: {e}")
            return JsonResponse({'error': 'Invalid JSON request format.'}, status=400)

        # 2. Extract & validate message text and requested language code
        message_text = (data.get('message') or '').strip()
        language_code = (data.get('language_code') or data.get('language') or 'en').strip().lower()
        target_language = LANGUAGE_MAP.get(language_code, 'English')

        if not message_text:
            logger.warning("[AIChatView] Empty message rejected.")
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

        if len(message_text) > MAX_MESSAGE_LENGTH:
            logger.warning(f"[AIChatView] Over-length message rejected ({len(message_text)} chars).")
            return JsonResponse(
                {'error': f'Message is too long. Maximum allowed length is {MAX_MESSAGE_LENGTH} characters.'},
                status=400
            )

        user = request.user

        # 3. Retrieve or create session & save user message
        session = None
        chat_history_list = []
        try:
            session_id = f"user_{user.id}" if user and user.is_authenticated else f"anon_{request.session.session_key or 'default'}"
            session, _ = AIChatSession.objects.get_or_create(
                user=user if user and user.is_authenticated else None,
                session_id=session_id
            )

            AIChatMessage.objects.create(
                session=session,
                sender='user',
                message_text=message_text
            )

            history = list(
                session.messages.order_by('timestamp').values('sender', 'message_text')
            )
            chat_history_list = [
                {'role': m['sender'], 'content': m['message_text']} for m in history
            ]
        except Exception as e:
            logger.error(f"[AIChatView] Database session save error: {e}")

        # 4. Generate PRIMARY English AI response with Gemini
        english_response = ""
        try:
            chatbot = MedicalChatbot()
            english_response = chatbot.chat(message_text, chat_history_list=chat_history_list)
        except Exception as e:
            logger.error(f"[AIChatView] Gemini API failure or timeout: {e}")
            english_response = (
                "AI service is temporarily unavailable. Please try again later.\n\n"
                "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
            )

        # 5. Multilingual Translation (if non-English language selected)
        translated_response = ""
        if language_code != 'en':
            try:
                gemini_client = GeminiClient()
                translated_response = gemini_client.translate_text(english_response, target_language)
            except Exception as e:
                logger.error(f"[AIChatView] Translation to {target_language} failed: {e}")
                translated_response = english_response

        # 6. ElevenLabs Text-to-Speech Synthesis
        audio_base64 = ""
        try:
            tts_text = translated_response if (language_code != 'en' and translated_response) else english_response
            elevenlabs_service = ElevenLabsService()
            audio_bytes = elevenlabs_service.generate_speech(tts_text, language_code=language_code)
            if audio_bytes:
                audio_base64 = "data:audio/mpeg;base64," + base64.b64encode(audio_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"[AIChatView] ElevenLabs TTS error: {e}")

        # 7. Persist AI response
        if session:
            try:
                saved_text = f"English:\n{english_response}\n\n{target_language}:\n{translated_response}" if (language_code != 'en' and translated_response) else english_response
                AIChatMessage.objects.create(
                    session=session,
                    sender='ai',
                    message_text=saved_text
                )
            except Exception as e:
                logger.error(f"[AIChatView] Failed to save AI response message: {e}")

        return JsonResponse({
            'reply': translated_response if (language_code != 'en' and translated_response) else english_response,
            'english_response': english_response,
            'translated_response': translated_response if language_code != 'en' else '',
            'language': target_language,
            'language_code': language_code,
            'audio_base64': audio_base64,
            'audio_url': ''
        })


class TextToSpeechView(View):
    """
    Standalone API endpoint for Text-to-Speech synthesis (POST /api/ai/tts/).
    Generates ElevenLabs audio for the specified text and language code.
    """
    def dispatch(self, request, *args, **kwargs):
        user = authenticate_user(request)
        if not user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            if request.body:
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST
        except Exception:
            data = {}

        text = (data.get('text') or data.get('message') or '').strip()
        language_code = (data.get('language_code') or 'en').strip().lower()

        if not text:
            return JsonResponse({'error': 'Text parameter is required.'}, status=400)

        elevenlabs_service = ElevenLabsService()
        audio_bytes = elevenlabs_service.generate_speech(text, language_code=language_code)
        if audio_bytes:
            return HttpResponse(audio_bytes, content_type='audio/mpeg')
        return JsonResponse({'error': 'ElevenLabs TTS unavailable.', 'fallback': True}, status=404)



class AIRiskAssessmentView(View):
    """Risk assessment endpoint — session & JWT authenticated."""

    def dispatch(self, request, *args, **kwargs):
        user = authenticate_user(request)
        if not user.is_authenticated:
            return JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            if request.body:
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST
        except Exception as e:
            logger.warning(f"[AIRiskAssessmentView] Invalid JSON payload: {e}")
            return JsonResponse({'error': 'Invalid request format.'}, status=400)

        patient_data = data.get('patient_data', '')
        if not patient_data:
            return JsonResponse({'error': 'Patient data is required'}, status=400)

        try:
            evaluator = RiskEvaluator()
            result = evaluator.evaluate(patient_data)
        except Exception as e:
            logger.error(f"[AIRiskAssessmentView] Risk evaluation error: {e}")
            result = {'error': 'Risk assessment service unavailable.', 'details': str(e)}

        return JsonResponse({'assessment': result})
