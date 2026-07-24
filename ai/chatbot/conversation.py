import logging
from ai.services.gemini import GeminiClient
from ai.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)


class MedicalChatbot:
    """
    DocMed AI Healthcare Assistant — Handles multi-lingual conversation,
    session context, RAG knowledge retrieval, and polite medical advice.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.retriever = RAGRetriever()
        self.system_prompt = """
        You are DocMed's AI Healthcare Assistant, a polite, empathetic, and professional medical virtual assistant.

        Core Guidelines:
        1. Answer healthcare and medical questions politely, clearly, and concisely.
        2. Never provide a definitive or final clinical diagnosis. Always remind the user that your output is for educational purposes only.
        3. Recommend consulting a qualified doctor or specialist on DocMed for clinical evaluation and prescription.
        4. Multi-Lingual Support: Seamlessly support both English and Hindi (and other Indian languages). Always detect the user's input language and respond in the SAME language.
        5. Session Memory: Maintain context from previous messages in the conversation session.
        6. Disclaimer: ALWAYS end your response with this disclaimer (translated to the user's language):
           "Disclaimer: This information is for educational purposes and does not replace professional medical advice. Please consult a doctor on DocMed for clinical care."
        """

    def chat(self, user_input: str, chat_history_list: list | None = None) -> str:
        """
        Processes user query with conversation history context and RAG retrieval.
        chat_history_list: [{'role': 'user', 'content': '...'}, {'role': 'model', 'content': '...'}]
        """
        if chat_history_list is None:
            chat_history_list = []

        # 1. Format previous session conversation history (last 6 exchanges)
        history_context = "Session Conversation History:\n"
        for msg in chat_history_list[-6:]:
            role_name = "User" if msg.get('role') == 'user' else "Assistant"
            history_context += f"{role_name}: {msg.get('content', '')}\n"

        # 2. Retrieve relevant context from RAG Knowledge Base safely
        try:
            rag_context = self.retriever.retrieve_context(user_input)
        except Exception as e:
            logger.warning(f"RAG retrieval error: {e}")
            rag_context = ""

        # 3. Combine context
        full_context = f"{history_context}\n\nDocMed Medical Knowledge Base:\n{rag_context}"

        # 4. Generate AI response
        try:
            response = self.gemini.generate_content(
                prompt=user_input,
                context=full_context,
                system_instruction=self.system_prompt
            )
            return response
        except Exception as e:
            logger.error(f"MedicalChatbot generation exception: {e}")
            return (
                "AI service is temporarily unavailable. Please try again later.\n\n"
                "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
            )
