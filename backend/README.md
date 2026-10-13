# ModelMesh AI — Backend

FastAPI gateway service. See the [root README](../README.md) for architecture and roadmap.

## Setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/v1/health

## Checks

```bash
pytest
ruff check .
ruff format --check .
mypy app
```
