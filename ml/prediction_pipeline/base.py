import os
import joblib
import numpy as np
import pandas as pd
import logging
from sklearn.base import BaseEstimator

logger = logging.getLogger(__name__)

class BasePredictionPipeline:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models_storage')
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
        self.model = self._load_or_create_mock()

    def _load_or_create_mock(self):
        if os.path.exists(self.model_path):
            try:
                return joblib.load(self.model_path)
            except Exception as e:
                logger.error(f"Error loading model {self.model_name}: {e}")
        
        # Fallback Mock Model that behaves like scikit-learn estimator
        logger.info(f"Model file {self.model_name}.pkl not found. Creating mock model.")
        return MockModel(self.model_name)

    def predict(self, features: dict) -> dict:
        raise NotImplementedError("Subclasses must implement predict")

class MockModel(BaseEstimator):
    def __init__(self, name: str):
        self.name = name

    def predict(self, X):
        # Always output binary class 0 or 1
        return np.random.choice([0, 1], size=len(X))

    def predict_proba(self, X):
        # Generate random probability pairs
        probs = np.random.rand(len(X))
        return np.vstack([1 - probs, probs]).T

class DiabetesPipeline(BasePredictionPipeline):
    def __init__(self):
        super().__init__('diabetes_model')

    def predict(self, features: dict) -> dict:
        # Expected keys: age, glucose, bmi, bp, insulin
        df = pd.DataFrame([features])
        pred = self.model.predict(df)[0]
        proba = self.model.predict_proba(df)[0][1] if hasattr(self.model, 'predict_proba') else 0.45
        
        result = "High Risk" if pred == 1 else "Normal Risk"
        risk_score = round(proba * 100, 1)

        suggestions = (
            "Maintain a low sugar diet, exercise at least 30 minutes daily, "
            "and check blood sugar levels regularly."
            if pred == 1 else "Keep up the balanced diet and active lifestyle."
        )

        return {
            'prediction_type': 'Diabetes',
            'result': result,
            'probability': float(proba),
            'risk_score': risk_score,
            'lifestyle_suggestions': suggestions
        }

class HeartDiseasePipeline(BasePredictionPipeline):
    def __init__(self):
        super().__init__('heart_disease_model')

    def predict(self, features: dict) -> dict:
        # Expected keys: age, cholesterol, bp, max_heart_rate, chest_pain
        df = pd.DataFrame([features])
        pred = self.model.predict(df)[0]
        proba = self.model.predict_proba(df)[0][1] if hasattr(self.model, 'predict_proba') else 0.35
        
        result = "High Risk" if pred == 1 else "Normal Risk"
        risk_score = round(proba * 100, 1)

        suggestions = (
            "Limit cholesterol/fat intake, engage in light cardio under supervision, "
            "and consult a cardiologist."
            if pred == 1 else "Continue a heart-healthy diet with regular exercise."
        )

        return {
            'prediction_type': 'Heart Disease',
            'result': result,
            'probability': float(proba),
            'risk_score': risk_score,
            'lifestyle_suggestions': suggestions
        }

class StrokePipeline(BasePredictionPipeline):
    def __init__(self):
        super().__init__('stroke_model')

    def predict(self, features: dict) -> dict:
        df = pd.DataFrame([features])
        pred = self.model.predict(df)[0]
        proba = self.model.predict_proba(df)[0][1] if hasattr(self.model, 'predict_proba') else 0.20
        
        result = "High Risk" if pred == 1 else "Normal Risk"
        risk_score = round(proba * 100, 1)

        suggestions = (
            "Control high blood pressure, reduce salt intake, and avoid stressful activities."
            if pred == 1 else "Continue cardiovascular health maintenance."
        )

        return {
            'prediction_type': 'Stroke',
            'result': result,
            'probability': float(proba),
            'risk_score': risk_score,
            'lifestyle_suggestions': suggestions
        }

class KidneyDiseasePipeline(BasePredictionPipeline):
    def __init__(self):
        super().__init__('kidney_disease_model')

    def predict(self, features: dict) -> dict:
        df = pd.DataFrame([features])
        pred = self.model.predict(df)[0]
        proba = self.model.predict_proba(df)[0][1] if hasattr(self.model, 'predict_proba') else 0.15
        
        result = "High Risk" if pred == 1 else "Normal Risk"
        risk_score = round(proba * 100, 1)

        suggestions = (
            "Avoid high protein intake, drink plenty of water, and monitor kidney function parameters."
            if pred == 1 else "Maintain hydration and regular checkups."
        )

        return {
            'prediction_type': 'Kidney Disease',
            'result': result,
            'probability': float(proba),
            'risk_score': risk_score,
            'lifestyle_suggestions': suggestions
        }

class BloodPressurePipeline(BasePredictionPipeline):
    def __init__(self):
        super().__init__('bp_model')

    def predict(self, features: dict) -> dict:
        systolic = features.get('systolic', 120)
        diastolic = features.get('diastolic', 80)
        
        if systolic >= 140 or diastolic >= 90:
            result = "Hypertension"
            risk_score = 75.0
            suggestions = "Reduce sodium intake, perform meditation/stress reduction, and consult a physician."
        elif systolic <= 90 or diastolic <= 60:
            result = "Hypotension"
            risk_score = 45.0
            suggestions = "Increase fluid intake, consume adequate salt, and avoid sudden posture changes."
        else:
            result = "Normal"
            risk_score = 10.0
            suggestions = "Maintain normal physical activity and balanced diet."

        return {
            'prediction_type': 'Blood Pressure',
            'result': result,
            'probability': float(risk_score / 100),
            'risk_score': risk_score,
            'lifestyle_suggestions': suggestions
        }

class BMIPipeline:
    def predict(self, features: dict) -> dict:
        weight = features.get('weight', 70.0) # kg
        height = features.get('height', 1.75) # meters
        
        if height <= 0:
            return {
                'prediction_type': 'BMI',
                'result': 'Invalid parameters',
                'probability': 0.0,
                'risk_score': 0.0,
                'lifestyle_suggestions': ""
            }

        bmi = weight / (height ** 2)
        
        if bmi < 18.5:
            result = "Underweight"
            risk_score = 30.0
            suggestions = "Focus on nutrient-dense foods and strength building exercises."
        elif bmi < 25:
            result = "Normal weight"
            risk_score = 5.0
            suggestions = "Maintain your current healthy habits."
        elif bmi < 30:
            result = "Overweight"
            risk_score = 45.0
            suggestions = "Aim for regular physical activity and a calorie-controlled diet."
        else:
            result = "Obese"
            risk_score = 80.0
            suggestions = "Adopt a structured weight-loss program and consult a nutritionist."

        return {
            'prediction_type': 'BMI',
            'result': f"{result} ({round(bmi, 1)})",
            'probability': float(risk_score / 100),
            'risk_score': risk_score,
            'lifestyle_suggestions': suggestions
        }

class MLPredictionEngine:
    @staticmethod
    def run_all(features: dict) -> list:
        results = []
        try:
            results.append(DiabetesPipeline().predict(features))
            results.append(HeartDiseasePipeline().predict(features))
            results.append(StrokePipeline().predict(features))
            results.append(KidneyDiseasePipeline().predict(features))
            results.append(BloodPressurePipeline().predict(features))
            results.append(BMIPipeline().predict(features))
        except Exception as e:
            logger.error(f"Error executing prediction pipelines: {e}")
        return results
