import os
import joblib
import pandas as pd
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models_storage')

def get_model(name):
    path = os.path.join(MODEL_DIR, f"{name}.joblib")
    if os.path.exists(path):
        return joblib.load(path)
    return None

def predict_diabetes(age, glucose, bmi, bp, insulin):
    model = get_model('diabetes_model')
    if not model:
        return "High Risk" if glucose > 125 or bmi > 30 else "Normal Risk", 0.45
    df = pd.DataFrame([[age, glucose, bmi, bp, insulin]], columns=['age', 'glucose', 'bmi', 'bp', 'insulin'])
    pred = model.predict(df)[0]
    proba = model.predict_proba(df)[0][1]
    return "High Risk" if pred == 1 else "Normal Risk", float(proba)

def predict_heart_disease(age, cholesterol, bp, max_heart_rate, chest_pain):
    model = get_model('heart_disease_model')
    if not model:
        return "High Risk" if cholesterol > 240 or bp > 140 else "Normal Risk", 0.35
    df = pd.DataFrame([[age, cholesterol, bp, max_heart_rate, chest_pain]], 
                      columns=['age', 'cholesterol', 'bp', 'max_heart_rate', 'chest_pain'])
    pred = model.predict(df)[0]
    proba = model.predict_proba(df)[0][1]
    return "High Risk" if pred == 1 else "Normal Risk", float(proba)

def predict_stroke(age, hypertension, heart_disease, glucose):
    model = get_model('stroke_model')
    if not model:
        return "High Risk" if age > 65 and (hypertension or heart_disease) else "Normal Risk", 0.20
    df = pd.DataFrame([[age, hypertension, heart_disease, glucose]], 
                      columns=['age', 'hypertension', 'heart_disease', 'glucose'])
    pred = model.predict(df)[0]
    proba = model.predict_proba(df)[0][1]
    return "High Risk" if pred == 1 else "Normal Risk", float(proba)

def predict_kidney_disease(age, bp, specific_gravity):
    model = get_model('kidney_disease_model')
    if not model:
        return "High Risk" if bp > 90 and specific_gravity < 1.01 else "Normal Risk", 0.15
    df = pd.DataFrame([[age, bp, specific_gravity]], columns=['age', 'bp', 'specific_gravity'])
    pred = model.predict(df)[0]
    proba = model.predict_proba(df)[0][1]
    return "High Risk" if pred == 1 else "Normal Risk", float(proba)

def predict_bmi_risk(age, weight, height, gender):
    model = get_model('bmi_risk_model')
    bmi = weight / (height ** 2) if height > 0 else 0
    if not model:
        return "High Risk" if bmi < 18.5 or bmi >= 25 else "Normal Risk", 0.30
    df = pd.DataFrame([[age, weight, height, gender]], columns=['age', 'weight', 'height', 'gender'])
    pred = model.predict(df)[0]
    proba = model.predict_proba(df)[0][1]
    return "High Risk" if pred == 1 else "Normal Risk", float(proba)

def predict_hypertension_risk(age, systolic, diastolic, lifestyle_score):
    model = get_model('hypertension_risk_model')
    if not model:
        return "High Risk" if systolic >= 140 or diastolic >= 90 else "Normal Risk", 0.40
    df = pd.DataFrame([[age, systolic, diastolic, lifestyle_score]], 
                      columns=['age', 'systolic', 'diastolic', 'lifestyle_score'])
    pred = model.predict(df)[0]
    proba = model.predict_proba(df)[0][1]
    return "High Risk" if pred == 1 else "Normal Risk", float(proba)

def predict_lifestyle_risk(smoking, alcohol, physical_activity, sleep_hours):
    model = get_model('lifestyle_risk_model')
    if not model:
        score = smoking * 30 + alcohol * 20 - physical_activity * 3 + (8 - sleep_hours) * 5 + 40
        return float(np.clip(score, 0, 100))
    df = pd.DataFrame([[smoking, alcohol, physical_activity, sleep_hours]], 
                      columns=['smoking', 'alcohol', 'physical_activity', 'sleep_hours'])
    score = model.predict(df)[0]
    return float(score)
