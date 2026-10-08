# Documentation Index — October 2026

**Where to Find Information About Tenga Inventory POS**

---

## Quick Navigation

### 🚀 Getting Started (New to the Project?)

1. **Start here:** [`00-implementation-state-current.md`](00-implementation-state-current.md)
   - 5-minute overview of what the system is
   - Architecture summary
   - What's implemented vs planned

2. **Then read:** [`ALIGNMENT_SUMMARY.md`](ALIGNMENT_SUMMARY.md)
   - Understanding the documentation alignment process
   - What changed between planning and implementation
   - Key discoveries about the system

---

## By Role

### 👨‍💼 Project Leads / Executives

**Understand the project status:**
- [`00-implementation-state-current.md`](00-implementation-state-current.md) — System overview
- [`ALIGNMENT_SUMMARY.md`](ALIGNMENT_SUMMARY.md) — What was planned vs built
- [`00-FINAL-VERIFICATION-REPORT.md`](00-FINAL-VERIFICATION-REPORT.md) — Comprehensive assessment

**Make decisions about Phase 2:**
- [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) — Critical design decisions
- [`final-decision-ledger.md`](final-decision-ledger.md) — All decisions (planning + implementation)
- [`testing-summary-status.md`](testing-summary-status.md) — Current status and blockers

---

### 👨‍💻 Developers

**Understand how the system works:**
- [`00-implementation-state-current.md`](00-implementation-state-current.md) — Architecture & modules
- [`implementation-business-rules.md`](implementation-business-rules.md) — Rules enforced in code (20 rules)
- [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) — Why key decisions were made

**Start working:**
- Go to `/docs/01-project-charter.md` for original project goals (still valid)
- Check `implementation-business-rules.md` for constraints
- See `testing-summary-status.md` for known issues to fix

**Deploy or manage database:**
- [`postgresql-migration-guide.md`](postgresql-migration-guide.md) — Complete database guide

---

### 🔧 DevOps / Database Administrators

**Database setup & migrations:**
- [`postgresql-migration-guide.md`](postgresql-migration-guide.md) — PostgreSQL setup, migrations, production procedures

**Deployment:**
- [`00-implementation-state-current.md`](00-implementation-state-current.md) — Deployment options section
- Quick start: SQLite (dev) or PostgreSQL (prod)

---

### 🧪 QA / Testing

**Test status:**
- [`testing-summary-status.md`](testing-summary-status.md) — 173 tests, 98 passing, 18 failing, known issues
- Current status: Core features passing, API/auth/offline have issues

**Verify critical decisions:**
- [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) — U006, U007, U008 verification status
- Grace periods: ✅ Well-tested
- Oversell logic: ✅ Core passing, conflicts ⚠️
- Offline optimism: ✅ Cache logic passing, manager ⚠️

---

## By Topic

### Business Model & Scope

| Topic | Document |
|-------|----------|
| Original project charter | [01-project-charter.md](01-project-charter.md) |
| Original requirements | [05-requirements-specification.md](05-requirements-specification.md) |
| Original MVP scope | [10-mvp-scope-definition.md](10-mvp-scope-definition.md) |
| What was actually built | [`00-implementation-state-current.md`](00-implementation-state-current.md) |
| Scope evolution (planned vs actual) | [`ALIGNMENT_SUMMARY.md`](ALIGNMENT_SUMMARY.md) |

### Architecture & Decisions

| Topic | Document |
|-------|----------|
| Current system architecture | [`00-implementation-state-current.md`](00-implementation-state-current.md) |
| Critical architectural decisions (U006-U008) | [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) |
| All project decisions | [`final-decision-ledger.md`](final-decision-ledger.md) |
| Business rules enforced | [`implementation-business-rules.md`](implementation-business-rules.md) |

### Implementation Details

| Topic | Document |
|-------|----------|
| What services/models exist | [`00-implementation-state-current.md`](00-implementation-state-current.md) |
| Database schema | [`00-implementation-state-current.md`](00-implementation-state-current.md) |
| Subscription state machine | [`implementation-business-rules.md`](implementation-business-rules.md) |
| Inventory & stock rules | [`implementation-business-rules.md`](implementation-business-rules.md) |
| POS & sales rules | [`implementation-business-rules.md`](implementation-business-rules.md) |
| Offline operation | [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) |

### Testing & Verification

| Topic | Document |
|-------|----------|
| Test status (173 tests) | [`testing-summary-status.md`](testing-summary-status.md) |
| Known failures & root causes | [`testing-summary-status.md`](testing-summary-status.md) |
| U006-U008 verification status | [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) |
| Remediation priority & steps | [`testing-summary-status.md`](testing-summary-status.md) |

### Database & Deployment

| Topic | Document |
|-------|----------|
| Database setup (SQLite & PostgreSQL) | [`postgresql-migration-guide.md`](postgresql-migration-guide.md) |
| Alembic migrations | [`postgresql-migration-guide.md`](postgresql-migration-guide.md) |
| Production deployment | [`postgresql-migration-guide.md`](postgresql-migration-guide.md) |
| Multi-environment setup | [`postgresql-migration-guide.md`](postgresql-migration-guide.md) |

### Planning & Unknowns

| Topic | Document |
|-------|----------|
| Original unknowns (planning phase) | [`unknowns-register.md`](unknowns-register.md) |
| Unknown resolution status | [`final-unknowns-register.md`](final-unknowns-register.md) |
| Naming collision clarification | [`final-unknowns-register.md`](final-unknowns-register.md) |
| Pilot readiness checklist | [`final-unknowns-register.md`](final-unknowns-register.md) |

---

## Special Topics

### 🚨 Naming Collision Alert

**Important:** The implementation uses IDs U006-U008 which collide with original unknowns.

- **Original U006-U008:** Planning questions (regulatory, Arrupe, count)
- **Implementation U006-U008:** POS decisions (oversell, grace, offline)

**Clarified in:**
- [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md)
- [`final-decision-ledger.md`](final-decision-ledger.md)
- [`final-unknowns-register.md`](final-unknowns-register.md)

### 📊 What Was Planned vs What Was Built

| Area | Planned | Built | Status |
|------|---------|-------|--------|
| Inventory management | ✅ | ✅ | Complete |
| POS sales | ❌ | ✅ | New (not in MVP) |
| Subscription billing | ❌ | ✅ | New (not in MVP) |
| Offline operation | Deferred | ✅ | Implemented (was deferred) |
| API layer | Not specified | ✅ | New |
| PostgreSQL | SQLite only | ✅ | Now supported |
| CSV import | ✅ Planned | ⏸️ | Deferred |
| ERP integration | ✅ Planned | ⏸️ | Deferred |

**Full comparison:** [`ALIGNMENT_SUMMARY.md`](ALIGNMENT_SUMMARY.md)

---

## Document Statistics

| Category | Count |
|----------|-------|
| Original planning documents (preserved) | 27 |
| New implementation documents | 7 |
| Enhanced existing documents | 2 |
| **Total markdown files** | **36** |
| Total size | ~420 KB |
| New documentation added | ~127 KB |

---

## Reading Recommendations by Time

### 5 Minute Overview
- [`00-implementation-state-current.md`](00-implementation-state-current.md) — First section only

### 15 Minute Deep Dive
- [`00-implementation-state-current.md`](00-implementation-state-current.md)
- [`ALIGNMENT_SUMMARY.md`](ALIGNMENT_SUMMARY.md) — Key discoveries section

### 1 Hour Full Understanding
- [`00-implementation-state-current.md`](00-implementation-state-current.md)
- [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md)
- [`implementation-business-rules.md`](implementation-business-rules.md)
- [`testing-summary-status.md`](testing-summary-status.md) — Known issues section

### Deep Expertise (All Areas)
- Start with [`00-implementation-state-current.md`](00-implementation-state-current.md)
- Then read each topic-specific document as needed
- Use this index to navigate

---

## Search Tips

Looking for something specific?

- **"Offline"** → [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) (U008)
- **"Oversell"** → [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) (U006)
- **"Grace"** → [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md) (U007)
- **"Test"** → [`testing-summary-status.md`](testing-summary-status.md)
- **"Database"** → [`postgresql-migration-guide.md`](postgresql-migration-guide.md)
- **"Business rules"** → [`implementation-business-rules.md`](implementation-business-rules.md)
- **"Naming collision"** → [`final-unknowns-register.md`](final-unknowns-register.md) or [`implementation-decisions-u006-u007-u008.md`](implementation-decisions-u006-u007-u008.md)
- **"Migration"** → [`postgresql-migration-guide.md`](postgresql-migration-guide.md)
- **"API"** → [`00-implementation-state-current.md`](00-implementation-state-current.md) — API Summary section

---

## Files in This Directory

### Core Implementation (Oct 8, 2026)

```
docs/
├── 00-implementation-state-current.md          ← START HERE (overview)
├── 00-FINAL-VERIFICATION-REPORT.md            ← Comprehensive assessment
├── ALIGNMENT_SUMMARY.md                       ← This alignment project
├── implementation-decisions-u006-u007-u008.md ← Critical decisions
├── implementation-business-rules.md           ← 20 enforced rules
├── postgresql-migration-guide.md              ← Database operations
├── testing-summary-status.md                  ← Test status & issues
└── INDEX.md                                   ← This file
```

### Original Planning (Pre-Implementation, Preserved)

```
├── 01-project-charter.md
├── 02-feasibility-study.md
├── 03-business-requirements-document.md
├── 04-product-requirements-document.md
├── 05-requirements-specification.md
├── 06-user-use-case-specification.md
├── 07-domain-data-requirements.md
├── 08-business-rules-specification.md
├── 09-ux-interaction-requirements.md
├── 10-mvp-scope-definition.md
├── 11-non-functional-requirements.md
├── 12-integration-future-requirements.md
├── 13-acceptance-criteria.md
├── 14-requirements-traceability-matrix.md
├── assumption-register.md
├── decision-ledger.md                         ← Updated with U006-U008
├── discovery-summary.md
├── final-assumption-register.md
├── final-decision-ledger.md                   ← Updated with U006-U008
├── final-unknowns-register.md                 ← Updated with status
├── mvp-definition-final.md
├── pilot-scoping-questionnaire.md
├── requirements-validation-final.md
├── requirements-validation-report.md
├── system-model.md
├── system-understanding.md
└── unknowns-register.md
```

---

## Last Updated

- **Status Documents:** October 8, 2026 16:48 UTC+2
- **All Original Documents:** Preserved as-is from previous update
- **Enhanced Documents:** 2 (decision-ledger.md, unknowns-register.md)

---

## Questions?

See the document that matches your interest above, or:
- For architecture: Read `00-implementation-state-current.md`
- For decisions: Read `implementation-decisions-u006-u007-u008.md`
- For rules: Read `implementation-business-rules.md`
- For tests: Read `testing-summary-status.md`
- For database: Read `postgresql-migration-guide.md`

---

**Status:** ✅ Complete  
**Scope:** Documentation only (no source code modified)  
**Ready for:** Development, pilot deployment, production scaling
