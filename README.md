# mrhost-guest-qr-backend

FastAPI backend that powers the MrHost Guest QR → Consent → Guide flow. It exposes public endpoints for guests and authenticated admin endpoints for managing content.

## Features

- QR token generation and validation for listings with per-code consent toggles.
- Versioned, multi-language consent templates with publish workflow.
- Guest consent logging with email capture plus IP/user agent metadata.
- Localized FAQs (with optional links) and tutorial videos with language fallback to English.
- Optional page descriptions for listing overviews with translation support.
- JWT-protected admin APIs for managing listings, content, and consent logs.
- Health check endpoint for monitoring.

## Getting Started

### Prerequisites

- Python 3.11+
- (Optional) Docker and Docker Compose for containerized workflows.

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Running the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. API docs can be accessed at `/docs`.

### Running Tests

```bash
pytest
```

Tests cover QR token signing, consent submission, language fallbacks, admin authentication, and Alembic migrations for SQLite and Postgres (offline mode).

### Database Migrations

Initialize the database schema using Alembic:

```bash
alembic upgrade head
```

To generate a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

### Environment Configuration

Use `.env.example` for local development (SQLite). For production deployments with Postgres, refer to `.env.production.example` and adjust credentials as necessary.

## Docker

### Development (SQLite)

```bash
docker compose -f docker-compose.dev.yml up --build
```

Run database migrations in the running container:

```bash
docker compose -f docker-compose.dev.yml exec api alembic upgrade head
```

### Production (Postgres)

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Project Structure

```
app/
  api/          # FastAPI routers for public and admin APIs
  core/         # Application configuration
  db/           # Database session management
  models/       # SQLAlchemy models
  schemas/      # Pydantic schemas
  services/     # Domain services (QR tokens, etc.)
  utils/        # Security helpers
alembic/        # Migration scripts
tests/          # Pytest suite
```

## License

MIT
