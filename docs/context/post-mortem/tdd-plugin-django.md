# Post-Mortem: T-009 — Django Plugin

**Date:** June 21, 2026  
**Status:** ✅ COMPLETE  
**Review Status:** APPROVE (after 2 TDD review rounds + 1 code review round)

---

## 1. Overview

### Original Ticket
**Title:** Create the Django bundled plugin

**Original Acceptance Criteria (19 ACs in ticket v1):**
```markdown
AC-01: plugin.name returns 'django'
AC-02a: files() returns core file paths (manage.py, config/settings.py, config/urls.py, config/wsgi.py, requirements.txt)
AC-02b: PluginExecutionEngine (simulated) stages core files and appends deps
AC-03: questions() returns proper keys (database, include_drf), types (CHOICE, BOOLEAN), options, uniqueness
AC-04: database=postgresql → postgresql ENGINE + psycopg2-binary in requirements.txt
AC-05: database=sqlite → sqlite3 ENGINE + no database packages
AC-06: database=mysql → mysql ENGINE + mysqlclient in requirements.txt
AC-07: include_drf=True → rest_framework in INSTALLED_APPS + djangorestframework in requirements.txt
AC-08: include_drf=False/absent → no rest_framework
AC-09: directories() returns config/, apps/, static/, templates/
AC-10: dependencies() base set ['django>=5.1']
AC-11: dependencies() with DRF includes djangorestframework>=3.15
AC-12: dependencies() with postgresql includes psycopg2-binary>=2.9
AC-13: generate() calls executor.run() with uv add django>=5.1
AC-14: generate() with DRF includes djangorestframework>=3.15
AC-15: empty config dict → SQLite defaults, no extra deps
AC-16: missing 'django' key → no exception, defaults
AC-17: invalid database value → ValidationEngine error
AC-18: display_name='Django', description non-empty
AC-19: DjangoPlugin importable from forge.plugins.django
```

**Original api_spec:**
```python
class DjangoPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "django"
    display_name = "Django"
    description = "Django backend with choice of database + DRF"
    requires: list[str] = []

    def questions(self):   # database: CHOICE [postgresql, sqlite, mysql], include_drf: BOOLEAN
    def files(self):       # manage.py, config/settings.py, config/urls.py, config/wsgi.py, requirements.txt
    def directories(self): # config/, apps/, static/, templates/
    def generate(self, spec, target_dir, executor): ...
    def dependencies(self): # django>=5.1 + conditional packages
```

### Refined Acceptance Criteria (21 ACs after 2 TDD review rounds)

```
AC-01:  plugin.name returns 'django'
AC-02a: files() returns core file paths (manage.py, config/settings.py, config/urls.py, config/wsgi.py, requirements.txt) as GeneratedFile with Path objects
AC-02b: PluginExecutionEngine (simulated) stages files via txn.stage_file() and appends deps to txn.requirements
AC-03:  questions() returns keys 'database' (CHOICE, options exactly ["postgresql", "sqlite", "mysql"]) and 'include_drf' (BOOLEAN); all keys unique
AC-04:  database=postgresql → "ENGINE": "django.db.backends.postgresql" in settings.py, psycopg2-binary>=2.9 in requirements.txt
AC-05:  database=sqlite → "ENGINE": "django.db.backends.sqlite3" in settings.py, no psycopg2-binary or mysqlclient in requirements.txt
AC-06:  database=mysql → "ENGINE": "django.db.backends.mysql" in settings.py, mysqlclient>=2.2 in requirements.txt
AC-07:  include_drf=True → "rest_framework" in INSTALLED_APPS, djangorestframework>=3.15 in requirements.txt
AC-08:  include_drf=False or absent → no "rest_framework" in INSTALLED_APPS, no djangorestframework in requirements.txt
AC-09:  directories() contains config/, apps/, static/, templates/
AC-10:  dependencies() returns ['django>=5.1'], excludes djangorestframework, psycopg2-binary, mysqlclient (SQLite default)
AC-11:  dependencies() with include_drf=True includes djangorestframework>=3.15 AND still includes django>=5.1
AC-12:  dependencies() with database=postgresql includes psycopg2-binary>=2.9 AND still includes django>=5.1
AC-13:  generate() calls executor.run() with command containing ["uv", "add", "django>=5.1"] and passes cwd=target_dir
AC-14:  generate() with include_drf=True includes djangorestframework>=3.15
AC-15:  generate() with database=postgresql includes psycopg2-binary>=2.9
AC-16:  generate() with database=mysql includes mysqlclient>=2.2
AC-17:  empty config dict → SQLite defaults, no extra deps (cross-method: files + dependencies)
AC-18:  missing 'django' key → no exception, defaults used (files + directories + dependencies)
AC-19:  invalid database value → ValidationEngine.validate_plugin_config() returns ValidationError with severity='error'
AC-20:  display_name='Django', description non-empty string
AC-21:  DjangoPlugin importable from forge.plugins.django
```

---

## 2. Problems Identified

### TDD Review Round 1 — CHANGES REQUESTED (2 blocking + 10 non-blocking issues)

The initial ticket was reviewed against the existing codebase infrastructure (plugin base classes, mixin signatures, generation stages, AC-4 scanner):

#### Blocking Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| AC-2 conflated `generate()` with `files()` | **Blocking** | AC-2 described file output behavior ("creates files") but `generate()` returns `None` per the CommandRunner interface. `files()` is the FileProvider method that returns `GeneratedFile` objects. The AC as written would require a `generate()` implementation that returns file objects — impossible under the existing mixin contract |
| `dependencies(self)` signature wrong | **Blocking** | API spec showed `def dependencies(self)` but the actual interface (changed during T-008) is `def dependencies(self, spec: ProjectSpec) -> list[str]`. Would cause `TypeError` at runtime when `PluginExecutionEngine` calls `plugin.dependencies(spec)` |

#### Non-Blocking Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| API spec `generate()` missing `executor` param | **Non-blocking** | Pseudocode showed `def generate(self, spec, target_dir)` but CommandRunner mixin requires executor param. AC-4 scanner constraint requires untyped `executor: Any` |
| AC-3 (original) ambiguous — psycopg2 location | **Non-blocking** | "requirements.txt includes psycopg2-binary" didn't specify whether it was in INSTALLED_APPS, DATABASES ENGINE, or requirements.txt |
| AC-4 (original) missing negative test | **Non-blocking** | Only tested PostgreSQL path — no test for SQLite default (which should exclude all database packages) |
| No AC for `questions()` | **Non-blocking** | Keys, types, options, and uniqueness of question keys were not tested |
| No AC for `dependencies()` or `directories()` | **Non-blocking** | Two of the 4 mixin methods had zero AC coverage |
| No error-case ACs | **Non-blocking** | Empty config, missing config key, invalid database value — no negative test coverage |
| `include_celery` in API spec with zero ACs | **Non-blocking** | Had a config key with no corresponding AC, risking untestable dead code |
| No `__init__.py` AC-4 scanner compliance note | **Non-blocking** | Design notes didn't document the mandatory `from forge.domain import ...` pattern required by the AC-4 AST scanner |
| No `_config()` helper pattern mention | **Non-blocking** | T-008 established a static `_config(spec)` helper pattern for safe config access — not referenced in T-009 |
| Missing database=sqlite and database=mysql ACs | **Non-blocking** | Only PostgreSQL was tested as a database variant; SQLite (default) and MySQL had no coverage |

---

### TDD Review Round 2 — APPROVED (0 blocking, 0 moderate, 12 remaining green findings)

After fixing all Round 1 issues, the re-review found no blocking or moderate issues. Twelve non-blocking (green) findings remained, all documented as actionable improvements for the implementation:

| Issue | Severity | Area | Fix |
|-------|----------|------|-----|
| AC-02a "contains" loose | **Green** | Precision | Test should use exact set membership for core file paths |
| AC-02b combines assertions | **Green** | Test design | Consider splitting into 2b_i (stage_file) and 2b_ii (requirements) |
| AC-03 "options containing" loose | **Green** | Precision | Should assert exact equality: `["postgresql", "sqlite", "mysql"]` |
| AC-04/06/07 version strings | **Green** | Consistency | files() ACs should reference version strings matching dependencies() |
| AC-05/10/15 ambiguous packages | **Green** | Precision | "any database-specific package" → explicit `psycopg2-binary`/`mysqlclient` |
| AC-08 missing requirements.txt check | **Green** | Scope | Should assert no djangorestframework in requirements.txt |
| AC-11/12 base deps preservation | **Green** | Completeness | Should assert django>=5.1 still present when adding conditional deps |
| AC-13 "containing" ambiguity | **Green** | Precision | Clarify exact vs subsequence match for command list |
| Question defaults undocumented | **Green** | Documentation | API spec should show default="sqlite", default=False |
| AC-16 defaults underspecified | **Green** | Precision | Should say "database defaults to sqlite, include_drf defaults to False" |
| generate() missing database=postgresql/mysql | **Green** | Coverage gap | No AC tests conditional database deps in generate() — same bug class as T-008 critical finding |
| AC-18 not tagged [unit] | **Green** | Consistency | Minor formatting inconsistency with AC-01/AC-19 |

All 12 green findings were incorporated into the final ticket spec. The **generate() database-conditional deps gap** (critical lesson from T-008) was specifically addressed by adding AC-15 (generate with postgresql) and AC-16 (generate with mysql), expanding from 19 to 21 ACs.

#### Verdict Rationale (Round 2)

> All 12 prior issues (2 blocking + 10 non-blocking) are VERIFIED RESOLVED. The ticket now thoroughly covers all 4 capability mixins, includes error cases (empty config, missing key, invalid value), and incorporates all critical lessons from T-008 (AC-4 scanner compliance, `_config` helper, cross-method consistency, ValidationEngine ownership, test-first construction). One coverage gap remained (generate() with database=postgresql/mysql — same class as T-008 critical code review finding) but Design Note 9 explicitly warns about cross-method consistency. The gap was addressed before implementation by adding AC-15/AC-16. All 21 ACs are individually testable as unit tests with existing test infrastructure. **APPROVED.**

---

### Code Review Round 1 — 0 Issues Found (C.L.E.A.R. Framework)

The C.L.E.A.R. review after implementation found **zero issues** across all dimensions:

| Dimension | Result |
|-----------|--------|
| **C — Context** | ALIGNED — All 21 ACs covered, all 10 design notes respected, no feature creep |
| **L — Logic** | CORRECT — Happy path, all 3 database variants, DRF conditional, missing key, empty config — all correct |
| **E — Efficiency** | OPTIMAL — No redundant computation, O(1) per method, pattern matches FastAPI exactly |
| **A — Architecture** | COMPLIANT — Zero forbidden imports, AC-4 scanner passes, layer separation preserved |
| **R — Reliability** | ROBUST — All error cases handled via `.get()` defaults, validation delegated to ValidationEngine |

No regressions were introduced. All quality gates passed: 239 tests (0 failures), mypy (0 issues), ruff lint/format (clean), AC-4 scanner (clean).

---

## 3. Fixes Applied

### A. Split AC-2 into AC-2a (files) and AC-2b (engine integration) (v1 B1)

**Before:** AC-2 described "creates core files" but conflated `files()` (FileProvider) with `generate()` (CommandRunner) — impossible to implement under the existing mixin contract.

**After (FIXED):**
- **AC-2a**: `files()` returns `GeneratedFile` entries for 5 core paths — tests FileProvider
- **AC-2b**: `PluginExecutionEngine` (simulated) stages files via `txn.stage_file()` and appends deps to `txn.requirements` — tests the generation pipeline integration
- `generate()` moved to separate ACs (AC-13/14/15/16)

### B. Fixed `dependencies()` Signature (v1 B2)

**Before:** `def dependencies(self)` — no `spec` parameter, would crash at runtime when `PluginExecutionEngine` calls `plugin.dependencies(spec)`.

**After (FIXED):** `def dependencies(self, spec: ProjectSpec) -> list[str]` — matches `base.py:49-51` exactly. Callers in `plugin_execution_engine.py:57` already pass `spec`. All mock fixtures updated during T-008.

### C. Fixed `generate()` Signature — Untyped `executor` (v1 NB3)

**Before:** `def generate(self, spec, target_dir)` — missing executor parameter.

**After (FIXED):** `def generate(self, spec, target_dir, executor)` — executor param present with untyped annotation (`Any`). This satisfies AC-4 scanner compliance (Design Note 7): concrete plugins must NOT import `ProcessExecutor` from `forge.infrastructure`.

### D. Clarified Database Dependency Assertions (v1 NB4/NB5/NB12)

**Before:** Ambiguous — "psycopg2-binary" without specifying whether it's in INSTALLED_APPS, DATABASES ENGINE, or requirements.txt. Missing negative test for SQLite default.

**After (FIXED):** Each database variant has 2-part assertions:
- (a) **settings.py**: `"ENGINE": "django.db.backends.<backend>"` in DATABASES setting
- (b) **requirements.txt**: specific package inclusion/exclusion (e.g., `psycopg2-binary>=2.9` present for PostgreSQL, absent for SQLite)

### E. Added Questions AC-3 (v1 NB6)

**Before:** No AC tested that `questions()` returns proper Question objects.

**After (FIXED):** AC-3 covers:
- Key presence: `"database"` and `"include_drf"` in returned keys
- Types: `database` is `QuestionType.CHOICE`, `include_drf` is `QuestionType.BOOLEAN`
- Options: `database.options == ["postgresql", "sqlite", "mysql"]`
- Uniqueness: `len(keys) == len(set(keys))`

### F. Added Dependencies/Directories ACs (v1 NB7)

**Before:** No ACs for `dependencies()` or `directories()`.

**After (FIXED):**
- AC-9: `directories()` contains `config/`, `apps/`, `static/`, `templates/`
- AC-10: `dependencies()` base set — `['django>=5.1']`, no database/DRF packages
- AC-11: `dependencies()` with DRF — includes `djangorestframework>=3.15` AND still `django>=5.1`
- AC-12: `dependencies()` with PostgreSQL — includes `psycopg2-binary>=2.9` AND still `django>=5.1`

### G. Added Error-Case ACs (v1 NB8)

**Before:** No tests for empty config, missing config key, or invalid values.

**After (FIXED):**
- AC-15/AC-17: empty `{"django": {}}` → SQLite defaults, no extra deps (cross-method: files + dependencies)
- AC-16/AC-18: missing `"django"` key → no exception, defaults used
- AC-17/AC-19: invalid database value → `ValidationEngine.validate_plugin_config()` returns error

### H. Removed `include_celery` from Scope (v1 NB9)

**Before:** API spec had `include_celery` in questions but zero AC coverage — untestable dead code risk.

**After (FIXED):** Design Note 10 explicitly removes `include_celery` from scope: "Removed from API spec." No mention remains.

### I. Added AC-4 Scanner Compliance Note (v1 NB10)

**Before:** No documentation of the mandatory domain import for AC-4 scanner.

**After (FIXED):** Design Note 4: "Every .py file under plugins/ must import from forge.domain. django/__init__.py must include this import even if only re-exporting." Follows T-008 pattern.

### J. Added _config() Helper Pattern (v1 NB11)

**Before:** No reference to T-008's established `_config(spec)` static helper pattern for safe config access.

**After (FIXED):** Design Note 1: "Follow the `_config(spec)` helper pattern established in FastAPiPlugin (`_config` static method returning `spec.config.get("django", {})`)."

### K. Added `generate()` Database-Conditional ACs (v2 Green — Coverage Gap)

**Before (Round 2 gap):** No AC tested that `generate()` installs `psycopg2-binary>=2.9` for PostgreSQL or `mysqlclient>=2.2` for MySQL. This was **exactly the same class of bug** found as a CRITICAL issue during T-008 code review (the `generate()` method only installed framework deps, ignoring conditional database deps — causing generated projects to crash at runtime).

**After (FIXED):** Three new ACs added:
- AC-14: generate with DRF → includes `djangorestframework>=3.15`
- AC-15: generate with PostgreSQL → includes `psycopg2-binary>=2.9`
- AC-16: generate with MySQL → includes `mysqlclient>=2.2`

Cross-method consistency verified: `files()`, `dependencies()`, and `generate()` all use identical conditional logic for database choice and DRF flag.

### L. Tightened All Ambiguous Assertions (v2 Green Precision Fixes)

| AC | Before | After |
|----|--------|-------|
| AC-02a | "contains" | Exact path set membership with `isinstance(f.path, Path)` |
| AC-03 | "options containing" | `database_q.options == ["postgresql", "sqlite", "mysql"]` |
| AC-04 | "includes psycopg2-binary" | `"psycopg2-binary>=2.9" in reqs.content` |
| AC-05 | "any database-specific package" | `"psycopg2-binary" not in reqs.content and "mysqlclient" not in reqs.content` |
| AC-06 | "includes mysqlclient" | `"mysqlclient>=2.2" in reqs.content` |
| AC-07 | "includes djangorestframework" | `"djangorestframework>=3.15" in reqs.content` |
| AC-08 | Missing requirements.txt check | Added: `"djangorestframework" not in reqs.content` |
| AC-10 | "any database-specific package" | Explicit: `"psycopg2" not in d and "mysqlclient" not in d` |
| AC-11/12 | Missing base deps preservation | Added: `"django>=5.1" in deps` |
| AC-13 | "containing" ambiguous | Subsequence check: `"uv" in cmd`, `"add" in cmd`, `"django>=5.1" in cmd` |
| AC-15/17 | "contains sqlite3" | `"sqlite3" in settings.content` |

---

## 4. Technical Issues Found During Implementation

### Dependency Analysis Discoveries (Pre-Implementation)

A detailed cross-reference of the ticket against existing code — performed during the dependency analysis phase — revealed several integration points:

1. **AC-4 scanner scope** — The scanner (`test_plugin_base.py:TestAC4`) walks `plugins/rglob("*.py")` with `INFRA_EXEMPT_FILES = {"base.py"}`. Confirmed that `django/plugin.py` and `django/__init__.py` would be scanned. The `executor: Any` pattern (Design Note 7) and domain import (Design Note 4) correctly satisfy the scanner.

2. **`_config(spec)` pattern inheritance** — T-008's `_config()` static helper (`spec.config.get("fastapi", {})`) was documented in Design Note 1. Verified that `spec.config.get("django", {})` works identically and does NOT need `spec.plugin_config("django")` which raises `KeyError`.

3. **Cross-method consistency mapping** — The ticket requires 3 methods (`files()`, `dependencies()`, `generate()`) to produce consistent output for each of 6 config permutations (3 databases × 2 DRF states). This creates 18 conditional assertions across the test suite. Design Note 9 explicitly warns about this.

4. **ValidationEngine integration** — `ValidationEngine.validate_plugin_config()` (validation.py:148-157) validates CHOICE values. The Django plugin's `database` question is a CHOICE with `options=["postgresql", "sqlite", "mysql"]`. The inline Question construction pattern (Design Note 8) is used in AC-19 tests to avoid coupling between validation tests and plugin bootstrap.

5. **Entry point registration** — `pyproject.toml:16` already registers `django = "forge.plugins.django:DjangoPlugin"`. AC-01 asserts `name == "django"` matching this entry point.

### Source of Discovery (Pre-Implementation)

| Finding | Discovery Method | Relevant File |
|---------|-----------------|---------------|
| AC-4 scanner uses `rglob()` with `INFRA_EXEMPT_FILES` | Reading `test_plugin_base.py:176-183` | `tests/unit/test_plugin_base.py` |
| `dependencies()` requires `spec` param | Reading `base.py:49-51` | `src/forge/plugins/base.py` |
| `CommandRunner.generate()` signature with untyped executor constraint | Reading `base.py:44-46` + `test_plugin_base.py:187-196` | `src/forge/plugins/base.py` |
| `_config()` pattern from T-008 | Reading `fastapi/plugin.py:190-192` | `src/forge/plugins/fastapi/plugin.py` |
| No changes needed to generation/ or infrastructure/ layers | Cross-referencing all ACs against existing code | — |
| Entry point already in `pyproject.toml:16` | Reading pyproject.toml | `pyproject.toml` |

### Implementation Discoveries

No new structural issues were discovered during implementation. All design decisions were validated during the TDD review phase. The implementation was straightforward:

| Item | Finding | Resolution |
|------|---------|------------|
| `manage.py` content | Standard Django manage.py — no design decisions needed | Copied from Django documentation |
| `config/settings.py` DATABASES dict format | Conditional ENGINE based on database choice, plus conditional `rest_framework` in INSTALLED_APPS | Implemented via `_build_settings(database, include_drf)` function |
| `executor.run()` command construction | Same pattern as T-008: build deps list, call `executor.run(deps, cwd=target_dir)` | Simple conditional list building |
| No Jinja2 templates needed | Template files are small enough for inline strings | Skipped `templates/` directory |

### Code Review Discoveries (Post-Implementation)

The C.L.E.A.R. code review found zero issues. This is the first ticket in the series to pass code review without any findings.

---

## 5. Final Implementation

### Files Created

```
src/forge/plugins/django/__init__.py     # Package init: re-export DjangoPlugin; AC-4 scanner compliance
src/forge/plugins/django/plugin.py       # DjangoPlugin: 4 mixins, 5 methods, 6 file templates
```

### Files Modified

- `src/forge/plugins/django/.gitkeep` — **Deleted** (placeholder removed after real files created)

### Files Not Modified (verified)

- `src/forge/plugins/base.py` — mixin interfaces unchanged
- `src/forge/plugins/__init__.py` — re-exports base mixins, unchanged
- `src/forge/plugins/fastapi/` — no changes needed
- `src/forge/generation/` — no changes to registry, validation, stages, orchestrator
- `src/forge/infrastructure/` — no changes
- `src/forge/domain/` — domain models unchanged
- `pyproject.toml` — entry point already registered (line 16)
- `tests/` — test files already exist (test-first), no modifications needed

### Architecture

```python
# ── DjangoPlugin (PluginBase + 4 mixins) ──────────────────────────────
class DjangoPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "django"
    display_name = "Django"
    description = "Django backend with choice of database + DRF"
    requires: list[str] = []

    @staticmethod
    def _config(spec: ProjectSpec) -> dict[str, Any]:
        return spec.config.get("django", {})

    def questions(self) -> list[Question]:
        # 2 questions: database (CHOICE: postgresql/sqlite/mysql), include_drf (BOOLEAN)

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # 6 files: manage.py, config/__init__.py, config/settings.py, config/urls.py,
        #          config/wsgi.py, requirements.txt
        # Conditional: database → ENGINE in settings.py + packages in requirements.txt
        # Conditional: include_drf → rest_framework in INSTALLED_APPS + djangorestframework

    def directories(self, spec: ProjectSpec) -> list[str]:
        # 4 directories: config/, apps/, static/, templates/

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        # django>=5.1 + conditional: psycopg2-binary>=2.9, mysqlclient>=2.2, djangorestframework>=3.15

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: Any) -> None:
        # executor.run(["uv", "add", "django>=5.1", ...], cwd=target_dir)
        # Conditional deps mirror dependencies() exactly
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `_config(spec)` static helper | Matches T-008 FastAPI pattern; safe `.get()` access avoids `KeyError` on missing config |
| `executor: Any` (untyped) | Required by AC-4 scanner — concrete plugins must NOT import `ProcessExecutor` from `forge.infrastructure` |
| `_build_settings(database, include_drf)` function | settings.py content is too large for inline string — function encapsulates conditional logic cleanly |
| Module-level template constants (5) | Matches T-008 pattern; keeps file templates out of method body for readability |
| No Jinja2 templates | All file templates are small static strings — Jinja2 would add a dependency without benefit |
| Local `_MockTransaction` in test (not shared) | Preserves layer isolation — test file imports only from `forge.domain`, no cross-layer imports |
| `engine_map` dict for ENGINE values | Cleaner than if/elif chain for 3 database variants; `.get()` fallback handles unexpected values |

---

## 6. Test Coverage

| Category | Tests | Covers ACs | Status |
|----------|-------|------------|--------|
| Name & properties | 2 | AC-01, AC-20 | ✅ |
| files() core paths (type + membership) | 3 | AC-02a | ✅ |
| Engine integration (simulated) | 2 | AC-02b | ✅ |
| questions() keys, types, options, uniqueness | 4 | AC-03 | ✅ |
| database=postgresql (settings + requirements) | 2 | AC-04 | ✅ |
| database=sqlite (settings + requirements) | 2 | AC-05 | ✅ |
| database=mysql (settings + requirements) | 2 | AC-06 | ✅ |
| include_drf=True (settings + requirements) | 2 | AC-07 | ✅ |
| include_drf=False or absent (settings + requirements) | 3 | AC-08 | ✅ |
| directories() content | 1 | AC-09 | ✅ |
| dependencies() base set | 2 | AC-10 | ✅ |
| dependencies() with DRF | 1 | AC-11 | ✅ |
| dependencies() with PostgreSQL | 1 | AC-12 | ✅ |
| generate() default (command + cwd) | 2 | AC-13 | ✅ |
| generate() with DRF | 1 | AC-14 | ✅ |
| generate() with PostgreSQL | 1 | AC-15 | ✅ |
| generate() with MySQL | 1 | AC-16 | ✅ |
| Empty config defaults | 1 | AC-17 | ✅ |
| Missing key defaults (no exception) | 2 | AC-18 | ✅ |
| Module export | 1 | AC-21 | ✅ |
| **Total** | **37** | **21 ACs** | ✅ |

### Test Classes (14)

| Class | Tests | Focus |
|-------|-------|-------|
| `TestAC1_Name` | 1 | AC-01: name == "django" |
| `TestAC2a_FilesCorePaths` | 3 | AC-02a: file paths, types, Path objects |
| `TestAC2b_EngineIntegration` | 2 | AC-02b: staging + deps |
| `TestAC3_Questions` | 4 | AC-03: keys, types, options, uniqueness |
| `TestAC4_DatabasePostgresql` | 2 | AC-04: postgresql ENGINE + package |
| `TestAC5_DatabaseSqlite` | 2 | AC-05: sqlite3 ENGINE + no packages |
| `TestAC6_DatabaseMysql` | 2 | AC-06: mysql ENGINE + package |
| `TestAC7_DrfTrue` | 2 | AC-07: DRF in settings + package |
| `TestAC8_DrfFalseOrAbsent` | 3 | AC-08: no DRF in settings + package |
| `TestAC9_Directories` | 1 | AC-09: directory list |
| `TestAC10_BaseDependencies` | 2 | AC-10: base deps |
| `TestAC11_DepsDrfTrue` | 1 | AC-11: DRF deps |
| `TestAC12_DepsPostgresql` | 1 | AC-12: PostgreSQL deps |
| `TestAC13_GenerateDefault` | 2 | AC-13: command + cwd |
| `TestAC14_GenerateDrf` | 1 | AC-14: generate with DRF |
| `TestAC15_GeneratePostgresql` | 1 | AC-15: generate with PostgreSQL |
| `TestAC16_GenerateMysql` | 1 | AC-16: generate with MySQL |
| `TestAC17_EmptyConfigDefaults` | 1 | AC-17: empty config defaults |
| `TestAC18_MissingConfigKey` | 2 | AC-18: missing key handling |
| `TestAC20_DisplayNameAndDescription` | 2 | AC-20: display name + description |
| `TestAC21_ModuleExport` | 1 | AC-21: module importability |

### Validation Test (Pre-existing, Unchanged)

| Class | Tests | Focus |
|-------|-------|-------|
| `TestAC19_DjangoDatabaseValidation` | 2 | AC-19: inline Question construction; invalid value rejected, valid value accepted |

---

## 7. Outstanding Issues

### Non-Blocking

- [ ] LOW: `_build_settings()` fallback for invalid database values produces sqlite3 ENGINE with non-SQLite credentials (e.g., MySQL port + user). This is explicitly by design (Design Note 2: ValidationEngine owns input validation; plugin trusts validated input). If this becomes a support surface, consider adding an assertion guard at the `_build_settings` entry point.
- [ ] LOW: No Jinja2 template files created — all templates are inline Python strings. If future Django plugin features require complex templates, the templates/ directory should be created and `jinja2` added to `pyproject.toml` dependencies.
- [ ] LOW: No integration tests that verify the full generation pipeline with `DjangoPlugin` — the 37 unit tests cover all mixin methods in isolation and via simulated engine, but not the actual `app.py → PluginRegistry → PluginExecutionEngine` flow with a DjangoPlugin instance.

### Resolved During Review

- [x] AC-2 conflated `generate()` with `files()` → split into AC-2a (files) and AC-2b (engine integration)
- [x] `dependencies()` signature missing `spec` param → fixed to match `base.py:49-51`
- [x] `generate()` missing `executor` param → added untyped `executor` per AC-4 compliance
- [x] Ambiguous database package assertions → explicit ENGINE + package name + version
- [x] SQLite/MySQL database coverage missing → added AC-5 and AC-6
- [x] `questions()` not tested → added AC-3 with type/options/uniqueness checks
- [x] `dependencies()` and `directories()` not tested → added AC-9/10/11/12
- [x] No error-case ACs → added AC-15/16/17/18 (empty config, missing key, invalid value)
- [x] `include_celery` in spec with no ACs → removed from scope (Design Note 10)
- [x] No AC-4 scanner compliance note → added Design Note 4
- [x] No `_config()` helper pattern mention → added Design Note 1
- [x] Missing `generate()` database-conditional ACs → added AC-15/AC-16 (T-008 critical lesson)
- [x] Ambiguous "contains/options containing/any package" → all tightened to exact equality
- [x] AC-08 missing requirements.txt check → added negative assertion for djangorestframework
- [x] AC-11/12 missing base deps preservation → added `"django>=5.1" in deps` assertions

---

## 8. Lessons Learned

### What Went Well

1. **TDD review found all structural issues pre-implementation** — Unlike prior tickets where code review caught spec-vs-implementation mismatches after coding, T-009's 2 TDD review rounds surfaced all 2 blocking and 10 non-blocking issues before any code was written. The implementation phase was purely execution with zero spec surprises.

2. **T-008 lessons directly applied** — The `_config()` helper pattern, AC-4 scanner compliance, cross-method consistency requirement, and generate/deps alignment were all established by T-008 and explicitly referenced in T-009's design notes. This reduced the TDD review scope from "discover the pattern" to "verify the pattern is applied correctly."

3. **Coverage gap in generate() caught before it became a bug** — The Round 2 review identified that `generate()` had no database-conditional ACs (PostgreSQL/MySQL) — exactly the same class of bug found as a CRITICAL issue during T-008 code review. Adding AC-15/AC-16 before implementation prevented the bug from ever reaching code.

4. **Zero code review findings** — T-009 is the first ticket in the series to pass C.L.E.A.R. review with zero issues. This validates that the TDD pre-implementation process has matured: thorough spec review eliminates structural issues before they become code problems.

5. **Plugin implementation cost is now predictable** — Following the T-008 pattern, the Django plugin took approximately the same effort (~30% of window per the estimate). The pattern is repeatable: implement `__init__.py` (AC-4 scaffold) + `plugin.py` (5 methods + templates + `_config()` helper), write file content as module-level constants, run 37 tests.

6. **239 tests pass with zero regressions** — The implementation added 2 new source files without modifying any existing files (beyond removing the `.gitkeep`). This confirms the plugin isolation architecture is working: plugins are self-contained with no cross-file coupling.

### What Could Improve

1. **Pre-populate Question.default values in API spec** — The API spec's `questions()` pseudocode shows `database: str (choice: postgresql, sqlite, mysql, default: sqlite)` and `include_drf: bool (default: False)` but the pseudocode doesn't show `Question(default="sqlite")` / `Question(default=False)` in the constructor calls. This was noted as a green finding in Round 2. Future plugin tickets should include explicit `default=` values in the `Question(...)` pseudocode.

2. **State version strings consistently across ACs** — Several ACs used unversioned package names (e.g., "includes psycopg2-binary") while the API spec `dependencies()` showed versioned strings (e.g., "psycopg2-binary>=2.9"). Future tickets should either always use versioned strings in files() ACs or clearly state the substring-matching strategy.

3. **Add `# noqa: F401` to AC-4 comment in a consistent position** — The AC-4 domain import pattern uses `from forge.domain import ProjectSpec as _  # noqa: F401 — comment`. The `# noqa: F401` position and comment style should be standardized across all plugin `__init__.py` files for consistency.

4. **Consider extracting a shared `_build_requirements(deps)` helper** — The requirement-to-string conversion (`"\n".join(reqs) + "\n"`) is repeated in both FastAPI and Django plugins. A shared utility could reduce duplication, but the benefit is marginal given the one-line pattern.

### Key Metrics

| Metric | Value |
|--------|-------|
| Original ACs | 19 |
| Refined ACs | 21 |
| TDD review rounds | 2 |
| Code review rounds | 1 |
| Implementation issues found by dependency analysis | 5 (all pre-implementation) |
| Source files created | 2 |
| Files modified | 0 (1 `.gitkeep` deleted) |
| Django unit tests | 37 |
| Pre-existing validation tests (unchanged) | 2 |
| Total test suite | 239 (all pass, 0 regressions) |
| TDD issues found | 2 blocking + 10 non-blocking (R1) → 0 (R2 APPROVED) |
| Code review issues | 0 |
| Mock complexity | None (MagicMock for executor, local _MockTransaction) |
| New dependencies | 0 |

---

## 9. Acceptance Criteria Verification

| AC | Test(s) | Verification Method | Status |
|----|---------|---------------------|--------|
| AC-01 | `test_name_returns_django` | Direct: `plugin.name == "django"` | ✅ |
| AC-02a | `test_files_contains_core_files`, `test_files_returns_list_of_generated_files`, `test_file_paths_are_path_objects` | Structural: 5 core paths present as `Path` objects in `GeneratedFile` list | ✅ |
| AC-02b | `test_engine_stages_core_files_and_deps`, `test_engine_empty_config_no_error` | Structural: files staged via `txn.stage_file()`, deps appended to `txn.requirements` | ✅ |
| AC-03 | `test_questions_keys_include_database_and_drf`, `test_database_question_type_and_options`, `test_include_drf_is_boolean`, `test_question_keys_are_unique` | Structural: key presence, type checks, option equality, uniqueness | ✅ |
| AC-04 | `test_settings_engine_is_postgresql`, `test_requirements_includes_psycopg2` | Structural: ENGINE string in settings.py content, package in requirements.txt | ✅ |
| AC-05 | `test_settings_engine_is_sqlite3`, `test_requirements_excludes_db_packages` | Structural: sqlite3 ENGINE, no database packages | ✅ |
| AC-06 | `test_settings_engine_is_mysql`, `test_requirements_includes_mysqlclient` | Structural: mysql ENGINE, mysqlclient in requirements | ✅ |
| AC-07 | `test_settings_includes_rest_framework`, `test_requirements_includes_drf` | Structural: rest_framework in INSTALLED_APPS, djangorestframework in requirements | ✅ |
| AC-08 | `test_settings_excludes_rest_framework` (×2 configs), `test_requirements_excludes_drf` | Structural: no rest_framework in settings, no djangorestframework in requirements | ✅ |
| AC-09 | `test_directories_contains_expected_dirs` | Structural: 4 directory strings present | ✅ |
| AC-10 | `test_base_deps_includes_django`, `test_base_deps_excludes_drf_and_db_packages` | Structural: django>=5.1 present, DRF/db packages absent | ✅ |
| AC-11 | `test_deps_include_drf_when_enabled` | Structural: djangorestframework>=3.15 AND django>=5.1 present | ✅ |
| AC-12 | `test_deps_include_psycopg2` | Structural: psycopg2-binary>=2.9 AND django>=5.1 present | ✅ |
| AC-13 | `test_generate_calls_executor_run_with_uv_add`, `test_generate_passes_cwd_to_executor` | Structural: executor.run() called with ["uv", "add", "django>=5.1"] + cwd=target_dir | ✅ |
| AC-14 | `test_generate_includes_drf` | Structural: executor.run() command includes djangorestframework>=3.15 | ✅ |
| AC-15 | `test_generate_includes_psycopg2` | Structural: executor.run() command includes psycopg2-binary>=2.9 | ✅ |
| AC-16 | `test_generate_includes_mysqlclient` | Structural: executor.run() command includes mysqlclient>=2.2 | ✅ |
| AC-17 | `test_empty_config_uses_defaults` | Structural: SQLite defaults, no extra deps, cross-method consistency | ✅ |
| AC-18 | `test_missing_django_key_uses_defaults`, `test_missing_django_key_does_not_raise` | Structural: no exception on files/directories/dependencies with empty config | ✅ |
| AC-19 | `test_database_invalid_value`, `test_database_valid_value` | Structural: ValidationEngine returns error for invalid value, no error for valid | ✅ |
| AC-20 | `test_display_name`, `test_description_is_non_empty` | Direct: display_name == "Django", description is non-empty string | ✅ |
| AC-21 | `test_module_export` | Import: `from forge.plugins.django import DjangoPlugin` succeeds | ✅ |

---

## 10. Timeline

| Date | Activity |
|------|----------|
| Jun 21, 2026 | Ticket loaded (19 ACs, 10 design notes, API spec with 4 mixins) |
| Jun 21, 2026 | Dependency analysis: 5 pre-implementation findings verified |
| Jun 21, 2026 | TDD review round 1 (CHANGES REQUESTED — 2 blocking + 10 non-blocking issues) |
| Jun 21, 2026 | Fixed v1: split AC-2, fixed signatures, added ACs for questions/deps/dirs/errors, added design notes |
| Jun 21, 2026 | TDD review round 2 (APPROVED — 0 blocking, 12 green findings) |
| Jun 21, 2026 | Fixed v2: tightened assertions, added generate() database ACs, fixed version strings, added base-dep preservation |
| Jun 21, 2026 | **Implementation**: `src/forge/plugins/django/__init__.py`, `src/forge/plugins/django/plugin.py` (173 lines, 5 methods, 6 file templates) |
| Jun 21, 2026 | **Verification**: ruff lint ✅, ruff format ✅, 37/37 Django tests ✅, AC-4 scanner ✅, AC-19 validation ✅ |
| Jun 21, 2026 | **Full suite**: 239/239 tests ✅, mypy clean ✅ |
| Jun 21, 2026 | **C.L.E.A.R. code review**: 0 issues — APPROVE |
| Jun 21, 2026 | Post-mortem updated |

---

## 11. Next Steps

1. Mark T-009 as ✅ COMPLETE in tickets index document
2. T-010 (React Plugin) will follow the same pattern — estimated at ~30% of window (already established by T-008/T-009)
3. For T-010/T-011, pre-populate all `Question.default` values in API spec pseudocode to avoid Round 2 green findings
4. Standardize AC-4 domain import comment format across all plugin `__init__.py` files: `from forge.domain import ProjectSpec as _  # noqa: F401`
5. Consider adding a shared `_build_requirements(deps: list[str]) -> str` helper in `plugins/base.py` to deduplicate the `"\n".join(reqs) + "\n"` pattern across plugins
6. Codify the "cross-method consistency matrix" step in the TDD review checklist: for each config key, verify that `files()`, `dependencies()`, and `generate()` all produce consistent output for all permutations
