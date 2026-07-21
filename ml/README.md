# DocMed — ML Pipeline Module

This directory is the placeholder for future machine learning models and predictors.

## Current Status: Scaffold Only

No trained models are included. This structure is designed for future integration.

## Directory Structure

```
ml/
├── README.md              # This file
├── __init__.py
├── predictors/
│   ├── __init__.py
│   └── base.py            # Abstract base class for all predictors
└── data/                  # (gitignored) Training data and model artifacts
```

## Planned ML Features (Phase 3+)

1. **Symptom-based Doctor Recommendation**
   - Input: Patient symptoms (text)
   - Output: Recommended department + top 3 doctors

2. **Appointment No-Show Prediction**
   - Input: Booking metadata (day, time, distance, history)
   - Output: Probability of no-show

3. **Medical Report Triage**
   - Input: OCR text from uploaded report
   - Output: Urgency level (Normal / Needs Attention / Critical)

## How to Add a Predictor

1. Subclass `BasePredictor` from `predictors/base.py`
2. Implement `load_model()` and `predict()` methods
3. Register in the factory if needed
