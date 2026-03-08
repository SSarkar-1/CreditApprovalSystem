# CreditApprovalSystem

Django + DRF backend for customer registration, loan eligibility checks, loan creation, and loan history, using PostgreSQL, Redis, and Celery.

## Tech Stack
- Python 3.11
- Django 5
- Django REST Framework
- PostgreSQL 15
- Redis 7
- Celery
- Docker Compose

## Project Structure
- `api/` - models, views, tasks, URLs
- `credit_approval/` - Django settings and root URLs
- `data/` - Excel files used for initial ingestion
- `docker-compose.yaml` - service orchestration
- `Dockerfile` - app image build

## Prerequisites
- Docker Desktop running
- Docker Compose v2 (`docker compose`)

## Environment Variables
Create a `.env` file in project root:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=credit_db
```

Notes:
- `.env` is already ignored by `.gitignore`.
- Never commit real passwords or secrets.

## Run Locally (Docker)

```bash
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## API Endpoints
- `POST /register`
- `POST /check-eligibility`
- `POST /create-loan`
- `GET /view-loan/<loan_id>`
- `GET /view-loans/<customer_id>`

## Data Ingestion
On startup, web service runs:
1. `python manage.py migrate`
2. `python manage.py ingest_data`
3. starts Django server

Celery tasks used:
- `api.tasks.ingest_customer_data`
- `api.tasks.ingest_loan_data`

## Common Issues

### 1) `FATAL: the database system is in recovery mode`
Cause: PostgreSQL is recovering after an unclean shutdown.
Fix:
- Wait for log: `database system is ready to accept connections`
- Restart cleanly:

```bash
docker compose down
docker compose up -d
```

### 2) `duplicate key value violates unique constraint api_customer_pkey`
Cause: sequence drift after explicit ID ingestion.
Fix: sequence is synced in `api/tasks.py` after ingestion.

### 3) `null value in column "first_name"`
Cause: trailing blank rows in Excel interpreted as `None` rows.
Fix: ingestion skips blank/malformed rows in `api/tasks.py`.

## Security Checklist Before Pushing to GitHub
- Keep `.env` out of git (already configured).
- Remove hardcoded passwords/secrets from code.
- Rotate credentials if they were committed earlier.
- Add and maintain `.env.example` with placeholder values only.

## Development Commands

```bash
# Rebuild images
docker compose up -d --build

# See logs
docker compose logs -f web
docker compose logs -f celery
docker compose logs -f db

# Stop services
docker compose down
```

