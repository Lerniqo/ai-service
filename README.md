# ai-service

FastAPI service with multi-environment configuration (development, testing, production) using pydantic-settings and python-dotenv.

## Features
- Environment-specific `.env.<environment>` files auto-loaded based on `ENV` variable
- Centralized settings in `app/config.py`
- Development hot-reload only in development
- Simple Makefile commands for each environment
- Strict settings management via Pydantic models
- Easily extendable for databases / external services

## Tech Stack
- Python 3.13+
- FastAPI / Starlette
- Pydantic v2 / pydantic-settings
- Uvicorn
- python-dotenv

## Project Structure
```
.
├── app
│   ├── __init__.py
│   ├── config.py          # Settings management & env loading
│   └── main.py            # FastAPI application instance
├── run.py                 # Entrypoint that starts uvicorn with settings
├── Makefile               # Convenience commands per environment
├── .env.development       # Env vars for development
├── .env.testing           # Env vars for testing
├── .env.production        # Env vars for production
├── requirements.txt       # Locked dependencies (pip)
└── README.md
```

## Prerequisites
- Python 3.13 (adjust if needed)
- pip
- (Optional) A virtual environment tool: `venv`, `pyenv`, or `uv`

## Setup
```bash
# 1. Clone repository
git clone <repo-url>
cd ai-service

# 2. Create & activate virtual environment (example with venv)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pick / review environment file
cp .env.development .env.development.local  # (optional) override pattern
```

## Environment Selection
The active environment is determined by the `ENV` variable (defaults to `development`). The loader reads `.env.<ENV>`.

Example: if `ENV=testing` then `.env.testing` is loaded before settings validation.

## Core Environment Variables
| Name | Description | Default (in code) | Typical Overrides |
|------|-------------|-------------------|-------------------|
| ENV | Current environment (`development`, `testing`, `production`) | development | Deployment target |
| APP_NAME | FastAPI title | MyApp | Branding |
| APP_VERSION | Application version | 1.0.0 | Release version |
| APP_DESCRIPTION | Docs description | This is my app | Documentation |
| HOST | Bind host | 127.0.0.1 | 0.0.0.0 in containers |
| PORT | Bind port | 8000 | 80 / 8080 in deployment |
| RELOAD | Enable autoreload (dev only) | False | True in `.env.development` |

Add new settings in `Settings` (in `app/config.py`) then expose via env file.

## Running (Make Targets)
```bash
make start-dev   # development (reload enabled if RELOAD=true in .env.development)
make start-test  # testing
make start-prod  # production
```

## Running (Manual)
```bash
ENV=development python run.py
ENV=testing python run.py
ENV=production python run.py
```

## API Quick Test
After starting (default dev):
```bash
curl http://127.0.0.1:8000/
```
Expected JSON:
```json
{"message": "Welcome to MyApp!"}
```

## Extending Configuration
1. Add a field to `Settings` in `app/config.py` with `Field(..., env="VARIABLE_NAME")`.
2. Add the variable to your `.env.<environment>` files.
3. Access via `from app.config import get_settings` then `settings.NEW_FIELD`.

## Development Tips
- Use `reload` only in development to avoid performance overhead.
- Cache settings via `@lru_cache` (already implemented) to prevent re-parsing.
- Keep secrets out of VCS: create `.env.*.local` variants and gitignore them.

## Deployment Notes
- Set `HOST=0.0.0.0` and adjust `PORT`.
- Use a process manager (e.g., `gunicorn` with `uvicorn.workers.UvicornWorker`) for production if scaling.
- Ensure only production-safe dependencies are installed in the deploy image.

Example gunicorn command:
```bash
gunicorn -k uvicorn.workers.UvicornWorker app.main:app -b 0.0.0.0:8000 --workers 4
```
## References
- FastAPI Docs: https://fastapi.tiangolo.com/
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Uvicorn: https://www.uvicorn.org/

