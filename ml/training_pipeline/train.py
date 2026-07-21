import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

def train_and_save_mock_models():
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models_storage')
    os.makedirs(model_dir, exist_ok=True)
    
    # 1. Diabetes Model
    np.random.seed(42)
    X_diabetes = pd.DataFrame(np.random.rand(100, 5), columns=['age', 'glucose', 'bmi', 'bp', 'insulin'])
    y_diabetes = np.random.choice([0, 1], size=100)
    model_diabetes = RandomForestClassifier(n_estimators=10, random_state=42)
    model_diabetes.fit(X_diabetes, y_diabetes)
    joblib.dump(model_diabetes, os.path.join(model_dir, 'diabetes_model.pkl'))
    
    # 2. Heart Disease Model
    X_heart = pd.DataFrame(np.random.rand(100, 5), columns=['age', 'cholesterol', 'bp', 'max_heart_rate', 'chest_pain'])
    y_heart = np.random.choice([0, 1], size=100)
    model_heart = RandomForestClassifier(n_estimators=10, random_state=42)
    model_heart.fit(X_heart, y_heart)
    joblib.dump(model_heart, os.path.join(model_dir, 'heart_disease_model.pkl'))

    # 3. Stroke Model
    X_stroke = pd.DataFrame(np.random.rand(100, 4), columns=['age', 'hypertension', 'heart_disease', 'glucose'])
    y_stroke = np.random.choice([0, 1], size=100)
    model_stroke = LogisticRegression(random_state=42)
    model_stroke.fit(X_stroke, y_stroke)
    joblib.dump(model_stroke, os.path.join(model_dir, 'stroke_model.pkl'))

    # 4. Kidney Disease Model
    X_kidney = pd.DataFrame(np.random.rand(100, 3), columns=['age', 'bp', 'specific_gravity'])
    y_kidney = np.random.choice([0, 1], size=100)
    model_kidney = RandomForestClassifier(n_estimators=10, random_state=42)
    model_kidney.fit(X_kidney, y_kidney)
    joblib.dump(model_kidney, os.path.join(model_dir, 'kidney_disease_model.pkl'))

    print(f"Mock ML models trained and saved to {model_dir}")

if __name__ == '__main__':
    train_and_save_mock_models()
