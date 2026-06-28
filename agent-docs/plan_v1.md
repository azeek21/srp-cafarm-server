# Animal (Cattle) Management System — Server Plan

## Context

`srp-cafarm-server` is the server for a single-farmer livestock management system. The client
(React 19 + TanStack Router/Query/Table/Form) lives in a separate repo. The repo is currently
empty except `README.md` and `.gitignore` — this is a greenfield build at the **repo root**.

Stack: **Python + FastAPI + SQLModel**, sync sessions via **psycopg**, **local PostgreSQL**,
tooling via **uv + ruff**. Layout is domain-oriented and layered: **router → service →
repository**.

Scope: animal CRUD, browsing (search/filter/sort/pagination), analytics, and a seed script.

## Data Model

`Animal` (table `animal`):
- `id: UUID` — PK, `default_factory=uuid4`.
- `type: AnimalType` — enum `CATTLE` (extensible), indexed.
- `tag: str` — free-form alphanumeric ear-tag / ID (real-world tags contain letters, e.g.
  `UK123456700123`).
- `name: str | None` — optional.
- `breed: str` — indexed.
- `gender: Gender` — enum `MALE | FEMALE`.
- `date_of_birth: date`.
- `status: AnimalStatus` — enum `ACTIVE | SOLD | DECEASED`, default `ACTIVE`, indexed.
- `status_changed_at: datetime | None` — nullable UTC; set by service whenever `status` changes.
  Single field scales to any future status (vs one column per status). Stores last transition
  only; full history is out of scope.
- `note: str | None` — nullable free-form text (`varchar`) for farmer notes on the animal.
- `created_at / updated_at: datetime` — UTC.
- `deleted_at: datetime | None` — nullable, **indexed**; `NULL` = live, non-null = soft-deleted.
- **Partial unique index** on `(type, tag) WHERE deleted_at IS NULL`.

`age_years` is derived from `date_of_birth` at read time (not stored).

## Architecture

```
client (TanStack Table, sends type=cattle) ── HTTP+JSON, CORS ──┐
                                                                ▼
app/main.py ── FastAPI (lifespan: init_db) + CORS + /health, mounts routers
        ├── animals/router.py    (/api/animals)
        └── analytics/router.py  (/api/analytics)
                 │ Depends(get_*_service) wires session → repository → service
                 ▼
            service     business rules; raises domain exceptions (NotFoundError / ConflictError)
                 ▼
            repository  data access: filters, sort, pagination, COUNT, GROUP BY;
                        applies deleted_at IS NULL to every read
                 ▼
            database.py (engine, get_session) ◄── config.py (Settings)
                 ▼
            local PostgreSQL

main.py also registers app-level exception handlers: NotFoundError → 404, ConflictError → 409.
```

- **router**: parse query/body, call service, return response model. **No status-code logic** —
  handlers never `try/except` domain errors.
- **service**: business rules — duplicate `(type, tag)` check, set `updated_at` on edit,
  status-transition stamping (set `status_changed_at = now()` whenever `status` changes),
  soft-delete, assemble analytics summary (buckets, average) from
  repository counts. Stays
  HTTP-agnostic: raises **domain exceptions** (`NotFoundError`, `ConflictError` from
  `app/exceptions.py`), never `HTTPException`.
- **repository**: all SQL/SQLModel access. A single private helper builds the base `select` with
  `deleted_at IS NULL` so soft-deleted rows are uniformly excluded; `delete` sets
  `deleted_at`/`updated_at` instead of removing the row.
- **exception handlers**: `app/exceptions.py` defines the domain exceptions and a
  `register_exception_handlers(app)` that maps them to HTTP responses, called once in `main.py`.
- **DI**: provider fns (e.g. `get_animal_service`) chain `Depends(get_session)` →
  `AnimalRepository(session)` → `AnimalService(repo)`.

## Endpoints

**Animals** (`app/animals/router.py`, prefix `/api/animals`):
- `POST /` — create. Body `AnimalCreate` (includes `type`). **409** on duplicate
  `(type, tag)`. Returns `AnimalRead`.
- `GET /` — list → `{ items: AnimalRead[], total, page, page_size }`. Query params:
  - `type`, `search` (case-insensitive `ILIKE` over `tag`/`name`/`breed`),
  - `breed`, `gender`, `status` (exact), `born_after`, `born_before` (date range),
  - `sort_by` ∈ `tag|breed|date_of_birth|status|created_at` (default `created_at`),
    `sort_order` ∈ `asc|desc` (default `desc`),
  - `page` (default 1, ≥1), `page_size` (default 20, capped 100).
  `total` is a `COUNT` over the same filters (pre-pagination).
- `GET /{id}` — fetch one. **404** if missing/soft-deleted.
- `PATCH /{id}` — partial update. Body `AnimalUpdate` (all optional). Touches `updated_at`.
  **404** / **409** (tag collision among live animals of that type).
- `DELETE /{id}` — **soft delete**: sets `deleted_at = now()` and `updated_at`. **204** / **404**
  (404 if missing or already soft-deleted).

**Analytics** (`app/analytics/router.py`, prefix `/api/analytics`):
- `GET /summary?type=cattle` → `AnalyticsSummary`:
  - `total`, `active_total`,
  - `by_status`, `by_breed`, `by_gender` (count maps via SQL `GROUP BY`),
  - `age_distribution` — buckets calf `<1y`, young `1–2y`, adult `>2y`,
  - `average_age_years`.
  Counts computed in SQL; bucket/average shaping in the service.

## Project Structure (repo root)

```
pyproject.toml            # fastapi, uvicorn[standard], sqlmodel, psycopg[binary],
                          #   pydantic-settings ; dev: ruff
README.md                 # setup, run, decisions, assumptions, future work
.env.example              # DATABASE_URL (local PG), CORS_ORIGINS
app/
  __init__.py
  main.py                 # FastAPI app, lifespan(init_db), CORS, register_exception_handlers,
                          #   mount routers, GET /health
  config.py               # Settings (pydantic-settings): DATABASE_URL, CORS_ORIGINS
  database.py             # engine, get_session dependency, init_db()
  exceptions.py           # NotFoundError, ConflictError + register_exception_handlers(app)
  animals/
    __init__.py
    models.py             # Animal + AnimalType / Gender / AnimalStatus enums
    schemas.py            # AnimalCreate, AnimalUpdate, AnimalRead (+age_years),
                          #   AnimalListResponse, AnimalListParams
                          #   note is client-writable; status_changed_at is server-set
                          #   (read-only in AnimalRead, not in Create/Update)
    repository.py         # AnimalRepository: CRUD + filtered/paginated query + COUNT + GROUP BY
    service.py            # AnimalService
    router.py             # handlers + get_animal_service
  analytics/
    __init__.py
    schemas.py            # AnalyticsSummary
    service.py            # AnalyticsService
    router.py             # handler + DI provider
  seed.py                 # python -m app.seed — ~30–50 sample animals (type=cattle)
```

- Enums in `animals/models.py`, reused by schemas. `AnimalRead.age_years` is a computed field.
- `seed.py` uses stdlib `random` + a breed list and inserts through `AnimalService.create`.
- Analytics aggregation queries live in `AnimalRepository`; `AnalyticsService` shapes the summary.

## Implementation Order
1. `pyproject.toml`, `.env.example`.
2. `app/config.py` + `app/database.py` + `app/exceptions.py`.
3. `app/animals/models.py` (enums + `Animal` + indexed `deleted_at` + partial unique index on
   `(type, tag) WHERE deleted_at IS NULL`).
4. `app/animals/schemas.py`.
5. `app/animals/repository.py`.
6. `app/animals/service.py` (raises domain exceptions) + `app/animals/router.py`.
7. `app/analytics/{schemas,service,router}.py`.
8. `app/main.py` (incl. `register_exception_handlers`).
9. `app/seed.py`.
10. `README.md`.

## Verification
1. Local Postgres running and the DB in `DATABASE_URL` exists (`createdb cattle`).
2. `uv sync`.
3. `cp .env.example .env`, adjust `DATABASE_URL`.
4. `uv run uvicorn app.main:app --reload` → `:8000`; `GET /health` ok (tables created on startup).
5. `uv run python -m app.seed`.
6. `http://localhost:8000/docs`: create → list (`type`, `search`, `status`, `sort_by`, `page`) →
   get → patch → delete (then confirm it disappears from list).
7. `GET /api/analytics/summary?type=cattle` returns non-empty aggregates.
8. CORS: configured client origin can call the API without browser errors.
9. `uv run ruff check .` clean.

## Out of Scope (note in README)
- Auth / multi-farm tenancy.
- Automated tests (pytest) — recommended next step.
- Hard-purge / GDPR erasure of soft-deleted rows; audit history.
- Additional `AnimalType`s, async DB driver, pagination cursors, richer/time-series analytics.
