#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing requirements..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

# Optional: pre-populate mock ML models on deploy
echo "Generating mock ML models..."
python -m ml.training_pipeline.train

echo "Render build completed successfully!"
