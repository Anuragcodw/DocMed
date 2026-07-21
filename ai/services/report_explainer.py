from ai.services.gemini import GeminiClient

class ReportExplainer:
    def __init__(self):
        self.gemini = GeminiClient()
        self.system_prompt = """
        You are a medical AI assistant specializing in explaining medical reports (Blood, MRI, X-Ray, CBC, etc.) to patients in plain language.
        Analyze the report text or findings and output:
        1. Summary of findings
        2. Abnormal values (highlighted clearly)
        3. Normal values
        4. Simple explanation of medical terminology
        5. Educational guidance
        
        Important: Include a short disclaimer that the information is educational and does not replace professional medical advice.
        Format the response in clean Markdown.
        """

    def explain(self, report_text, file_type="text"):
        prompt = f"Please explain the following medical report ({file_type}):\n\n{report_text}"
        return self.gemini.generate_content(
            prompt=prompt,
            system_instruction=self.system_prompt
        )
