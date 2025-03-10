# AI-Enhanced Obsidian-like Knowledge Base API Setup Guide

This guide covers the setup process for the AI-enhanced knowledge management API, including the basic version and the enhanced version with LLM and embedding capabilities.

## 1. Basic Setup (Required)

### Install Core Dependencies

```bash
pip install flask flask-cors pymongo networkx python-dateutil
```

### Configure MongoDB

Ensure MongoDB is installed and running on your machine or provide a connection string to your MongoDB instance.

### Start the API Server

```bash
python app.py
```

By default, this will run the API in basic mode without AI features.

## 2. Enhanced Setup with AI Features (Optional)

### Install Additional Dependencies

Uncomment and install the additional requirements in `requirements.txt`:

```bash
pip install openai sentence-transformers scikit-learn numpy
```

### Configure Environment Variables

Set up your OpenAI API key:

```bash
export OPENAI_API_KEY=your_api_key_here
```

For Windows:

```powershell
$env:OPENAI_API_KEY = "your_api_key_here"
```

### Start the API Server

```bash
python app.py
```

The API will automatically detect the available AI dependencies and enable those features.

## 3. API Structure

The API consists of several key components:

- `app.py`: Main Flask application with API endpoints
- `llm_integration.py`: LLM controller for AI-powered metadata generation
- `semantic_search.py`: Embedding-based semantic search
- `memory_evolution.py`: System for evolving knowledge connections

## 4. Folder Structure

```
knowledge-api/
├── app.py                  # Main application
├── llm_integration.py      # LLM integration
├── semantic_search.py      # Embedding-based search
├── memory_evolution.py     # Memory evolution system
├── mongodb_schema.py       # Database schema setup
├── requirements.txt        # Dependencies
└── example_client.py       # Example client usage
```

## 5. Testing the API

Use the included `example_client.py` to test the API functionality:

```bash
python example_client.py
```

## 6. AI Features Overview

When AI features are enabled, the API provides:

1. **Automatic Metadata Generation**:
   - Keywords extraction
   - Context identification
   - Tag suggestions

2. **Semantic Search**:
   - Find notes by meaning, not just keywords
   - Hybrid search combining text and semantic matching

3. **Memory Evolution**:
   - Automatic connection between related notes
   - Tag propagation to similar notes
   - Context refinement based on new information

4. **Importance Scoring**:
   - Notes are scored by importance (0.0-2.0)
   - Retrieval tracking to identify frequently accessed notes

## 7. Configuration Options

You can configure the API by modifying parameters in:

- `llm_integration.py`: Change LLM model, provider, etc.
- `semantic_search.py`: Change embedding model
- `memory_evolution.py`: Adjust evolution thresholds

## 8. Running in Production

For production deployment:

1. Use a production WSGI server (Gunicorn, uWSGI)
2. Set up proper authentication
3. Configure MongoDB with authentication and proper security measures
4. Set DEBUG=False in the Flask app

Example production start command with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```