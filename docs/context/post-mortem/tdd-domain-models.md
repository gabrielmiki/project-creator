# Post-Mortem: T-001 Domain Models

**Date:** June 6, 2026
**Status:** ✅ COMPLETE
**Review Status:** APPROVED

---

## 1. Overview

### Original Ticket

**Title:** Domain Models — Create all pure domain models in `src/forge/domain/` as `@dataclass` classes

**Original Acceptance Criteria (9 ACs, well-specified):**

```
AC-01: Domain package imports successfully with zero import errors
AC-02: plugin_config("fastapi") returns {"orm": "sqlalchemy"} for existing key
AC-03: plugin_config("django") raises KeyError for missing key
AC-04: Domain slug auto-derived with 5 edge cases (whitespace, multi-space, override, empty)
AC-05: Question round-trips through dataclasses.asdict()
AC-06: TemplateDefinition constructs with frontend_id=None default
AC-07: No forbidden imports from other Forge layers (ast-based static analysis)
AC-08: GeneratedFile constructs correctly with all fields
AC-09: DurationEstimate constructs correctly with all fields
```

**Files specified:**
- `src/forge/domain/__init__.py`
- `src/forge/domain/project_spec.py`
- `src/forge/domain/questions.py`
- `src/forge/domain/generated_file.py`

### What Actually Happened

The ticket was implemented in a single session without following the pipeline's prescribed TDD workflow. No test files were created alongside the production code. After implementation, a post-hoc analysis identified that the pipeline lacked a **Test-First Gate** step, which was subsequently added. Unit tests were then retrofitted and verified against the existing code.

---

## 2. Problems Identified

### Problem 1: Test file gap — no ticket lists test files for production code

**Severity: Medium**

**Description:** Every production-code ticket (001–015) lists only source files in "Files to create." No ticket in the range 001–015 references `tests/` paths. Test files are deferred to T-016, T-017, T-018 at the end of Phase 1. This means domain models — the foundation of the entire application — would have no test file for 15 tickets.

**Root cause:** The ticket structure intentionally separates production code from test code, but the pipeline's own quality gate says "Domain models: unit tests only." No mechanism ensures those unit tests are written at the same time as the code.

**Resolution:** Added a **Test-First Gate** step (Step 2) to the pipeline workflow: write unit tests before implementation, confirm they fail, then implement until they pass. The gate also mandates `pytest.raises` for error cases and `ast`-based static analysis for import purity.

---

### Problem 2: TDD Reviewer agent was skipped

**Severity: Medium**

**Description:** The pipeline.md (before fix) specified "Run the TDD Reviewer agent on acceptance criteria" in Step 1 (Design). This was not done — the prompt went straight to implementation.

**Root cause:** No enforced gate between design and implementation. The pipeline described the step but provided no mechanism to prevent skipping it.

**Resolution:** The pipeline now explicitly places the TDD Reviewer in Step 2 (Test-First Gate) and separates it from Step 1 (Design) where the Architecture Reviewer lives. The TDD Reviewer validates AC testability before any test or code is written.

---

### Problem 3: Question round-trip with nested ValidationRule requires custom serializer

**Severity: Low**

**Description:** `dataclasses.asdict()` converts nested `ValidationRule` dataclasses to plain dicts (`{"min": 1024, "max": 65535, "pattern": None}`). Reconstructing a `Question` with `Question(**asdict(q))` produces a `Question` whose `validation` field is a `dict`, not a `ValidationRule`. Equality comparison fails.

The ticket's implementation notes acknowledge this: "A full round-trip with a non-None ValidationRule would need a custom serialization helper (beyond dataclasses.asdict())." The initial test didn't account for this and failed.

**Root cause:** `dataclasses.asdict()` performs one-level dict conversion on nested dataclasses. The round-trip AC-5 only covers the `validation=None` case explicitly. The non-None case requires a manual reconstruction step.

**Resolution:** Test was adjusted to document the limitation: `asdict()` produces `{"min": 1024, "max": 65535, "pattern": None}` for `ValidationRule`, and reconstruction requires `ValidationRule(**d["validation"])`.

---

### Problem 4: mypy + src-layout conflict with editable install

**Severity: Low**

**Description:** Running `mypy src/` failed because the editable install (`uv sync`) creates a `forge` package in site-packages that points back to `src/forge/`. Mypy saw the same source files under two module names (`domain.generated_file` and `forge.domain.generated_file`), producing a "Source file found twice" error.

**Root cause:** The src-layout pattern (`src/forge/` as package root) combined with editable installs creates a dual-resolution path. This is a known issue documented in mypy's troubleshooting guide.

**Resolution:** Added `explicit_package_bases = true` to `pyproject.toml` and changed the mypy command from `mypy src/` to `mypy -p forge`. Updated both `pyproject.toml` and `AGENTS.md`.

---

### Problem 5: Missing dev dependencies and py.typed marker

**Severity: Low**

**Description:** `ruff`, `mypy`, `pytest`, and `pytest-cov` were not installed as dev dependencies — they were referenced in `AGENTS.md` commands but not in `pyproject.toml`. Additionally, the `py.typed` marker file was missing, causing mypy to skip type-checking the installed `forge` package.

**Root cause:** The project scaffold didn't include dev dependencies because no code had been written yet. The `py.typed` marker is required by PEP 561 for packages to expose type information.

**Resolution:** Added dev dependencies via `uv add --dev ruff mypy pytest pytest-cov` and created `src/forge/py.typed`.

---

### Problem 6: `from __future__ import annotations` was duplicated

**Severity: Trivial**

**Description:** During test file edits, a duplicate `from __future__ import annotations` was introduced. Ruff flagged this as an unused import (the second occurrence).

**Root cause:** Manual editing without checking the full file state.

**Resolution:** Removed the duplicate.

---

## 3. Fixes Applied

### A. Added Test-First Gate to Pipeline (Problem 1)

**Before:**
```
1. Design → 2. Implement → 3. Review → 4. Test → 5. Commit
```

**After:**
```
1. Design → 2. Test-First Gate → 3. Implement → 4. Review → 5. Test → 6. Commit
```

The new Step 2 includes:
- Run TDD Reviewer on acceptance criteria
- Write unit tests in `tests/unit/` covering all ACs (happy path, error cases, edge cases)
- Tests must not import from other Forge layers beyond the ticket's domain
- Cross-layer dependencies use mocks or stubs
- Confirm tests fail before any production code is written

### B. Fixed Question Round-Trip Test (Problem 3)

**Before (failing):**
```python
def test_round_trip_with_validation_rule(self) -> None:
    q = Question(...)
    d = dataclasses.asdict(q)
    restored = Question(**d)
    assert restored == q  # Fails: validation is dict, not ValidationRule
```

**After (passing):**
```python
def test_round_trip_with_validation_rule_needs_custom_serializer(self) -> None:
    q = Question(...)
    d = dataclasses.asdict(q)
    assert d["validation"] == {"min": 1024, "max": 65535, "pattern": None}
    restored = Question(
        key=d["key"], label=d["label"],
        question_type=d["question_type"],
        validation=ValidationRule(**d["validation"]),
    )
    assert restored == q
```

### C. Fixed mypy src-layout Conflict (Problem 4)

**pyproject.toml:**
```toml
[tool.mypy]
python_version = "3.12"
strict = true
explicit_package_bases = true
```

**AGENTS.md:**
```diff
-| Type check | `uv run mypy src/` |
+| Type check | `uv run mypy -p forge` |
```

### D. Added Dev Dependencies and py.typed (Problem 5)

- `uv add --dev ruff mypy pytest pytest-cov`
- Created `src/forge/py.typed` (empty marker file)

## 4. Technical Issues Found During Implementation

| Finding | Discovery Method |
|---------|-----------------|
| No test files in any production ticket (001–015) | Reading all 18 tickets |
| TDD Reviewer not invoked before implementation | Not following pipeline.md Step 1 |
| `dataclasses.asdict()` flattens nested dataclasses to dicts | Test failure on `Question(**asdict(q))` equality |
| Mypy src-layout + editable install conflict | Running `mypy src/` |
| No dev dependencies installed | Running `ruff check src/` → "command not found" |
| Missing `py.typed` marker | Mypy `import-untyped` error on local package |
| Duplicate `from __future__ import annotations` | Ruff `F401` unused import |

## 5. Final Implementation

### Files Created

```
src/forge/domain/__init__.py
src/forge/domain/project_spec.py
src/forge/domain/generated_file.py
src/forge/domain/questions.py
src/forge/py.typed

tests/unit/test_domain_models.py
```

### Files Modified

```
docs/context/pipeline.md              — Added Test-First Gate (Step 2)
docs/context/dependency-analysis.md   — Created with full dependency graph
AGENTS.md                             — Fixed mypy command
pyproject.toml                        — Added mypy config, dev dependencies
```

### Quality Gate

| Check | Result |
|-------|--------|
| `ruff check src/ tests/` | ✅ All checks passed |
| `ruff format --check` | ✅ 4 files already formatted |
| `mypy -p forge` | ✅ Success, 15 source files |
| `pytest tests/unit/test_domain_models.py -v` | ✅ 22 passed |

## 6. Test Coverage

| Class | Tests | Covers ACs | Status |
|-------|-------|------------|--------|
| `TestAC1_Importability` | 1 | AC-01 | ✅ |
| `TestAC2_PluginConfigHappyPath` | 1 | AC-02 | ✅ |
| `TestAC3_PluginConfigKeyError` | 1 | AC-03 | ✅ |
| `TestAC4_DomainSlug` | 5 | AC-04 | ✅ |
| `TestAC5_QuestionRoundTrip` | 2 | AC-05 | ✅ |
| `TestAC6_TemplateDefinition` | 2 | AC-06 | ✅ |
| `TestAC7_NoCrossLayerImports` | 1 | AC-07 | ✅ |
| `TestAC8_GeneratedFile` | 2 | AC-08 | ✅ |
| `TestAC9_DurationEstimate` | 2 | AC-09 | ✅ |
| `TestEdgeCases` | 5 | — (extra) | ✅ |
| **Total** | **22** | **9 ACs** | ✅ |

### AC Coverage Breakdown

| AC | Happy Path | Error Case | Edge Cases |
|----|-----------|------------|------------|
| AC-01: Importability | ✅ `import forge.domain` | — | — |
| AC-02: plugin_config returns | ✅ dict equality | — | — |
| AC-03: plugin_config raises | — | ✅ `pytest.raises(KeyError)` | — |
| AC-04: Domain slug | ✅ basic slug | — | ✅ 5 sub-cases |
| AC-05: Question round-trip | ✅ asdict round-trip | — | ✅ validation=None |
| AC-06: TemplateDefinition | ✅ construction | — | ✅ frontend_id default |
| AC-07: No forbidden imports | — | ✅ ast scanner | — |
| AC-08: GeneratedFile | ✅ construction | — | ✅ executable default |
| AC-09: DurationEstimate | ✅ construction | — | ✅ empty list |

## 7. Outstanding Issues

### Non-Blocking

- [ ] LOW: AC-5 round-trip covers `validation=None` only — a non-None `ValidationRule` round-trip requires a custom serialization helper
- [ ] LOW: No integration tests exist for domain models (deferred to T-016)
- [ ] LOW: No conftest.py in `tests/unit/` yet — will be needed by T-002+ for shared fixtures

### Resolved During Implementation

- [x] Test file missing for T-001 → retrofitted `tests/unit/test_domain_models.py` with 22 tests
- [x] Pipeline lacked test-first workflow → added Test-First Gate (Step 2)
- [x] Question round-trip with ValidationRule failed → test documents the limitation
- [x] Mypy src-layout conflict → added `explicit_package_bases` + `mypy -p forge`
- [x] Missing dev dependencies → added via `uv add --dev`
- [x] Missing `py.typed` marker → created
- [x] Duplicate `from __future__` import → removed

## 8. Lessons Learned

### What Went Well

1. **The ACs were well-specified.** Unlike the template example (which had 3 vague ACs needing expansion to 8), T-001 had 9 concrete ACs with explicit edge cases. The implementation required zero spec changes.

2. **Static analysis for AC-7 is the right approach.** Using `ast.parse()` to scan domain files for forbidden imports is clean, deterministic, and doesn't require mocking the nonexistent Forge layers. This pattern should be reused in future tickets that need layer-purity guarantees.

3. **Greenfield implementation was straightforward.** With no existing code to refactor, the domain models were created from scratch following the ticket's API spec exactly. No architectural surprises.

4. **The dependency analysis document captured the full picture.** Creating `docs/context/dependency-analysis.md` during the impact analysis revealed the complete dependency chain across all 18 tickets, including the gap that no ticket creates unit tests for domain models.

### What Could Improve

1. **Enforce the Test-First Gate mechanically, not just by instruction.** The pipeline now describes the gate, but there's no mechanism to prevent an agent from skipping it. Consider a pre-execution hook or a checklist that must be acknowledged before implementation begins.

2. **Embed test files in every production ticket's "Files to create" section.** The current convention of separating test files into T-016/017/018 creates a 15-ticket gap where the foundation is unverified. Each ticket should list `tests/unit/test_<module>.py` alongside its source files.

3. **Verify the toolchain before coding.** The missing ruff/mypy/pytest dependencies and the mypy src-layout issue cost ~10 minutes of debugging across the quality gate. A pre-flight check (`uv sync --dev && mypy -p forge && ruff check src/`) before any implementation would surface these immediately.

4. **Account for `dataclasses.asdict()` behavior with nested dataclasses.** The AC-5 round-trip test for non-None `ValidationRule` failed because `asdict()` type-erases nested dataclasses to plain dicts. The ticket's implementation notes documented this, but the initial test didn't account for it. When writing tests that use `asdict()`, always verify nested dataclass handling explicitly.

5. **Run the full quality gate before declaring done, not just pytest.** The initial verification ran only pytest. Running ruff and mypy afterward found 5 additional issues (unused imports, line length, mypy config, truthy-function warnings) that pytest alone would never catch.

### Key Metrics

| Metric | Value |
|--------|-------|
| Original ACs | 9 |
| Test files created | 1 |
| Source files created | 5 (4 domain + 1 py.typed) |
| Total tests | 22 |
| Test failures on first run | 3 (fixed) |
| Ruff issues | 2 (fixed) |
| Mypy issues | 8 (fixed) |
| Pipeline changes | 1 (added Test-First Gate) |
| Infrastructure fixes | 4 (mypy config, dev deps, py.typed, AGENTS.md) |
| Test-First Gate compliance | Retroactive (tests written after code) |

## 9. Acceptance Criteria Verification

| AC | Test(s) | Verification Method | Status |
|----|---------|---------------------|--------|
| AC-01 | `test_all_models_importable` | Import + `__name__` assertions on all 8 models | ✅ |
| AC-02 | `test_returns_config_for_existing_plugin` | `plugin_config("fastapi")` returns `{"orm": "sqlalchemy"}` | ✅ |
| AC-03 | `test_raises_key_error_for_missing_plugin` | `pytest.raises(KeyError)` on `plugin_config("django")` | ✅ |
| AC-04 | 5 tests in `TestAC4_DomainSlug` | Direct `Domain(name=...).slug` assertions | ✅ |
| AC-05 | 2 tests in `TestAC5_QuestionRoundTrip` | `dataclasses.asdict()` + `Question(**asdict(q))` round-trip | ✅ |
| AC-06 | 2 tests in `TestAC6_TemplateDefinition` | Construction + `frontend_id=None` default | ✅ |
| AC-07 | `test_no_imports_from_other_forge_layers` | `ast.parse()` scanning domain source files | ✅ |
| AC-08 | 2 tests in `TestAC8_GeneratedFile` | Construction + `executable=False` default | ✅ |
| AC-09 | 2 tests in `TestAC9_DurationEstimate` | Construction + empty `slow_step_details` | ✅ |

## 10. Timeline

| Date | Activity |
|------|----------|
| June 6, 2026 | Ticket implementation started without TDD review or test-first workflow |
| June 6, 2026 | Domain model files created (`project_spec.py`, `questions.py`, `generated_file.py`, `__init__.py`) |
| June 6, 2026 | Quality gate failed — missing dev dependencies, mypy src-layout conflict |
| June 6, 2026 | Infrastructure fixes: `uv add --dev`, `py.typed`, mypy config, AGENTS.md update |
| June 6, 2026 | Dependency analysis created (`docs/context/dependency-analysis.md`) |
| June 6, 2026 | Pipeline.md updated with Test-First Gate (Step 2) |
| June 6, 2026 | Unit tests retrofitted in `tests/unit/test_domain_models.py` (22 tests) |
| June 6, 2026 | 3 test failures fixed (asdict flattening, slug special chars, TemplateDefinition attrs) |
| June 6, 2026 | Full quality gate: ruff ✅, mypy ✅, 22/22 pytest ✅ |
| June 6, 2026 | Post-mortem written |

## 11. Next Steps

1. Follow the Test-First Gate for all future tickets — write tests before implementation
2. Consider embedding `tests/unit/test_<module>.py` in each production ticket's "Files to create"
3. Create `tests/unit/conftest.py` when shared fixtures are needed by T-002+
4. Revisit the custom serialization helper for nested `ValidationRule` round-trips when T-005 (ValidationEngine) is designed
5. Add a pre-flight check to the pipeline: `uv sync --dev && mypy -p forge && ruff check src/` before any implementation
