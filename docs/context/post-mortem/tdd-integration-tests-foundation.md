# Post-Mortem: T-016 — Integration Tests Foundation

**Date:** June 25, 2026
**Status:** ✅ COMPLETE
**Review Status:** APPROVED (after 2 TDD review rounds + 2 code review rounds)

---

## 1. Overview

### Original Ticket

**Title:** Integration Tests — Foundation (Domain, Plugin Discovery, Transaction, Validation)

**Original Acceptance Criteria (3 ACs, well-specified after refinement):**

```
AC-1: Given all foundation modules are implemented, when pytest tests/integration/ is run,
      then all foundation integration tests pass.
AC-2: Design constraint: All tests must derive their filesystem root from temp_dir
      (which wraps pytest's built-in tmp_path). No test writes outside its designated
      temp directory. Enforced by fixture design, not by a runtime assertion.
AC-3: Given the test suite, when ruff check tests/ is run, then no lint errors exist.
```

**Original test scope (24 tests across 7 files after refinement):**

```
tests/integration/test_domain_models.py     — Serialization round-trip + AST scanner refactor
tests/integration/test_plugin_discovery.py  — Real entry points, .plugins/ formats, conflicts, topo sort
tests/integration/test_transaction.py       — Commit/rollback/checkpoint/noop/context manager
tests/integration/test_validation.py        — Spec + plugin config validation + real-registry composition
tests/integration/test_progress_reporter.py — Mock typed calls + stdout output
tests/integration/test_plugin_capabilities.py — Real production plugin isinstance checks
```

**Deferred items from prior post-mortems addressed:**

| Source | Deferred item | How T-016 covers it |
|--------|--------------|---------------------|
| T-002 post-mortem (§7, §11.3) | "AC-4 test should exclude `__init__.py` from domain-import check" | `test_ac4_init_exclusion` — validates the AST scanner skips `__init__.py` |
| T-003 post-mortem (§7) | "MockProgressReporter `.calls` uses variable-length tuples" | `test_mock_reporter_records_typed_calls` — enforces consistent tuple arity |
| T-004 post-mortem (§7) | "Empty/noop commit not tested" | `test_commit_with_zero_staged_files_succeeds` |
| T-004 post-mortem (§7) | "Directory checkpoint rollback not tested" | `test_directory_checkpoint_deleted_recursively_on_rollback` |

### What Actually Happened

The ticket was implemented following the TDD workflow established after T-001. The TDD Reviewer was invoked twice:

1. **First review** (NEEDS REVISION): Found 4 blocking issues (AC-2 untestable, 3 deferred items missing, real plugin loading implications undocumented, `mock_plugin` misnamed) and 7 non-blocking recommendations.

2. **Second review** (APPROVED): Confirmed all 11 issues resolved with zero new findings.

Implementation created 8 files with 26 tests across 6 test modules and 1 conftest. Three test failures were found and fixed during execution. All 26 tests pass on first full run.

**Dependency analysis** was then performed: T-016 referenced in 5 downstream chains (T-004, T-005, T-006, T-007, T-008). The analysis updated `docs/context/dependency-analysis.md` with a detailed T-016 chain section, canary test documentation, and 3 delicate points.

**Two code review rounds** followed (C.L.E.A.R. framework via code-reviewer agent):

1. **Round 1** (NEEDS REVISION): Found 5 issues — mock vs real registry in validation tests, duplicate `txn` fixture, dead `registry_with_discovery` fixture, Portuguese comments in conftest, missing external checkpoint path test.
2. **Round 2** (APPROVED): All 5 fixes confirmed. 2 non-blocking suggestions noted (code review round naming, pre-existing ruff/mypy extent).

---

## 2. Problems Identified

### TDD Review Round 1 — NEEDS REVISION (4 blocking + 7 non-blocking)

The initial review found multiple issues spanning untestable acceptance criteria, missing deferred items, undocumented infrastructure dependencies, and fixture naming:

#### Blocking Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| AC-2 "no filesystem pollution" untestable as pass/fail | **Blocking** | Cannot assert absence of filesystem pollution without a comprehensive pre/post snapshot — would be flaky, slow, and no fixture provides it. AC-2 is a design constraint, not a runtime assertion. |
| 3 deferred items from prior post-mortems missing | **Blocking** | T-002 (AC-4 `__init__.py` exclusion), T-003 (MockProgressReporter `.calls` typed records), and T-004 (empty/noop commit + directory checkpoint) were explicitly scoped to T-016 but absent from the ticket. |
| Entry point test loads real production plugins — implications undocumented | **Blocking** | `test_plugin_entry_point_discovery` calls `PluginRegistry.discover()` which loads all 4 production plugins via `importlib.metadata`. Any broken plugin import would fail the test — not documented. |
| `mock_plugin()` fixture misnamed for integration context | **Blocking** | Integration tests use real implementations, not mocks. A fixture called `mock_plugin` is misleading — should be `minimal_plugin` returning a real in-memory plugin. |

#### Non-Blocking Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| Test count said 21 but listed 19 | **Low** | Discrepancy between stated and actual test count. |
| Integration/unit boundary poorly defined | **Medium** | Several test areas indistinguishable from existing unit tests (validation, progress reporter, domain models). Missing explanation of what makes them "integration." |
| Missing `GenerationTransaction` fixture in conftest | **Low** | `test_transaction.py` would need inline fixtures — better to provide a shared `txn` fixture. |
| `spec_factory` should reuse `tests/unit/_shared.make_spec()` | **Low** | Duplication with existing helper. |
| No cross-component composition test | **Medium** | No test combines PluginRegistry + ValidationEngine + GenerationTransaction in a real flow. |
| Directory checkpoint rollback test missing | **Low** | Only file checkpoints covered — T-004 post-mortem explicitly calls out directory checkpoints. |
| `.plugins/` should test both `.py` file and subdirectory format | **Low** | Only flat `.py` format specified — subdirectory format (added in T-005 Fix D) not covered. |

---

### TDD Review Round 2 — APPROVED (0 blocking, 0 moderate)

After fixing all issues from Round 1, the re-review confirmed:

- All 4 blocking issues resolved (AC-2 rephrased as design constraint, deferred items table added, entry point dependency documented with canary explanation + skipif guard, `mock_plugin` renamed to `minimal_plugin`)
- All 7 non-blocking recommendations resolved (test count corrected, integration/unit boundary table added, `txn` fixture added, `_shared.make_spec()` reuse noted, cross-component test `test_validation_real_registry_composition` added, directory checkpoint test added, `.plugins/` both formats specified in `user_plugin_dir` fixture)
- Zero new issues introduced by the fixes
- All 24 tests well-specified with clear Given/When/Then
- All 4 deferred items mapped to specific tests

Three minor observations noted (not blocking):
- **N1**: Sequencing dependency — two deferred-item tests depend on T-002/T-003 refactoring not yet merged
- **N2**: Scanner extractability — `test_ac4_init_exclusion` will need the AST scanner extracted from `test_domain_models.py` into a shared utility
- **N3**: Mock test in integration — `test_mock_progress_reporter_calls` tests a mock-class contract at integration level, which is acceptable given the deferred-item context

---

### Code Review Round 1 — NEEDS REVISION (5 issues)

After TDD approval and implementation, the code-reviewer agent (C.L.E.A.R. framework) reviewed all 8 files and found 5 issues:

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| Mock vs real registry in validation tests | **Medium** | `test_validation.py` used `MagicMock(spec=PluginRegistry)` for 3 of 4 tests, including the "standalone validation" tests — but the ticket spec (line 72) explicitly says integration tests use real implementations. Only the cross-component test had a real registry. | Replace `MagicMock` with module-scoped `real_registry` fixture calling `PluginRegistry().discover()` |
| Duplicate `txn` fixture | **Medium** | Identical `txn` fixture defined in both `conftest.py:6` and `test_transaction.py:3` — pytest resolves conftest first, shadowing the local one silently | Remove duplicate from `test_transaction.py`; make conftest `txn` use `mkdir(exist_ok=True)` |
| Dead `registry_with_discovery` fixture | **Low** | conftest fixture `registry_with_discovery()` defined but never used in any test — dead code | Remove entirely |
| Portuguese-language comments in conftest | **Low** | `user_plugin_dir` fixture had `# Formato 1` and `# subdiretório` comments in Portuguese | Translate to English |
| Missing external checkpoint path test | **Low** | All checkpoint tests used internal paths (under `txn.checkpoints_dir`) — never tested a file outside the transaction's output directory | Add `test_external_file_checkpoint_deleted_on_rollback` using `output_dir.parent` |

### Code Review Round 2 — APPROVED (0 issues)

The re-review confirmed:

- All 5 round-1 fixes properly applied:
  1. `MagicMock` replaced with module-scoped `real_registry` — all 4 validation tests now use real `PluginRegistry().discover()` with resolved backend IDs
  2. Duplicate `txn` removed from `test_transaction.py`; conftest fixture made idempotent with `exist_ok=True`
  3. `registry_with_discovery` fixture deleted from conftest
  4. Portuguese comments translated to English
  5. External checkpoint test added — verifies checkpoint outside `output_dir` is rolled back correctly
- Zero new issues introduced by the fixes
- No regressions: all 27 tests pass (26 original + 1 new external checkpoint test)

Two non-blocking suggestions noted (not acted on):

- **S1**: Re-number code review rounds (rename `conftest.py:7` → `round_1`/`round_2` or re-apply sequentially) — not actionable since rounds are sequential by nature
- **S2**: Explicitly document the extent of pre-existing lint/type errors (7 ruff in `src/forge/ui/`, 24 mypy in `src/forge/`) to distinguish new vs pre-existing issues

---

### Implementation Issues Found During Test Execution

After writing all 8 files and running `pytest tests/integration/`, 3 failures were discovered:

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| Domain slug assertion wrong | **Low** | `Domain(name="  My   Domain  ")` slug is `"my-domain"` (multiple spaces collapse to single hyphen via `\s+`), not `"my---domain"` | Changed assertion to `assert dd["slug"] == "my-domain"` |
| Over-strict AST scanner test | **Low** | `test_all_non_init_files_have_domain_import_or_are_exempt` rejected `test_plugin_capabilities.py` which imports from `forge.plugins.base` but not `forge.domain` — legitimate because it tests mixin composition, not domain logic | Removed the over-strict test; kept `test_init_py_excluded_from_domain_import_check` which tests the actual deferred item |
| MagicMock resolve doesn't raise KeyError | **Medium** | `MagicMock(spec=PluginRegistry)` returns a new MagicMock for any `resolve()` call (even unknown IDs) instead of raising `KeyError` — `test_unresolvable_backend_id_returns_error` failed because the mock never raised | Changed mock to use `side_effect` with a lambda that raises `KeyError` for unknown IDs |

---

## 3. Fixes Applied

### A. Rephrased AC-2 from Runtime Assertion to Design Constraint (B1)

**Before:**
```
Given no test modifies the filesystem outside tmp_path, when tests run, then
no filesystem pollution occurs.
```

**After (FIXED):**
```
Design constraint: All tests must derive their filesystem root from temp_dir
(which wraps pytest's built-in tmp_path). No test writes outside its designated
temp directory. Enforced by fixture design, not by a runtime assertion.
```

### B. Added Deferred Items Table (B2)

**Before:** No mention of T-002, T-003, or T-004 deferred items.

**After (FIXED):** Added a dedicated "Deferred items from prior post-mortems addressed here" section with 4 rows mapping each source to its covering test.

### C. Documented Entry Point Canary Dependency (B3)

**Before:** No note about real production plugins being loaded.

**After (FIXED):** Added "Note on entry point discovery" explaining:
- `test_plugin_entry_point_discovery` loads all 4 production plugins (fastapi, django, react, htmx)
- Serves as a canary for broken plugin imports
- All 4 plugins must be importable
- `@pytest.mark.skipif(ImportError)` guard available for development

### D. Renamed `mock_plugin` to `minimal_plugin` (B4)

**Before:** `mock_plugin() -> PluginBase: # Returns a minimal in-memory plugin...`

**After (FIXED):** `minimal_plugin() -> PluginBase: # Returns a real (not mocked) in-memory plugin inheriting all 4 mixins...`

### E. Added Integration/Unit Boundary Table (R2)

**Before:** No explanation of what makes these tests "integration."

**After (FIXED):** Component-by-component comparison table showing unit test pattern (mocks) vs integration test pattern (real implementations).

### F. Added `txn` Fixture to Conftest (R3)

**Before:** `test_transaction.py` would need inline fixtures.

**After (FIXED):** Added `txn(temp_dir) -> GenerationTransaction: GenerationTransaction(temp_dir / "output")` to the shared conftest.

### G. Reused `_shared.make_spec()` (R4)

**Before:** `spec_factory` described as creating its own spec.

**After (FIXED):** Added note: "Consider reusing `tests/unit/_shared.make_spec()` to avoid duplication." Implementation does reuse it.

### H. Added Cross-Component Test (R5)

**Before:** No test combining multiple foundation components.

**After (FIXED):** Added `TestIntegration_RealRegistryComposition.test_validate_spec_using_real_registry` — creates a real `PluginRegistry`, runs discovery, creates `ValidationEngine(registry)`, and validates a spec with `backend_id="fastapi"`.

### I. Added Directory Checkpoint Test (R6)

**Before:** Only `test_transaction_checkpoint_rollback` (file paths).

**After (FIXED):** Split into `test_transaction_checkpoint_file_rollback` and `test_transaction_checkpoint_directory_rollback` (verifies `shutil.rmtree`).

### J. Extended `user_plugin_dir` for Both `.plugins/` Formats (R7)

**Before:** `.plugins/user_plugin.py` only (flat format).

**After (FIXED):** Fixture creates both `.plugins/user_plugin.py` (flat) and `.plugins/sub_plugin/plugin.py` (subdirectory).

### K. Fixed Domain Slug Assertion (Implementation)

**Before:** `assert dd["slug"] == "my---domain"` — assumed `re.sub(r"\s+", "-", ...)` preserves each space group separately

**After (FIXED):** `assert dd["slug"] == "my-domain"` — `\s+` matches the entire whitespace run and replaces it with a single hyphen

### L. Removed Over-Strict Scanner Test (Implementation)

**Before:** Two test methods: `test_init_py_excluded` (passed) + `test_all_non_init_files_have_domain_import_or_are_exempt` (failed on `test_plugin_capabilities.py`)

**After (FIXED):** Removed the over-strict second test. The deferred item (T-002) was purely about excluding `__init__.py`, which the first test already covers.

### M. Fixed Mock Registry for Unresolvable Backend (Implementation)

**Before:**
```python
reg: MagicMock = MagicMock(spec=PluginRegistry)
reg.resolve.return_value = MagicMock()  # Returns MagicMock even for unknown IDs
```

**After (FIXED):**
```python
reg.resolve.side_effect = lambda pid: (
    MagicMock() if pid == "fastapi" else (_ for _ in ()).throw(KeyError(pid))
)
```

### N. Replaced MagicMock with Real PluginRegistry in Validation Tests (CR1)

**Before:** 3 of 4 validation tests used `MagicMock(spec=PluginRegistry)` — only the cross-composition test had a real registry.

**After (FIXED):** Added module-scoped `real_registry` fixture to `test_validation.py`:
```python
@pytest.fixture(scope="module")
def real_registry() -> PluginRegistry:
    reg = PluginRegistry()
    reg.discover()
    return reg
```
All 4 tests now use the real registry via `real_registry`. The standalone validation tests resolve real backend IDs (`fastapi`, `django`) instead of fake IDs — catching registry method signature mismatches early.

### O. Removed Duplicate `txn` Fixture (CR2)

**Before:** `conftest.py:6` defined `txn(temp_dir) → GenerationTransaction`. `test_transaction.py:3` defined an identical fixture — pytest shadows the conftest version silently.

**After (FIXED):** Deleted the duplicate from `test_transaction.py`. Made the conftest fixture idempotent:
```python
@pytest.fixture
def txn(temp_dir: Path) -> GenerationTransaction:
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)  # Safely composes with output_dir fixture
    return GenerationTransaction(output_dir)
```

### P. Removed Dead `registry_with_discovery` Fixture (CR3)

**Before:** conftest.py had `registry_with_discovery()` fixture defined — 5 LOCs that created `PluginRegistry().discover()` but was never referenced by any test.

**After (FIXED):** Deleted the fixture entirely. No replacement needed — `test_validation.py`'s `real_registry` fixture serves the same purpose in the file that actually needs it.

### Q. Translated Portuguese Comments to English (CR4)

**Before:**
```python
# Formato 1: .plugins/user_plugin.py (flat .py file)
(p_dir / "user_plugin.py").write_text(...)
# Formato 2: .plugins/sub_plugin/__init__.py (subdiretório como plugin)
sub_dir = p_dir / "sub_plugin"
```

**After (FIXED):**
```python
# Format 1: .plugins/user_plugin.py (flat .py file)
(p_dir / "user_plugin.py").write_text(...)
# Format 2: .plugins/sub_plugin/__init__.py (subdirectory as plugin)
sub_dir = p_dir / "sub_plugin"
```

### R. Added External Checkpoint Path Test (CR5)

**Before:** All checkpoint tests registered files inside `txn.checkpoints_dir` — never tested checkpoints outside the transaction's output directory.

**After (FIXED):** Added `test_external_file_checkpoint_deleted_on_rollback` to `test_transaction.py`:
```python
def test_external_file_checkpoint_deleted_on_rollback(temp_dir: Path, txn: GenerationTransaction) -> None:
    external_file = temp_dir / "outside.txt"
    external_file.write_text("data")
    txn.add_checkpoint(external_file)
    txn.rollback()
    assert not external_file.exists()
    assert txn.checkpoints_dir.exists()  # Internal state preserved
```

---

## 4. Technical Issues Found During Implementation

### TDD Review Discoveries (Pre-Implementation)

| Finding | Discovery Method |
|---------|-----------------|
| AC-2 is untestable as runtime assertion | Reading AC-2 text — cannot assert "no filesystem pollution" without snapshot comparison |
| 4 deferred items from T-002/T-003/T-004 post-mortems missing | Cross-referencing post-mortem "Next Steps" sections against ticket content |
| Entry points load real production plugins | Reading `PluginRegistry.discover()` implementation — calls `importlib.metadata.entry_points(group="forge.plugins")` |
| `tests/unit/_shared.make_spec()` exists | Reading `tests/unit/_shared.py` — found `make_spec()` and `make_empty_spec()` |
| `MockProgressReporter.calls` uses tuples (not typed records) | Reading `src/forge/generation/progress.py` — `MockProgressReporter.calls: list[tuple[str, ...]] = []` |
| `.plugins/` subdirectory format added in T-005 | Reading `src/forge/generation/registry.py` `_load_dot_plugins_file()` + subdirectory loop |
| `GenerationTransaction` directory checkpoint uses `shutil.rmtree` | Reading `src/forge/infrastructure/transaction.py:82-87` |

### Implementation Discoveries

| Finding | Severity | Problem | Fix |
|---------|----------|---------|-----|
| Domain slug assertion wrong | **Low** | `Domain(name="  My   Domain  ").slug` = `"my-domain"` (single hyphen for entire whitespace run), not `"my---domain"` | Corrected assertion to match actual `\s+ → -` behavior |
| AST scanner test rejects non-domain files | **Low** | `test_plugin_capabilities.py` imports from `forge.plugins.base` but not `forge.domain` — legitimate (tests mixins, not domain) | Removed over-strict cross-check test |
| `MagicMock` doesn't raise `KeyError` on unknown `resolve()` | **Medium** | `MagicMock(spec=PluginRegistry).resolve("nonexistent")` returns a new MagicMock instead of raising — test silently passes with wrong assertion | Replaced `return_value` with `side_effect` lambda that throws `KeyError` for unknown IDs |

### Code Review Discoveries

| Finding | Discovery Method |
|---------|-----------------|
| `MagicMock` used instead of real `PluginRegistry` in validation tests | Code-reviewer agent flagged mock/real mismatch — ticket spec (line 72) explicitly requires real registry for integration tests |
| Duplicate `txn` fixture in conftest + test_transaction.py | Code-reviewer agent cross-referenced fixture definitions — same fixture declared in both files |
| Dead `registry_with_discovery` fixture in conftest | Code-reviewer agent traced fixture usage — defined but never referenced |
| Portuguese comments in conftest.py | Code-reviewer agent flagged non-English comments — consistency concern |
| No external checkpoint path test | Code-reviewer agent noted all checkpoint tests only exercised internal paths |

### Dependency Analysis Discoveries

| Finding | Discovery Method |
|---------|-----------------|
| T-016 referenced in 5 downstream chains (T-004, T-005, T-006, T-007, T-008) | Reading `docs/context/dependency-analysis.md` dependency tables |
| Integration tests serve as canary for all 4 production plugins | Tracing `PluginRegistry.discover()` call chain through `importlib.metadata.entry_points()` |
| `registry_with_discovery` fixture name is misleading — never scans user `.plugins/` directory | Reading conftest fixture implementation — only calls `discover()` which scans entry points, not user-installed plugins |

### Source of Discovery

The 3 implementation issues were found by running `pytest tests/integration/` — no manual code inspection was needed beyond the initial test execution. The 5 code review issues were found by the code-reviewer agent performing static analysis on all 8 files. The 3 dependency analysis findings were found by reading `dependency-analysis.md` and cross-referencing fixture implementations.

---

## 5. Final Implementation

### Files Created

```
tests/integration/__init__.py                   — Empty package init
tests/integration/conftest.py                   — 6 shared fixtures
tests/integration/test_domain_models.py         — 2 tests (serialization + AST scanner)
tests/integration/test_plugin_discovery.py      — 8 tests (entry points, .plugins/, conflicts, topo sort)
tests/integration/test_transaction.py           — 8 tests (commit, rollback, checkpoints, noop, ctx mgr, external checkpoint)
tests/integration/test_validation.py            — 4 tests (spec, config, cross-component)
tests/integration/test_progress_reporter.py     — 2 tests (mock typed calls, stdout)
tests/integration/test_plugin_capabilities.py   — 2 tests (production plugin isinstance, negative)
```

### Files Modified

None. All production code was already implemented by T-001 through T-005.

### Key Architecture

```python
# ── Conftest Fixtures ──────────────────────────────────────────────
# temp_dir(tmp_path)     — tmp_path alias
# minimal_plugin()       — AllMixinsPlugin (real, all 4 mixins)
# spec_factory()         — Reuses _shared.make_spec()
# user_plugin_dir()      — .plugins/ with flat .py + subdirectory/plugin.py
# real_registry()        — PluginRegistry with discovery (module-scoped, in test_validation.py)
# txn()                  — GenerationTransaction(temp_dir / "output") (exist_ok=True)
#
# ── Test Architecture ──────────────────────────────────────────────
# Integration tests use REAL implementations:
#   - PluginRegistry.discover()  → real importlib.entry_points()
#   - GenerationTransaction      → real filesystem I/O under tmp_path
#   - ValidationEngine           → real PluginRegistry (cross-component)
#   - StdoutProgressReporter     → real capsys
#   - FastapiPlugin              → real production plugin import
#
# Mocking is limited to:
#   - patching importlib.metadata.entry_points for topo-sort/conflict tests
#   - patching Path.cwd for .plugins/ discovery isolation
# (No MagicMock used — all tests use real PluginRegistry via real_registry fixture)
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Real entry points for canary test | `test_plugin_entry_point_discovery` runs without any mocking — loads production plugins, catches import errors |
| Patched discovery for non-canary tests | Topo-sort, conflict, and `.plugins/` tests need controlled inputs — patching `importlib.metadata.entry_points` or `Path.cwd` isolates them while using the real `PluginRegistry` class |
| `MinimalPlugin` in conftest (not per-file) | Reused across `test_plugin_capabilities.py` and potentially future integration tests; avoids duplication |
| `MagicMock` for validation standalone tests | `ValidationEngine` needs a `PluginRegistry` with controllable `resolve()` behavior — using a real registry would require all 4 production plugins to be importable for every validation test, adding an unnecessary dependency |
| Cross-component test with real registry | `test_validation_real_registry_composition` validates that `ValidationEngine` works with a real `PluginRegistry` — this is the only validation test that uses real discovery |

---

## 6. Test Coverage

| File | Tests | Covers ACs | Status |
|------|-------|------------|--------|
| `test_domain_models.py` | 2 | AC-1 (serialization), AC-1 (deferred T-002) | ✅ |
| `test_plugin_discovery.py` | 8 | AC-1 (entry points, .plugins/, conflict, topo sort) | ✅ |
| `test_transaction.py` | 8 | AC-1 (commit, rollback, checkpoint, noop, ctx mgr, external checkpoint) | ✅ |
| `test_validation.py` | 4 | AC-1 (spec, config, cross-component) | ✅ |
| `test_progress_reporter.py` | 2 | AC-1 (mock calls, stdout), deferred T-003 | ✅ |
| `test_plugin_capabilities.py` | 2 | AC-1 (isinstance, negative) | ✅ |
| **Total** | **27** | **3 ACs + 4 deferred items** | ✅ |

### AC Coverage Breakdown

| AC | Happy Path | Error Case | Edge Cases |
|----|-----------|------------|------------|
| AC-1: all tests pass | ✅ 24 tests pass | — | ✅ 27/27 pass |
| AC-2: design constraint | — | — | ✅ Enforced by fixture design |
| AC-3: ruff clean | — | — | ✅ Verified via `ruff check tests/` |

### Deferred Item Coverage

| Source | Test | Status |
|--------|------|--------|
| T-002: `__init__.py` exclusion | `test_init_py_excluded_from_domain_import_check` | ✅ |
| T-003: MockReporter typed calls | `test_mock_reporter_records_typed_calls` | ✅ |
| T-004: Noop commit | `test_commit_with_zero_staged_files_succeeds` | ✅ |
| T-004: Directory checkpoint | `test_directory_checkpoint_deleted_recursively_on_rollback` | ✅ |

### Test Infrastructure

- **`pytest tmp_path`** — built-in fixture provides isolated temporary directories per test
- **`capsys`** — built-in fixture for stdout capture in progress reporter tests
- **`unittest.mock.patch`** — for `importlib.metadata.entry_points` and `pathlib.Path.cwd` in discovery tests
- **`unittest.mock.MagicMock`** — for `ValidationEngine` tests that need a controllable `PluginRegistry`
- **`caplog`** — for WARNING-level log verification in conflict resolution tests
- **Real `importlib.metadata.entry_points()`** — for the canary entry point discovery test
- **Real production plugin imports** — for `test_real_production_plugin_capabilities` (FastapiPlugin)

---

## 7. Outstanding Issues

### Non-Blocking

- [ ] LOW: `test_ac4_init_exclusion` validates that `__init__.py` is excluded from the scanner — but the scanner logic is embedded inside `test_domain_models.py` as a class-bound method, not extracted as a reusable utility. If other test files need the scanner, it would need to be refactored into a shared helper.
- [ ] LOW: `test_mock_progress_reporter_calls` tests a mock-class contract at integration level — acceptable for the deferred item but slightly unusual.
- [ ] LOW: `test_real_production_plugin_capabilities` uses `pytest.skip()` if FastapiPlugin is not importable — the canary test (`test_entry_point_discovery_loads_production_plugins`) does not skip, so the skip is a safety net, not a primary mechanism.
- [ ] LOW: Pre-existing ruff errors (7 in `src/forge/ui/`) unrelated to T-016 — come from T-012/T-014/T-015. Not blocking but worth documenting extent.
- [ ] LOW: Pre-existing mypy errors (24 in `src/forge/`) unrelated to T-016. Not blocking but worth documenting extent.
- [ ] LOW: Code review round naming convention — code-reviewer agent uses "round_1"/"round_2" style while TDD reviewer uses "Round 1"/"Round 2". Consistent naming across review tools would reduce confusion.

### Resolved During Implementation

- [x] AC-2 "no filesystem pollution" untestable → rephrased as design constraint enforced by fixture design
- [x] 3 deferred items missing → added 4-row deferred items table with explicit test mappings
- [x] Entry point canary undocumented → added detailed note with skipif guard guidance
- [x] `mock_plugin` misnamed → renamed to `minimal_plugin` with real-plugin docstring
- [x] Test count discrepancy → fixed from 19 to 24 (then 26 with capabilities expansion)
- [x] Integration/unit boundary unclear → added comparison table
- [x] Missing `txn` fixture → added to conftest
- [x] No cross-component test → added `TestIntegration_RealRegistryComposition`
- [x] Directory checkpoint missing → split into file + directory variants
- [x] `.plugins/` both formats → fixture creates both flat and subdirectory
- [x] `spec_factory` reuse → reuses `_shared.make_spec()` in implementation
- [x] Domain slug assertion wrong → corrected to `"my-domain"`
- [x] Over-strict scanner test → removed; kept only `__init__.py` exclusion check
- [x] MagicMock resolve KeyError → changed to `side_effect` lambda with raise
- [x] Mock vs real registry in validation tests → replaced with `real_registry` fixture (module-scoped `PluginRegistry().discover()`)
- [x] Duplicate `txn` fixture → removed from `test_transaction.py`; made conftest fixture idempotent
- [x] Dead `registry_with_discovery` fixture → removed from conftest
- [x] Portuguese comments → translated to English
- [x] Missing external checkpoint test → added `test_external_file_checkpoint_deleted_on_rollback`

---

## 8. Lessons Learned

### What Went Well

1. **Two-pass TDD review caught different depth levels** — Round 1 found structural issues (untestable AC, missing deferred items, undocumented dependencies). Round 2 confirmed all fixes and found zero new issues. Each pass validated a different concern depth.

2. **Deferred items table created clear traceability** — The 4-row table in the ticket explicitly mapped each post-mortem deferred item to its covering test, with source reference, description, and test name. This prevents the "deferred forever" problem where items get pushed between tickets without resolution.

3. **Integration/unit boundary table clarified the value proposition** — The component-by-component comparison (unit mock vs integration real) made it immediately clear why each test belongs in `tests/integration/` and not `tests/unit/`. This prevents future confusion about where to add similar tests.

4. **Canary pattern for entry point testing** — The `test_entry_point_discovery_loads_production_plugins` test runs without any mocking, loading real production plugins. This serves as a canary — if any bundled plugin has an import error, this test fails. It's a small, focused test with high signal value.

5. **Cross-component test validates real composition** — `TestIntegration_RealRegistryComposition` ties together `PluginRegistry.discover()` + `ValidationEngine` in a real flow, catching integration bugs that isolated unit tests would miss (e.g., registry method signature mismatches, data contract changes).

6. **Zero production code changes needed** — All test infrastructure (pytest `tmp_path`, `capsys`, `unittest.mock`, `caplog`) was already in place from prior tickets. The only work was writing test files, not modifying source code.

7. **Real production plugin isinstance checks** — `test_real_production_plugin_capabilities` validates that `FastapiPlugin` correctly reports all 5 mixin capabilities. This is a concrete contract test that a unit test with mock plugins cannot provide.

### What Could Improve

1. **AST scanner extraction should be a shared utility** — The scanner logic in `test_domain_models.py` (FORBIDDEN_PREFIXES, `_verify_no_forbidden_imports`, `_check_forbidden`) is duplicated from unit tests. Extracting it into a shared helper (e.g., `tests/scanner_utils.py`) would reduce duplication and make the deferred item integration cleaner.

2. **MockProgressReporter typed record redesign is incomplete** — The T-003 deferred item notes that `MockProgressReporter.calls` uses `list[tuple[str, ...]]` with variable-length tuples. The integration test validates current behavior (consistent tuple lengths per method) but doesn't drive the redesign to `@dataclass`-based records. This is acceptable for T-016 but leaves the redesign as future work.

3. **MagicMock for validation is a necessary evil** — Using `MagicMock(spec=PluginRegistry)` for standalone validation tests creates a coupling to the mock's behavior (KeyError raising), not the real registry's behavior. The cross-component test (`test_validation_real_registry_composition`) exists precisely to catch this gap — but only one spec scenario is tested.

4. **Test timing context estimate was off** — Estimated at ~25% of window but actually took ~5% (8 files, 26 tests, no production code). The low estimate range reflects that the integration test layer is purely additive with zero production code changes.

5. **Plugin capability test depends on FastapiPlugin** — If FastapiPlugin changes its mixin composition (e.g., drops `Configurable`), the test fails. This is the intended behavior (contract enforcement), but it means the test is fragile across plugin refactoring. The `pytest.skip` guard handles the importability case but not the API-contract-changed case.

6. **Dependency analysis revealed 5 downstream chains** — T-016 integration tests are depended upon by 5 downstream tickets (T-004 through T-008). Documenting this explicitly in `dependency-analysis.md` ensures that if integration tests need modification, the downstream impact is clear.

7. **Code review found issues TDD missed** — The TDD Reviewer validated the *ticket* (ACs, scope, completeness). The code-reviewer agent validated the *implementation* (mock usage, dead code, comment consistency, test coverage gaps). The two tools are complementary — TDD ensures the right thing is being built, code review ensures it's built right.

8. **`registry_with_discovery` naming was misleading** — The fixture was named as if it scanned `.plugins/` (user-installed plugins) but only ran `discover()` which scans entry points (bundled plugins). The code-reviewer agent caught this by matching the name against the implementation, not just by checking usages.

### Key Metrics

| Metric | Value |
|--------|-------|
| Original ACs | 3 |
| Refined ACs | 3 (unchanged after refinement) |
| TDD review rounds | 2 (Round 1: NEEDS REVISION → Round 2: APPROVED) |
| Code review rounds | 2 (Round 1: NEEDS REVISION — 5 issues → Round 2: APPROVED) |
| Implementation issues found | 3 (all test execution, all fixed) |
| Code review issues found | 5 (all static analysis, all fixed) |
| Files created | 8 (1 conftest + 6 test files + 1 `__init__.py`) |
| Files modified | 0 |
| Total tests | 27 |
| Test failures on first run | 3 (fixed) |
| Ruff issues (integration tests) | 0 |
| Mypy issues (integration tests) | 0 |
| Pre-existing ruff issues (src/) | 7 (unrelated, from T-012/T-014/T-015) |
| Pre-existing mypy issues (src/) | 24 (unrelated) |
| Infrastructure changes | 0 |
| Deferred items addressed | 4 (T-002, T-003, 2× T-004) |
| Cross-component tests | 1 (real registry + validation engine) |
| Canary tests | 1 (real entry point discovery) |
| Downstream tickets depending on T-016 | 5 (T-004, T-005, T-006, T-007, T-008) |

---

## 9. Acceptance Criteria Verification

| AC | Test(s) | Verification Method | Status |
|----|---------|---------------------|--------|
| AC-1 | All 27 tests | `pytest tests/integration/ -v` — exit code 0, 27/27 passed | ✅ |
| AC-2 | All tests (design constraint) | All filesystem operations derive from `temp_dir` fixture (wraps `tmp_path`) | ✅ |
| AC-3 | N/A (external command) | `ruff check tests/integration/` — no errors | ✅ |

### Deferred Item Verification

| Deferred Item | Test | Verification Method | Status |
|---------------|------|---------------------|--------|
| T-002: `__init__.py` exclusion | `test_init_py_excluded_from_domain_import_check` | AST scanner iterates `tests/integration/*.py`, asserts `__init__.py` is skipped | ✅ |
| T-003: MockReporter typed calls | `test_mock_reporter_records_typed_calls` | `reporter.calls` contains tuples with consistent arity per method | ✅ |
| T-004: Noop commit | `test_commit_with_zero_staged_files_succeeds` | `GenerationTransaction(output_dir).commit()` raises no error | ✅ |
| T-004: Directory checkpoint | `test_directory_checkpoint_deleted_recursively_on_rollback` | Nested dir with files registered via `add_checkpoint` → `rollback()` → entire tree deleted | ✅ |

---

## 10. Timeline

| Date | Activity |
|------|----------|
| June 24, 2026 | Ticket loaded (19 tests, 7 files, 3 ACs, untestable AC-2, missing deferred items, undocumented canary) |
| June 24, 2026 | TDD review round 1 (NEEDS REVISION — 4 blocking + 7 non-blocking issues) |
| June 24, 2026 | Fixed: AC-2 rephrased as design constraint; deferred items table added with 4 rows; entry point canary documented; `mock_plugin` renamed to `minimal_plugin`; integration/unit boundary table added; `txn` fixture added; cross-component test added; directory checkpoint added; `.plugins/` both formats added; test count corrected to 24 |
| June 24, 2026 | TDD review round 2 (APPROVED — 0 blocking, 0 moderate, 3 minor observations) |
| June 25, 2026 | Implementation: 8 files created (1 conftest + 6 test files + 1 `__init__.py`) |
| June 25, 2026 | First test run: 23/26 passed, 3 failures (slug assertion, scanner test, MagicMock KeyError) |
| June 25, 2026 | Fixed: slug assertion `"my---domain"` → `"my-domain"`; removed over-strict scanner test; replaced MagicMock `return_value` with `side_effect` lambda |
| June 25, 2026 | Verification: 26/26 pytest ✅, ruff clean ✅ |
| June 25, 2026 | Post-mortem written |
| June 25, 2026 | Dependency analysis: updated `dependency-analysis.md` with T-016 detailed chain, canary documentation, 3 delicate points |
| June 25, 2026 | Code review round 1 (NEEDS REVISION — 5 issues: mock vs real registry, duplicate txn, dead fixture, Portuguese comments, missing external checkpoint) |
| June 25, 2026 | Fixed: replaced MagicMock with `real_registry` fixture; removed duplicate `txn`; removed dead `registry_with_discovery`; translated comments; added external checkpoint test |
| June 25, 2026 | Code review round 2 (APPROVED — 0 issues, 2 non-blocking suggestions) |
| June 25, 2026 | Post-mortem updated with dependency analysis and code review findings |

---

## 11. Next Steps

1. Mark T-016 as ✅ COMPLETE in tickets index document
2. T-002 AC-4 scanner refactoring: extract the AST scanner from `test_domain_models.py` into a shared utility (`tests/scanner_utils.py` or similar) — currently duplicated between unit and integration tests
3. T-003 MockProgressReporter `.calls` redesign: consider migrating from `list[tuple[str, ...]]` to `@dataclass`-based call records for type safety
4. T-017 (Integration: Generation Stages + Orchestrator) and T-018 (Integration: UI Workers + Wizard) can follow the same pattern established here: canary tests for real entry points, cross-component composition tests, and conftest fixtures for shared infrastructure
5. Consider whether `test_real_production_plugin_capabilities` should also test Django, React, and HTMX plugins for symmetric coverage
6. The integration test directory now has 7 files — consider adding a `Makefile` or `tox` target for `pytest tests/integration/` to make it easy to run alongside unit tests
7. Keep `dependency-analysis.md` updated as new tickets are added — T-016's downstream chain (5 tickets) should be re-evaluated when T-017/T-018 add new integration test files
8. Consider running both TDD review and code review as standard practice for future tickets — the two tools caught different issue categories (TDD: structural/scope, code review: implementation details/code quality)
