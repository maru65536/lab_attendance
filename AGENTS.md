# Repository Guidelines

## Project Structure & Module Organization
- `site-root/` holds the static top-level menu served at `/`; keep assets idempotent so deploys can mirror safely.
- `apps/lab-attendance/backend/` contains the FastAPI service; never commit generated SQLite files such as `attendance.db`.
- `apps/lab-attendance/frontend/` is the Next.js + TypeScript client; colocate component-specific assets and rely on the repo ESLint settings.
- `infra/server/terraform/` defines shared server resources; edit only the `.tf` sources and let Terraform own `terraform.tfstate*`.
- `scripts/` stores operational helpers like `deploy_lab_attendance.sh`; assume scripts run from the repo root.
- `migration-backup/` archives historic snapshots—treat as read-only reference material.

## Build, Test, and Development Commands
- Backend bootstrap: `cd apps/lab-attendance/backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Run FastAPI locally: `uvicorn main:app --app-dir apps/lab-attendance/backend --reload --port 8000` (or `python apps/lab-attendance/backend/main.py`).
- Frontend setup: `cd apps/lab-attendance/frontend && npm install`.
- Frontend dev server: `npm run dev` (http://localhost:3000) with API calls proxied to `/lab_attendance`.
- Linting: `npm run lint` must pass before sending changes; use `--fix` only after reviewing diffs.

## Coding Style & Naming Conventions
- Python: adhere to PEP 8 with 4-space indents, snake_case, and explicit type hints on FastAPI endpoints/Pydantic models.
- Surface database side effects in docstrings and avoid hidden global state beyond the SQLite path constant.
- TypeScript: PascalCase component filenames, camelCase utilities/hooks, and explicit interfaces over `any`.
- Keep JSX minimal per component and lean on ESLint/Prettier defaults emitted by Next.js.

## Testing Guidelines
- Place backend tests under `apps/lab-attendance/backend/tests/` (pytest) covering enter/exit flows, duplicate suppression, and timestamp formatting.
- Frontend specs live in `apps/lab-attendance/frontend/__tests__/` using `@testing-library/react`, mirroring the component structure.
- Name tests after user journeys (e.g., `test_enter_exit_cycle.py`) and reset SQLite fixtures between cases.
- Run backend + frontend test suites and `npm run lint` before requesting review; document any skipped or flaky checks.

## Commit & Pull Request Guidelines
- Prefer imperative commit subjects (~50 chars) with optional wrapped bodies describing motivation and follow-up.
- Group related backend/frontend edits together; isolate Terraform or nginx changes so they can roll independently.
- PRs must call out behaviour changes, manual validation (API calls, UI screenshots), and link to tracking issues.
- Highlight backward-incompatible updates—schema migrations, infra mutations, config renames—in the PR summary and note rollout precautions.
