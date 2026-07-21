import re

class SymptomChecker:
    def __init__(self):
        # Dictionary linking symptoms to departments/diseases and severity
        self.kb = {
            'chest pain': {
                'diseases': ['Angina', 'Myocardial Infarction', 'Acid Reflux'],
                'specialty': 'Cardiology',
                'severity': 'Critical',
                'emergency': True,
                'warning': "Chest pain can indicate a cardiac emergency. Seek emergency services immediately!"
            },
            'shortness of breath': {
                'diseases': ['Asthma', 'COPD', 'Pneumonia', 'Heart Failure'],
                'specialty': 'Cardiology',
                'severity': 'High',
                'emergency': True,
                'warning': "Difficulty breathing requires immediate medical evaluation. Consult a doctor immediately."
            },
            'headache': {
                'diseases': ['Migraine', 'Tension Headache', 'Hypertension'],
                'specialty': 'Neuroanatomy',
                'severity': 'Low',
                'emergency': False,
                'warning': ""
            },
            'blurry vision': {
                'diseases': ['Cataract', 'Refractive Error', 'Diabetic Retinopathy'],
                'specialty': 'Eye Care',
                'severity': 'Medium',
                'emergency': False,
                'warning': ""
            },
            'toothache': {
                'diseases': ['Dental Caries', 'Pulpitis', 'Abscess'],
                'specialty': 'Dentistry',
                'severity': 'Low',
                'emergency': False,
                'warning': ""
            },
            'sore throat': {
                'diseases': ['Pharyngitis', 'Tonsillitis', 'Laryngitis'],
                'specialty': 'ENT Specialists',
                'severity': 'Low',
                'emergency': False,
                'warning': ""
            },
            'joint pain': {
                'diseases': ['Arthritis', 'Sprain', 'Gout'],
                'specialty': 'Physical Therapy',
                'severity': 'Medium',
                'emergency': False,
                'warning': ""
            }
        }

    def analyze_symptoms(self, text: str) -> dict:
        text_lower = text.lower()
        detected_symptoms = []
        possible_diseases = []
        specialties = set()
        max_severity = 'Low'
        is_emergency = False
        warnings = []

        for symptom, data in self.kb.items():
            if re.search(r'\b' + re.escape(symptom) + r'\b', text_lower):
                detected_symptoms.append(symptom)
                possible_diseases.extend(data['diseases'])
                specialties.add(data['specialty'])
                if data['emergency']:
                    is_emergency = True
                if data['warning']:
                    warnings.append(data['warning'])
                # Severity upgrading logic
                sev = data['severity']
                if sev == 'Critical' or (sev == 'High' and max_severity != 'Critical'):
                    max_severity = sev
                elif sev == 'Medium' and max_severity not in ['Critical', 'High']:
                    max_severity = sev

        # Defaults if nothing recognized
        if not detected_symptoms:
            possible_diseases = ["General Malaise", "Viral Syndrome"]
            specialties.add("Eye Care")  # default fallback
            max_severity = "Low"

        disclaimer = (
            "This symptom evaluation is powered by AI for informational purposes only. "
            "It is not a substitute for professional medical advice."
        )

        return {
            'detected_symptoms': detected_symptoms,
            'possible_diseases': list(set(possible_diseases)),
            'recommended_specialties': list(specialties),
            'severity': max_severity,
            'is_emergency': is_emergency,
            'emergency_warning': " ".join(warnings) if warnings else "Monitor your condition closely and seek professional help.",
            'disclaimer': disclaimer
        }
