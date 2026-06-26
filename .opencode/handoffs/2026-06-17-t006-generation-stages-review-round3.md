# Agent Output: T-006 Generation Stages — TDD Review (Round 3)

## Session Context
- **Ticket**: T-006 — Generation Stages (All 6)
- **Review Round**: 3 (final after Round 2 fixes)
- **Reviewed by**: TDD Reviewer Agent
- **Date**: 2026-06-17

## Round 2 Fix Verification

| Fix | Status | Evidence |
|-----|--------|----------|
| B-1: AC-1 changed to "existing empty output_dir" | ✅ FIXED | AC-1 line 87 matches orchestrator-creates-first design |
| B-3: Architecture diagram orchestrator mkdir | ✅ FIXED | Pipeline lines 233-236 show orchestrator mkdir before Stage 1 |
| B-2: AC-12 txn.requirements | ✅ FIXED | `txn.requirements` exists at transaction.py:13; AC-12 line 98 references it |
| Architecture.md Stage 5: CLAUDE.md path | ✅ FIXED | Line 256: `.claude/CLAUDE.md` |
| AC-7/AC-14 [integration] tags | ✅ FIXED | Both tagged |

## Structured Findings

```json
{
  "ac_validation": [
    {
      "criterion": "AC-1",
      "text": "Given a DirectoryInitializer and an existing empty output_dir, when run() is called, then no exception is raised.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-2",
      "text": "Given a DirectoryInitializer and existing non-empty output_dir, when run() is called, then DirectoryNotEmptyError is raised.",
      "testable": true,
      "issues": [
        "Contradiction with architecture.md: orchestrator also raises DirectoryNotEmptyError (arch lines 235-236). If orchestrator raises first on non-empty, Stage 1 never receives non-empty input, making this AC unreachable in integration.",
        "See blocking issue B-1 below."
      ],
      "suggested_fix": "Resolve whether orchestrator or Stage 1 is the enforcement point for DirectoryNotEmptyError (see blocking issue)."
    },
    {
      "criterion": "AC-3",
      "text": "Given a SharedStructureScaffolder with a valid ProjectSpec and txn, when run() is called, then README.md, .gitignore, .env.example, .python-version exist in staging.",
      "testable": true,
      "issues": [
        "Coverage gap: Stage 2 spec (lines 46-53) also generates docs/index.md and docs/architecture.md stubs, but AC-3 only verifies 4 files. docs/ stubs are untested.",
        "Not a contradiction, but an incomplete AC — docs/ stubs could be silently missing."
      ],
      "suggested_fix": "Either add docs/ stubs to AC-3, or add a separate AC for docs/ stubs."
    },
    {
      "criterion": "AC-4",
      "text": "Given a PluginExecutionEngine with a plugin implementing FileProvider, when run() is called, then the plugin's files are staged via txn.stage_file().",
      "testable": true,
      "issues": [
        "Bridge contract implicit: FileProvider.files() returns list[GeneratedFile] where path is Path. txn.stage_file() takes relative_path: str. The conversion str(generated_file.path) is needed but not documented anywhere."
      ],
      "suggested_fix": "Consider documenting the Path→str conversion in the Stage 3 spec, or changing txn.stage_file() to accept Path."
    },
    {
      "criterion": "AC-5",
      "text": "Given a PluginExecutionEngine with a plugin implementing CommandRunner, when run() is called, then generate() is invoked with target_dir = output_dir.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-6",
      "text": "Given a PluginExecutionEngine with a requires dependency not in the selected set, when run() is called, then MissingDependencyError is raised listing the missing dependency.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-7",
      "text": "[integration] Given an empty project (no domains or plugins selected), when stages 1-6 run, then Stage 3 is skipped (no-op) and the shared structure is still generated.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-8",
      "text": "Given a JustfileGenerator with a valid ProjectSpec and txn, when run() is called, then justfile in staging contains setup, dev, test, lint, format, build commands.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-9",
      "text": "Given a ProjectDocumentationWriter with a valid ProjectSpec and txn, when run() is called, then AGENTS.md exists in staging and contains the project name.",
      "testable": true,
      "issues": [
        "Stage 5 spec (line 73) also generates .claude/CLAUDE.md, but AC-9 only checks AGENTS.md. .claude/CLAUDE.md is not covered by any AC."
      ],
      "suggested_fix": "Add assertion for .claude/CLAUDE.md to AC-9 or create AC-9b."
    },
    {
      "criterion": "AC-10",
      "text": "Given an AgentSkillScaffolder with a backend plugin selected, when run() is called, then .opencode/skills/ directory exists in staging.",
      "testable": true,
      "issues": [
        "Stage 6 spec (lines 76-78) also creates .opencode/agents/ and .opencode/handoffs/ stubs. Only .opencode/skills/ is covered by AC-10."
      ],
      "suggested_fix": "Add coverage for .opencode/agents/ and .opencode/handoffs/ stubs."
    },
    {
      "criterion": "AC-11",
      "text": "Given a PluginExecutionEngine with a plugin set containing a circular dependency, when run() is called, then CycleDependencyError propagates from topological_sort().",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-12",
      "text": "Given a PluginExecutionEngine with a plugin implementing DependencyProvider, when run() is called, then the plugin's dependencies are appended to txn.requirements.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-13",
      "text": "Given a PluginExecutionEngine that checks cancellation mid-execution, when progress.should_cancel() returns True, then execution stops early.",
      "testable": true,
      "issues": [
        "MockProgressReporter.should_cancel() always returns False (test_progress.py lines 64-66). To test AC-13, the implementer must subclass MockProgressReporter or monkeypatch the method.",
        "Standard test technique, but the ticket does not mention this requirement."
      ],
      "suggested_fix": "Document in the test plan that AC-13 requires a configured mock (e.g., CancellableMockProgressReporter that returns True from should_cancel())."
    },
    {
      "criterion": "AC-14",
      "text": "[integration] Given all 6 stages run successfully and txn.commit() is called, when generation completes, then all staged files exist in output_dir and .forge-staging is removed.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    }
  ],
  "infrastructure_readiness": [
    {
      "requirement": "GenerationTransaction fixture (output_dir + txn)",
      "status": "EXISTS",
      "location": "tests/unit/test_transaction.py (lines 8-19)",
      "notes": "output_dir fixture creates tmp subdir; txn fixture returns GenerationTransaction(output_dir). Reusable by stage tests."
    },
    {
      "requirement": "MockProgressReporter fixture",
      "status": "EXISTS",
      "location": "src/forge/generation/progress.py (lines 42-66)",
      "notes": "Available via `from forge.generation import MockProgressReporter`. should_cancel() always returns False — AC-13 needs customization."
    },
    {
      "requirement": "Plugin fixtures (FileOnlyPlugin, CommandOnlyPlugin, etc.)",
      "status": "EXISTS",
      "location": "tests/unit/conftest.py (lines 17-99)",
      "notes": "All mixin combinations have fixture instances. Some may need modification for AC-6 (requires dependency) and AC-11 (circular dependency)."
    },
    {
      "requirement": "PluginRegistry fixture (for topological_sort)",
      "status": "EXISTS",
      "location": "tests/unit/test_registry.py",
      "notes": "PluginRegistry is creatable with `PluginRegistry()`. discover() not needed for stage tests — use resolve_many() or inject directly."
    },
    {
      "requirement": "AC-8 infrastructure import — future stage files",
      "status": "INCOMPLETE",
      "location": "tests/unit/test_progress.py (lines 147-158)",
      "notes": "test_infrastructure_imports_allowed() scans ALL .py files recursively in generation/ via rglob. 8 new files (stages/__init__.py, base.py, 6 stage .py files) will each need 'from forge.infrastructure import ...' or this test fails. The ticket does not mention this requirement."
    },
    {
      "requirement": "Temporary directory for staging tests",
      "status": "EXISTS",
      "location": "pytest tmp_path fixture",
      "notes": "Standard tmp_path works for all stage-level tests. GenerationTransaction creates .forge-staging inside output_dir."
    },
    {
      "requirement": "DirectoryNotEmptyError / MissingDependencyError imports",
      "status": "EXISTS",
      "location": "src/forge/generation/errors.py (lines 1-9)",
      "notes": "Both exceptions are defined and exported via generation/__init__.py. Importable as `from forge.generation import DirectoryNotEmptyError`."
    }
  ],
  "coverage_analysis": {
    "happy_path": "COVERED",
    "error_cases": "COVERED",
    "edge_cases": "PARTIALLY COVERED",
    "notes": [
      "Happy path: AC-1 (empty dir), AC-3 (shared files), AC-8 (justfile), AC-9 (AGENTS.md), AC-10 (skills dir) — all covered.",
      "Error cases: AC-2 (non-empty dir), AC-6 (missing dependency), AC-11 (circular dependency) — all covered.",
      "Edge cases: AC-7 [integration] (no plugins selected), AC-14 [integration] (full pipeline) — covered. But AC-3 doesn't test docs/ stubs (edge case of partial Stage 2 output), AC-9 doesn't test .claude/CLAUDE.md, AC-10 doesn't test .opencode/agents/ or handoffs/. Several stage outputs have partial AC coverage.",
      "Stage 3 edge case: empty plugin list (skip/no-op) is covered by AC-7 [integration] but has no unit-level AC."
    ],
    "plugin_isolation_tested": "YES",
    "plugin_isolation_notes": "AC-8 test (test_progress.py) scans for forbidden ui imports. New stage files will be included in this scan. All generation/ files must avoid `forge.ui` imports."
  },
  "verdict": "NEEDS_REVISION",
  "blocking_issues": [
    "B-1: Orchestrator/Stage 1 DirectoryNotEmptyError double-raise contradiction (carry-over from Round 2). Architecture.md lines 235-236 say orchestrator 'raises DirectoryNotEmptyError if proceeding with a non-empty directory' AND lines 239-240 say Stage 1 also 'raises DirectoryNotEmptyError if non-empty'. If orchestrator raises on non-empty (when user says 'proceed'), Stage 1 never receives non-empty input — Stage 1's check is dead code. If Stage 1 is the enforcement gate, the orchestrator should not raise — it should only prompt and let Stage 1 determine the outcome. The Round 2 fix chose 'Option A — orchestrator creates, Stage 1 validates' but the architecture diagram was not cleaned up to remove orchestrator's raise. SEVERITY: blocking — affects the correctness of the contract between Stage 1 and the orchestrator, and determines whether AC-2 is reachable in integration."
  ],
  "moderate_issues": [
    "M-1: AC-8 infrastructure import requirement not communicated. Existing test test_infrastructure_imports_allowed() scans ALL .py files in generation/ recursively. 8 new files (stages/__init__.py, base.py, 6 stage .py files) must each contain `from forge.infrastructure import ...` or the pre-existing test suite will fail. This constraint is not mentioned anywhere in the ticket. SEVERITY: moderate — won't break stage ACs but will break pre-existing test when new files are created.",
    "M-2: AC-3 does not verify docs/ stubs (docs/index.md, docs/architecture.md). Stage 2 spec lists these as generated outputs but no AC checks them. SEVERITY: moderate — coverage gap allows silent breakage of docs/ generation.",
    "M-3: AC-9 does not verify .claude/CLAUDE.md, AC-10 does not verify .opencode/agents/ or .opencode/handoffs/. Stage 5 and Stage 6 specs list these outputs but ACs cover only a subset. SEVERITY: moderate — coverage gaps.",
    "M-4: AC-13 requires non-default mock configuration (should_cancel() returning True), but MockProgressReporter hardcodes False. Not mentioned in ticket. SEVERITY: moderate — needs documentation or a configurable mock."
  ],
  "low_issues": [
    "L-1: Architecture says Stage 1 'Validates output_dir via GenerationTransaction' (arch line 239) but GenerationTransaction has no validation methods and _output_dir is private. Stage 1 validates output_dir directly (receives it as a parameter). Minor doc imprecision.",
    "L-2: GeneratedFile.path (Path) to txn.stage_file(relative_path: str) bridge not documented. The str() conversion is implicit.",
    "L-3: Stage 1 prompt behavior (orchestrator asks user) is mentioned in Stage 1 spec but not covered by any AC. The ACs correctly focus on Stage 1's deterministic behavior, but the spec could mislead."
  ],
  "recommendations": [
    "RESOLVE B-1: Choose one enforcement point for DirectoryNotEmptyError. Option A (recommended): orchestrator only prompts, Stage 1 is the sole enforcement gate — update architecture diagram to remove orchestrator's 'raises DirectoryNotEmptyError' (line 235-236). Option B: orchestrator is the sole gate, Stage 1 validates other properties — update Stage 1 spec to remove 'raises DirectoryNotEmptyError' and update AC-2 accordingly.",
    "DOCUMENT M-1: Add a note to the ticket's 'Files to create' section: 'Each new .py file in generation/stages/ must include from forge.infrastructure import GenerationTransaction as _  # noqa: F401 to pass AC-8 test_infrastructure_imports_allowed().'",
    "FILL M-2/M-3 coverage gaps: Extend AC-3 to cover docs/ stubs. Extend AC-9 to cover .claude/CLAUDE.md. Extend AC-10 to cover .opencode/agents/ and .opencode/handoffs/. Or add new ACs for these.",
    "DOCUMENT M-4: Add guidance for AC-13 testing: 'MockProgressReporter must be configured to return True from should_cancel() — use a subclass or monkeypatch.'"
  ]
}
```

## Summary

**Verdict: NEEDS REVISION**

1 blocking issue remains (B-1: orchestrator/Stage 1 double-raise contradiction — carry-over from Round 2 that was not fully resolved), plus 4 moderate issues (M-1: undocumented AC-8 infrastructure import requirement that will cause pre-existing test failures; M-2/M-3: AC coverage gaps for docs/, .claude/, .opencode/ outputs; M-4: AC-13 test pattern not documented).

Once B-1 is resolved (choose single enforcement point and update both architecture.md and ticket accordingly) and M-1 is documented, the ticket should be re-reviewed for final APPROVAL.
