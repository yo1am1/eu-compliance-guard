# Tech stack

Recorded: 2026-10-18T19:01:39Z

Existing [pyproject.toml](../../pyproject.toml) defines Python 3.12+, Pydantic, uv.lock and Hatchling packaging. Prefer standard-library file/HTTP/CLI facilities and existing dependencies. Existing FastAPI/uvicorn dependencies do not require an API/server for this CLI unit.

[Makefile](../../Makefile) runs unittest, generated JSON Schema checks and TypeScript checks. Generate contracts from [models.py](../../eu_compliance_guard/models.py); the frontend consumes contracts and is not an MVP dashboard. No new database/service/provider is needed.

Canonical proposed architecture: [design](../../specs_v2/design.md), pending Owner review. These are repository-grounded standards, not construction approval.
