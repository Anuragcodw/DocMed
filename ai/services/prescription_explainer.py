from ai.services.gemini import GeminiClient

class PrescriptionExplainer:
    def __init__(self):
        self.gemini = GeminiClient()
        self.system_prompt = """
        You are a medical AI assistant that explains prescriptions.
        Explain the following based on the provided text:
        1. Medicines (Purpose)
        2. Dosage
        3. Timing & Food Instructions
        4. Possible common side effects
        5. Warnings to discuss with the doctor
        
        Use simple, non-medical language.
        
        Important: Include a short disclaimer that the information is educational and does not replace professional medical advice.
        Format the response in clean Markdown.
        """

    def explain(self, prescription_text):
        prompt = f"Please explain this prescription:\n\n{prescription_text}"
        return self.gemini.generate_content(
            prompt=prompt,
            system_instruction=self.system_prompt
        )
