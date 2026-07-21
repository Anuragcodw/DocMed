import logging
from appointment.models import AIChatSession, AIChatMessage

logger = logging.getLogger(__name__)

class ConversationMemory:
    def __init__(self, session_id: str, user=None):
        self.session_id = session_id
        self.user = user
        # Ensure session exists in database
        self.session_obj, created = AIChatSession.objects.get_or_create(
            session_id=self.session_id,
            defaults={'user': self.user if (self.user and self.user.is_authenticated) else None}
        )

    def add_message(self, sender: str, text: str):
        try:
            AIChatMessage.objects.create(
                session=self.session_obj,
                sender=sender,
                message_text=text
            )
        except Exception as e:
            logger.error(f"Error adding to chat memory: {e}")

    def get_history(self, limit: int = 15):
        try:
            msgs = self.session_obj.messages.all().order_by('timestamp')[:limit]
            return [{"role": m.sender, "content": m.message_text} for m in msgs]
        except Exception as e:
            logger.error(f"Error reading chat history: {e}")
            return []

    def clear(self):
        try:
            self.session_obj.messages.all().delete()
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
