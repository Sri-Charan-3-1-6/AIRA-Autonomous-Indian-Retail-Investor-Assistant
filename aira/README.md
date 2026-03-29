# AIRA - Autonomous Indian Retail Investor Assistant

A production-grade FastAPI foundation for a multi-agent investment assistant focused on Indian retail investors.

## Project Layout

```
aira/
  main.py
  core/
  orchestrator/
  agents/
  models/
  api/
  db/
```

## Prerequisites

- Python 3.11+
- Supabase project (URL + keys)
- Gemini API key

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment file and fill values:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

4. Run SQL migration in Supabase SQL editor:

- Execute `db/migrations/001_initial_schema.sql`

5. Start API server:

```bash
uvicorn main:app --reload
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

If Supabase credentials are missing or invalid, `/health` will report `supabase.status` as `unhealthy`.

## Main Endpoints

- `GET /health`
- `POST /user/register`
- `GET /user/{user_id}`
- `POST /orchestrate/run`

## Docker

```bash
docker compose up --build
```

The compose setup includes a local Postgres container using Supabase Postgres image and the FastAPI service.
