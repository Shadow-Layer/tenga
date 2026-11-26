# Documentation Index

This index is navigation, not a release or test report. As of **2026-11-11**,
inventory, offline, and POS work remains under active integration; full
production acceptance is pending. No suite-pass claim is made here. Historical
status documents and verification counts below are records of earlier
snapshots, not evidence about the current working tree.

## Start here

- [Root README](../README.md) — actual development and Compose paths, secrets,
  migrations, recovery, verification commands, and readiness caveats.
- [Repository reconnaissance](REPOSITORY_RECONNAISSANCE.md) — source-based
  overview, with current status separated from dated findings.
- [Installation bootstrap](INSTALLATION_BOOTSTRAP.md) — one-time creation of
  an organization and first local administrator on an empty database.
- [Initial setup wizard manual](INITIAL_SETUP_WIZARD.md) — setup and import
  guidance, including known manual/UI mismatches.

## Operations and verification

- [PostgreSQL migration guide](postgresql-migration-guide.md) — database
  operation notes; verify instructions against the current scripts and schema.
- [Testing summary status](testing-summary-status.md) — **historical** test
  snapshot; do not use its counts as current results.
- [Final verification report](00-FINAL-VERIFICATION-REPORT.md) — historical
  assessment, not current release acceptance.
- [Implementation state document](00-implementation-state-current.md) —
  historical implementation snapshot; its completion labels may be stale.

The current script entry points are [`../scripts/migrate-db.sh`](../scripts/migrate-db.sh)
and [`../scripts/backup.sh`](../scripts/backup.sh). Their tested mocked paths
must not be confused with real PostgreSQL/runtime verification.

## Decisions and project history

These documents preserve requirements, decisions, and implementation history.
They are not a current completion checklist:

- [Production readiness implementation contracts](PRODUCTION_READINESS_IMPLEMENTATION_CONTRACTS.md)
- [Implementation decisions U006–U008](implementation-decisions-u006-u007-u008.md)
- [Final decision ledger](final-decision-ledger.md)
- [Final unknowns register](final-unknowns-register.md)
- [Original project charter](01-project-charter.md)
- [Requirements specification](05-requirements-specification.md)
- [Acceptance criteria](13-acceptance-criteria.md)
- [Design and alignment summary](ALIGNMENT_SUMMARY.md)

For the full set of preserved planning documents, see the files in this
directory. Older documents that describe inventory, offline, POS, or imports as
complete retain their historical wording; current implementation completion
must be established separately with current tests and runtime evidence.
