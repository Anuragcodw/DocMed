from ai.services.gemini import GeminiClient

class RiskEvaluator:
    def __init__(self):
        self.gemini = GeminiClient()
        self.system_prompt = """
        You are a health risk evaluation assistant.
        Evaluate the patient's inputs to estimate risk categories (Low, Moderate, High) for:
        - Diabetes Risk
        - Heart Health Risk
        - Blood Pressure Risk
        - BMI Analysis
        - Lifestyle Risk
        
        Important: Include a strict disclaimer that this is for educational purposes only and is not a clinical risk assessment.
        Format the response in clean Markdown.
        """

    def evaluate(self, patient_data):
        prompt = f"Please evaluate health risks based on the following data:\n\n{patient_data}"
        return self.gemini.generate_content(
            prompt=prompt,
            system_instruction=self.system_prompt
        )
