# AI Healthcare Platform Upgrade - Installation & Setup Guide

This guide provides instructions on how to configure and run the newly added AI Healthcare modules.

## 1. Prerequisites

You must have the new requirements installed.
```bash
pip install -r requirements.txt
```
This installs the new dependencies:
- `google-generativeai` (For the Gemini integration)
- `numpy` (For the fast local JSON vector store calculations)

## 2. API Keys

The AI module relies on Google Gemini.
Obtain a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
Add the following to your `.env` file (or set as environment variables):
```env
GEMINI_API_KEY=your_real_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```

## 3. Database Migrations

You must run migrations to create the AI Chat History tables.
```bash
python manage.py makemigrations
python manage.py migrate
```

## 4. Populating the Knowledge Base (Optional)

The RAG system requires clinical data to augment the assistant's responses.
A helper script is provided to ingest base medical information:
```bash
python -m ai.rag.knowledge_base
```
*This will chunk the text, generate embeddings using Gemini `embedding-001`, and save them to `ai/rag/vector_index.json`.*

## 5. Starting the Application

Start your Django development server normally:
```bash
python manage.py runserver
```

## 6. Accessing the Features

- **AI Chatbot**: Click the floating chat bubble on the bottom right of any page. You can type or use the Microphone icon for Speech-to-Text. The bot will automatically reply, and you can click the speaker icon to hear Text-to-Speech playback.
- **Report Explainer / Prescription Explainer**: Accessible via the Medical Report Center. Uploading a report will automatically trigger the AI analyzer.
