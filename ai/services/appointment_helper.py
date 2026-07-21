from ai.services.gemini import GeminiClient
import json

class AppointmentHelper:
    def __init__(self):
        self.gemini = GeminiClient()
        self.system_prompt = """
        You are an appointment routing assistant. 
        Analyze the user's intent and extract details for booking, rescheduling, or canceling an appointment.
        Determine the intent (BOOK, RESCHEDULE, CANCEL, QUERY_TIMINGS, or UNKNOWN).
        Extract relevant entities (date, time, doctor name, department, hospital).
        
        Respond ONLY with a valid JSON object matching this schema:
        {
            "intent": "string",
            "entities": {
                "doctor_name": "string or null",
                "department": "string or null",
                "date": "string or null",
                "time": "string or null"
            }
        }
        """

    def parse_intent(self, user_input):
        response_text = self.gemini.generate_content(
            prompt=user_input,
            system_instruction=self.system_prompt
        )
        try:
            # Clean up the response if it has markdown formatting
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception:
            return {"intent": "UNKNOWN", "entities": {}}
