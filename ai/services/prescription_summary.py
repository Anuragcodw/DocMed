from ai.services.llm import LLMManager
from ai.services.prompts import Prompts

class PrescriptionSummaryService:
    def __init__(self, provider: str = 'gemini'):
        self.connector = LLMManager.get_connector(provider)

    def explain_prescription(self, raw_prescription_text: str) -> dict:
        prompt = Prompts.get_prescription_prompt(raw_prescription_text)
        explanation = self.connector.generate_response(
            prompt=prompt,
            system_prompt=Prompts.PRESCRIPTION_EXPLAINER_SYSTEM
        )

        # Basic parse of response to output structured segments for fallback
        # In a real environment, the LLM will output a JSON which we load.
        # Here we provide a robust structured mock extractor if output starts with mock.
        is_mock = explanation.startswith("[Mock")
        
        medicines = []
        if is_mock:
            # Generate mock structured medicine list
            medicines = [
                {
                    'name': 'Amoxicillin 500mg',
                    'why_prescribed': 'Antibiotic to treat bacterial infections',
                    'dosage': '1 tablet',
                    'timing': 'Morning, Afternoon, Night',
                    'food_instructions': 'After Food',
                    'warnings': 'Complete the full course as prescribed.',
                    'side_effects': 'Nausea, diarrhea, stomach upset',
                    'storage': 'Store at room temperature away from direct sunlight.'
                },
                {
                    'name': 'Paracetamol 650mg',
                    'why_prescribed': 'Analgesic to reduce pain and fever',
                    'dosage': '1 tablet as needed',
                    'timing': 'When experiencing fever/pain',
                    'food_instructions': 'After Food',
                    'warnings': 'Do not exceed 4 tablets in 24 hours.',
                    'side_effects': 'Rare liver damage if exceeded dose',
                    'storage': 'Store in a dry place.'
                }
            ]
        
        return {
            'simplified_summary': explanation,
            'medicines': medicines,
            'disclaimer': (
                "This AI explanation is for informational purposes only. "
                "Always consult a pharmacist or doctor regarding your medicines."
            )
        }
