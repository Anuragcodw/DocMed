import logging
from ai.services.llm import LLMManager
from ai.services.prompts import Prompts
from ai.services.memory import ConversationMemory
from appointment.models import MedicalReport

logger = logging.getLogger(__name__)

class HealthcareChatbot:
    def __init__(self, session_id: str, user=None, provider: str = 'gemini'):
        self.memory = ConversationMemory(session_id, user)
        self.user = user
        self.connector = LLMManager.get_connector(provider)

    def ask(self, question: str, report_id: int = None) -> str:
        # Load chat history for context
        history = self.memory.get_history(limit=10)
        
        # Build context
        context_parts = []
        
        # Retrieve report context (RAG placeholder) if report_id specified
        if report_id:
            try:
                report = MedicalReport.objects.get(id=report_id)
                if hasattr(report, 'extracted_text_rel'):
                    context_parts.append(f"Patient's Report Extracted Text:\n{report.extracted_text_rel.raw_text}")
                elif report.extracted_text:
                    context_parts.append(f"Patient's Report Extracted Text:\n{report.extracted_text}")
                
                if hasattr(report, 'ai_analysis_rel'):
                    context_parts.append(f"AI Analysis Findings:\n{report.ai_analysis_rel.detected_diseases}")
                elif report.ai_summary:
                    context_parts.append(f"AI Analysis Findings:\n{report.ai_summary}")
            except MedicalReport.DoesNotExist:
                pass
        
        # Format prompt
        context = "\n\n".join(context_parts)
        
        # Compile messages/prompt with history
        history_str = ""
        for msg in history:
            history_str += f"{msg['role'].capitalize()}: {msg['content']}\n"
        
        prompt = f"{history_str}User: {question}\nAI:"
        
        # Generate response using LLM connector
        response = self.connector.generate_response(
            prompt=prompt,
            system_prompt=Prompts.CHATBOT_SYSTEM,
            context=context
        )
        
        # Save to memory
        self.memory.add_message('user', question)
        self.memory.add_message('ai', response)
        
        # Enforce clinical disclaimer
        disclaimer = (
            "\n\n*Disclaimer: This AI response is for informational purposes only and is not a substitute "
            "for a qualified medical professional. Please consult a licensed doctor for diagnosis and treatment.*"
        )
        if "disclaimer" not in response.lower() and "substitute" not in response.lower():
            response += disclaimer
            
        return response
