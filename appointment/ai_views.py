import json
import logging
from django.http import JsonResponse
from django.views import View

from appointment.models import AIChatSession, AIChatMessage
from ai.chatbot.conversation import MedicalChatbot
from ai.ml.risk_evaluator import RiskEvaluator

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000  # Step 8 Security rule: reject messages over 2000 chars


class AIChatView(View):
    """
    AI Chat endpoint — processes user messages safely,
    validates input, enforces a 2000-character ceiling, logs API failures,
    and guarantees a valid JSON response without server crashes.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
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

        # 2. Extract & validate message text
        message_text = (data.get('message') or '').strip()

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
            session, _ = AIChatSession.objects.get_or_create(
                user=user,
                is_active=True,
                defaults={'title': message_text[:50]}
            )

            AIChatMessage.objects.create(
                session=session,
                sender='user',
                message=message_text
            )

            history = list(
                session.messages.order_by('created_at').values('sender', 'message')
            )
            chat_history_list = [
                {'role': m['sender'], 'content': m['message']} for m in history
            ]
        except Exception as e:
            logger.error(f"[AIChatView] Database session save error: {e}")

        # 4. Generate AI response with comprehensive exception handling
        try:
            chatbot = MedicalChatbot()
            ai_response = chatbot.chat(message_text, chat_history_list=chat_history_list)
        except Exception as e:
            logger.error(f"[AIChatView] Gemini API failure or timeout: {e}")
            ai_response = (
                "AI service is temporarily unavailable. Please try again later.\n\n"
                "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
            )

        # 5. Persist AI response
        if session:
            try:
                AIChatMessage.objects.create(
                    session=session,
                    sender='model',
                    message=ai_response
                )
            except Exception as e:
                logger.error(f"[AIChatView] Failed to save AI response message: {e}")

        return JsonResponse({'reply': ai_response})


class AIRiskAssessmentView(View):
    """Risk assessment endpoint — session authenticated."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)
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
