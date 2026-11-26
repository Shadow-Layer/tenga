# Tenga Inventory POS

Tenga is an inventory and point-of-sale application in active development. The
repository contains a FastAPI/SQLAlchemy backend, a React/TypeScript frontend,
Alembic migrations, and a Docker Compose deployment topology for PostgreSQL,
the API, and an Nginx-served frontend.

> **Readiness (2026-11-11):** This is not a production-ready release. Inventory,
> offline, and POS workflows are still being integrated; their presence in the
> source tree or isolated tests is not evidence of complete end-to-end
> acceptance. Customer and supplier returns are out of scope for this release.
> Full production acceptance remains pending. Paynow live
> credentials/provider confirmation and Zimbabwe FDMS/ZIMRA credentials,
> certification, and access are unavailable.

## Development

Use Python 3.14+ and Node.js 22+ (the versions used by the container builds).
From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ENVIRONMENT=dev DATABASE_URL=sqlite:///./tenga-dev.db \
  uvicorn src.main:app --reload
```

In another terminal:

```sh
npm ci
npm run dev
```

The development API initializes its SQLite schema on startup. The browser
frontend uses the API at `http://localhost:8000` by default; `VITE_API_URL` can
override that base URL. Do not use a production database for development or
tests.

## Compose deployment path

Compose is the repository's deployment topology, not a production-readiness
certification. Prepare the environment file and replace every example value:

```sh
cp .env.example .env
# Set strong, unique POSTGRES_PASSWORD and JWT_SECRET_KEY values.
# Set CORS_ORIGINS to the actual frontend origin and review all exposed ports.
docker compose --env-file .env config
docker compose --env-file .env up -d --build
docker compose --env-file .env ps
curl --fail http://127.0.0.1:8000/health
```

Compose runs PostgreSQL 16, the API, and the frontend. The API's host port is
bound to loopback; the frontend port is published on the host. The PostgreSQL
host port defaults to 5432 and is published on all host interfaces unless
deployment/network configuration restricts it. Apply appropriate firewall
rules, use TLS at the public edge, and do not expose the database to the
internet. `JWT_SECRET_KEY` must be a non-default secret of at least 32
characters; configure `CORS_ORIGINS` explicitly. `.env.example` contains
placeholders, including ZIMRA values; they are not working credentials. Keep
`.env` private and verify it is not staged for commit. The root `.gitignore`
excludes `.env` and common generated database, backup, cache, and build files.

For first-time organization and administrator creation, follow
[`docs/INSTALLATION_BOOTSTRAP.md`](docs/INSTALLATION_BOOTSTRAP.md). Bootstrap
is only for an empty database and uses `INITIAL_SETUP_SECRET`; do not send that
secret through the public frontend. The dashboard setup procedure is described
in [`docs/INITIAL_SETUP_WIZARD.md`](docs/INITIAL_SETUP_WIZARD.md), which has
known mismatches with the current UI noted in that manual.

## Database migrations and recovery

The API container runs `alembic upgrade head` before starting the API.
For an explicit migration operation on a running Compose stack, use
[`scripts/migrate-db.sh`](scripts/migrate-db.sh):

```sh
./scripts/migrate-db.sh --env-file .env --dry-run
./scripts/migrate-db.sh --env-file .env
```

The script requires running API and PostgreSQL services. Coordinate migration
execution with container startup; do not run two migration processes
concurrently. Downgrade application is disabled; `--rollback REVISION
--dry-run` only generates SQL. Back up first and use a verified recovery
procedure rather than downgrading live history.

[`scripts/backup.sh`](scripts/backup.sh) backs up and restores PostgreSQL to
local SQL/SQL.GZ files under `backups/` by default:

```sh
./scripts/backup.sh --backup --env-file .env
./scripts/backup.sh --list
./scripts/backup.sh --restore 'backups/tenga_TIMESTAMP.sql.gz' --env-file .env
./scripts/backup.sh --prune --retention 30
```

Restore overwrites the target database after an interactive `yes` confirmation.
Quiesce application writes, verify the selected backup, and rehearse recovery
against an isolated database before any production restore. These scripts do
not back up SQLite databases or the Compose volumes as a whole.

## Verification

The package scripts include `npm run type-check`, `npm run build`, and
`npm test -- --run`; `npm run build` writes to `dist/`. Python tests use
`python -m pytest`. Pytest fixtures drop/recreate their configured SQLite
database, so point them at a new path that does not already contain data:

```sh
mkdir -p .verification
SQLITE_PATH="$PWD/.verification/tenga-test.db" python -m pytest
```

The default test database is the repository's `tenga-test.db`. PostgreSQL
integration tests can create and drop tables in `TEST_POSTGRES_URL`, so use
only a dedicated disposable database.

`tests/test_production_scripts.py` normally uses mocked Docker/Compose commands:
those tests verify script behavior, not a live PostgreSQL backup, migration, or
restore. It contains a separate opt-in disposable-PostgreSQL test gated by
`RUN_DISPOSABLE_POSTGRES_SCRIPT_TESTS=1` and Docker Compose availability. That
**Verification snapshot (2026-11-13):** a clean Python 3.14 install from
`requirements.txt` passed the full backend suite (379 passed, 14 skipped)
against an isolated in-memory test database. Frontend tests (18),
type-checking, the production build, `npm audit`, and `pip-audit` passed with
zero dependency advisories after updating vulnerable packages. The local
frontend on `127.0.0.1:80` was rebuilt from the current source and checked in
a browser. It displays the organization sign-in screen without shared demo
accounts, has no browser console errors, and serves the manifest, service
worker, and health endpoint.
An isolated Compose installation completed the organization/setup and cash-sale
journey; after restarting only its API and PostgreSQL containers, aggregate
counts for the organization, users, products, sale, stock movements, and till
sessions were unchanged. The opt-in disposable-PostgreSQL backup/restore/
migration test also passed after the latest migration.

These checks do not establish production acceptance. The full browser journey
with native network-offline/reopen/inventory-sync and count-conflict scenarios,
representative populated-database upgrade, and live Paynow/FDMS/ZIMRA provider
behavior remain unverified. The existing `tenga-api` container is still using
an image created on 2026-11-07. An unauthenticated request to its organization
detail route returns 200, while the same route in the isolated current-source
stack returns 401; current source requires authentication. The old API is
still running PyJWT 2.8.0, python-jose 3.3.0 and ecdsa 0.19.2, which the
dependency audit flags; current requirements remove python-jose and update the
remaining vulnerable pins. The API is loopback-bound and was not restarted or
replaced to preserve existing data and configuration, but it must not be
externally exposed before a controlled redeploy. The existing `tenga-postgres`
container also publishes port 5432 on all host interfaces. The repository
Compose file binds PostgreSQL to loopback, but that existing container was not
recreated; restrict its exposure before external use.

## Documentation

- [`docs/INDEX.md`](docs/INDEX.md) — documentation navigation and status caveats
- [`docs/REPOSITORY_RECONNAISSANCE.md`](docs/REPOSITORY_RECONNAISSANCE.md) — source-based repository overview and readiness notes
- [`docs/INSTALLATION_BOOTSTRAP.md`](docs/INSTALLATION_BOOTSTRAP.md) — first-install organization and owner bootstrap
- [`docs/INITIAL_SETUP_WIZARD.md`](docs/INITIAL_SETUP_WIZARD.md) — setup wizard/import manual and verified discrepancies
- [`docs/PRODUCTION_READINESS_IMPLEMENTATION_CONTRACTS.md`](docs/PRODUCTION_READINESS_IMPLEMENTATION_CONTRACTS.md) — approved implementation constraints; not a completion report
- [`docs/testing-summary-status.md`](docs/testing-summary-status.md) — historical test snapshot, not current verification
