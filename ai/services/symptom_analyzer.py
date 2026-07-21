from ai.services.gemini import GeminiClient

class SymptomAnalyzer:
    def __init__(self):
        self.gemini = GeminiClient()
        self.system_prompt = """
        You are a medical AI assistant specializing in symptom analysis.
        Analyze the patient's symptoms and output:
        1. Extracted symptoms
        2. Possible conditions (with reasoning)
        3. Recommended specialist
        4. Urgency/Seek emergency care flag (Yes/No)
        
        Important: Include a clear disclaimer that this is educational and NOT a medical diagnosis. Do not claim definitive diagnosis.
        Format the response in clean Markdown.
        """

    def analyze(self, patient_input):
        return self.gemini.generate_content(
            prompt=patient_input,
            system_instruction=self.system_prompt
        )
