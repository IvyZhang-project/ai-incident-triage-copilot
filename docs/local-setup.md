# Local Setup

## Current Status

The project skeleton exists, but Python dependencies are not installed yet.

## Backend Setup

From the project root:

```text
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:

```text
http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "ai-incident-triage-copilot",
  "version": "0.1.0"
}
```

## Why We Use a Virtual Environment

A virtual environment keeps this project's Python packages separate from your computer's global Python installation.

