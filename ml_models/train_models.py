import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression

def train_and_save_all():
    model_dir = os.path.join(os.path.dirname(__file__), 'models_storage')
    os.makedirs(model_dir, exist_ok=True)
    
    np.random.seed(42)
    
    # 1. Diabetes Prediction
    # Features: age, glucose, bmi, bp, insulin
    X_diabetes = pd.DataFrame(np.random.rand(100, 5) * [50, 150, 15, 60, 200] + [20, 70, 15, 60, 20], 
                              columns=['age', 'glucose', 'bmi', 'bp', 'insulin'])
    y_diabetes = (X_diabetes['glucose'] > 125) | (X_diabetes['bmi'] > 30)
    y_diabetes = y_diabetes.astype(int)
    model_diabetes = RandomForestClassifier(n_estimators=10, random_state=42)
    model_diabetes.fit(X_diabetes, y_diabetes)
    joblib.dump(model_diabetes, os.path.join(model_dir, 'diabetes_model.joblib'))
    
    # 2. Heart Disease Prediction
    # Features: age, cholesterol, bp, max_heart_rate, chest_pain
    X_heart = pd.DataFrame(np.random.rand(100, 5) * [50, 150, 60, 100, 4] + [20, 150, 90, 80, 0],
                           columns=['age', 'cholesterol', 'bp', 'max_heart_rate', 'chest_pain'])
    y_heart = (X_heart['cholesterol'] > 240) | (X_heart['bp'] > 140)
    y_heart = y_heart.astype(int)
    model_heart = RandomForestClassifier(n_estimators=10, random_state=42)
    model_heart.fit(X_heart, y_heart)
    joblib.dump(model_heart, os.path.join(model_dir, 'heart_disease_model.joblib'))
    
    # 3. Stroke Prediction
    # Features: age, hypertension, heart_disease, glucose
    X_stroke = pd.DataFrame(np.random.rand(100, 4) * [60, 1, 1, 150] + [18, 0, 0, 70],
                            columns=['age', 'hypertension', 'heart_disease', 'glucose'])
    y_stroke = (X_stroke['age'] > 65) & ((X_stroke['hypertension'] > 0.5) | (X_stroke['heart_disease'] > 0.5))
    y_stroke = y_stroke.astype(int)
    model_stroke = LogisticRegression(random_state=42)
    model_stroke.fit(X_stroke, y_stroke)
    joblib.dump(model_stroke, os.path.join(model_dir, 'stroke_model.joblib'))
    
    # 4. Kidney Disease Prediction
    # Features: age, bp, specific_gravity
    X_kidney = pd.DataFrame(np.random.rand(100, 3) * [50, 60, 0.02] + [20, 60, 1.00],
                            columns=['age', 'bp', 'specific_gravity'])
    y_kidney = (X_kidney['bp'] > 90) & (X_kidney['specific_gravity'] < 1.01)
    y_kidney = y_kidney.astype(int)
    model_kidney = RandomForestClassifier(n_estimators=10, random_state=42)
    model_kidney.fit(X_kidney, y_kidney)
    joblib.dump(model_kidney, os.path.join(model_dir, 'kidney_disease_model.joblib'))
    
    # 5. BMI Risk Prediction
    # Features: age, weight (kg), height (m), gender (0=female, 1=male)
    X_bmi = pd.DataFrame(np.random.rand(100, 4) * [50, 80, 0.5, 1] + [20, 40, 1.4, 0],
                         columns=['age', 'weight', 'height', 'gender'])
    bmi = X_bmi['weight'] / (X_bmi['height'] ** 2)
    y_bmi = (bmi < 18.5) | (bmi >= 25)
    y_bmi = y_bmi.astype(int)
    model_bmi = RandomForestClassifier(n_estimators=10, random_state=42)
    model_bmi.fit(X_bmi, y_bmi)
    joblib.dump(model_bmi, os.path.join(model_dir, 'bmi_risk_model.joblib'))
    
    # 6. Hypertension Risk
    # Features: age, bp (systolic), bp (diastolic), lifestyle_score (1-10)
    X_hyper = pd.DataFrame(np.random.rand(100, 4) * [50, 80, 40, 9] + [20, 90, 60, 1],
                           columns=['age', 'systolic', 'diastolic', 'lifestyle_score'])
    y_hyper = (X_hyper['systolic'] >= 140) | (X_hyper['diastolic'] >= 90)
    y_hyper = y_hyper.astype(int)
    model_hyper = RandomForestClassifier(n_estimators=10, random_state=42)
    model_hyper.fit(X_hyper, y_hyper)
    joblib.dump(model_hyper, os.path.join(model_dir, 'hypertension_risk_model.joblib'))
    
    # 7. Lifestyle Risk Score (regression outputting 0-100 risk score)
    # Features: smoking (0/1), alcohol (0/1), physical_activity (hours/week, 0-10), sleep_hours (4-10)
    X_life = pd.DataFrame(np.random.rand(100, 4) * [1, 1, 10, 6] + [0, 0, 0, 4],
                          columns=['smoking', 'alcohol', 'physical_activity', 'sleep_hours'])
    y_life = (X_life['smoking'] * 30 + X_life['alcohol'] * 20 - X_life['physical_activity'] * 3 + (8 - X_life['sleep_hours']) * 5)
    y_life = np.clip(y_life + 40, 0, 100) # scale to 0-100 range
    model_life = RandomForestRegressor(n_estimators=10, random_state=42)
    model_life.fit(X_life, y_life)
    joblib.dump(model_life, os.path.join(model_dir, 'lifestyle_risk_model.joblib'))
    
    print(f"All 7 ML models trained and saved successfully to {model_dir}!")

if __name__ == '__main__':
    train_and_save_all()
