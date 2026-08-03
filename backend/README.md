# Backend — Core

FastAPI async + SQLAlchemy 2.x + Alembic + PostgreSQL + Redis.

## Desarrollo local

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Calidad

```bash
ruff check . && ruff format .
mypy app
pytest
```

## Migraciones

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```
