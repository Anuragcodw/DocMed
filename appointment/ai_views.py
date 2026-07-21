from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

try:
    from rest_framework.views import APIView
    from rest_framework.response import Response
    from rest_framework.permissions import IsAuthenticated
    from rest_framework.authentication import SessionAuthentication, BasicAuthentication
    HAS_DRF = True
except ImportError:
    HAS_DRF = False

from appointment.models import AIChatSession, AIChatMessage
from ai.chatbot.conversation import MedicalChatbot
from ai.ml.risk_evaluator import RiskEvaluator


# ---------------------------------------------------------------------------
# Standalone Django View fallback (used when DRF is present but session is needed)
# ---------------------------------------------------------------------------

class AIChatView(View):
    """AI Chat endpoint — accepts session-authenticated requests (AJAX from browser)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        import json

        # Support both JSON body and form data
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        message_text = (data.get('message') or '').strip()

        if not message_text:
            return JsonResponse({'error': 'Message is required'}, status=400)

        user = request.user

        # Get or create active chat session
        session, _ = AIChatSession.objects.get_or_create(
            user=user,
            is_active=True,
            defaults={'title': message_text[:50]}
        )

        # Save user message
        AIChatMessage.objects.create(
            session=session,
            sender='user',
            message=message_text
        )

        # Build conversation history (last 6 exchanges)
        history = list(
            session.messages.order_by('created_at').values('sender', 'message')
        )
        chat_history_list = [
            {'role': m['sender'], 'content': m['message']} for m in history
        ]

        # Generate AI response
        try:
            chatbot = MedicalChatbot()
            ai_response = chatbot.chat(message_text, chat_history_list=chat_history_list)
        except Exception as e:
            ai_response = (
                "I'm currently unable to process your request. "
                "Please try again shortly or contact our support team."
            )

        # Save AI response
        AIChatMessage.objects.create(
            session=session,
            sender='model',
            message=ai_response
        )

        return JsonResponse({'reply': ai_response})


class AIRiskAssessmentView(View):
    """Risk assessment endpoint — session authenticated."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        import json

        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        patient_data = data.get('patient_data', '')
        if not patient_data:
            return JsonResponse({'error': 'Patient data is required'}, status=400)

        try:
            evaluator = RiskEvaluator()
            result = evaluator.evaluate(patient_data)
        except Exception as e:
            result = {'error': 'Risk assessment service unavailable.', 'details': str(e)}

        return JsonResponse({'assessment': result})
