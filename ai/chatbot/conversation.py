from ai.services.gemini import GeminiClient
from ai.rag.retriever import RAGRetriever

class MedicalChatbot:
    def __init__(self):
        self.gemini = GeminiClient()
        self.retriever = RAGRetriever()
        self.system_prompt = """
        You are an intelligent, empathetic AI Healthcare Assistant.
        You understand English, Hindi, Punjabi, Tamil, Telugu, Gujarati, Marathi, Kannada, Malayalam, Bengali, and Urdu.
        Auto-detect the language of the user's prompt and reply in the SAME language.
        
        Your capabilities:
        - Understand symptoms and suggest when to see a doctor.
        - Answer medical queries using the provided context.
        - Understand the context of the conversation from previous messages.
        
        Rules:
        1. Base your medical answers on the provided Context if relevant.
        2. Never claim a definitive diagnosis.
        3. ALWAYS include this short disclaimer at the end of your response (translated to the user's language): "Disclaimer: This information is for educational purposes and does not replace professional medical advice."
        """

    def chat(self, user_input, chat_history_list=None):
        """
        chat_history_list: [{'role': 'user', 'content': '...'}, {'role': 'model', 'content': '...'}]
        """
        if chat_history_list is None:
            chat_history_list = []
            
        # 1. Format history for context
        history_context = "Previous Conversation:\n"
        for msg in chat_history_list[-6:]: # Keep last 6 messages for context
            history_context += f"{msg['role'].capitalize()}: {msg['content']}\n"
            
        # 2. Retrieve RAG context based on current input
        rag_context = self.retriever.retrieve_context(user_input)
        
        # 3. Combine context
        full_context = f"{history_context}\n\nMedical Knowledge Base Context:\n{rag_context}"
        
        # 4. Generate response
        response = self.gemini.generate_content(
            prompt=user_input,
            context=full_context,
            system_instruction=self.system_prompt
        )
        
        return response
