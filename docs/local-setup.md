# Local Setup

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env` only when running full LLM analysis. Retrieval,
deterministic fallback, and the default test suite work without it.

## Run

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

Verify `http://localhost:8000/health` or open
`http://localhost:8000/docs` for the generated API interface.

## Test

From the repository root:

```bash
./.venv/bin/python -m pytest -q
```

The default suite is offline and does not call OpenAI.

## Generate Evaluation Reports

```bash
cd backend
../.venv/bin/python -m app.eval_report
../.venv/bin/python -m app.eval_report --run-analysis
```

The second command uses the configured OpenAI API and incurs API usage.
