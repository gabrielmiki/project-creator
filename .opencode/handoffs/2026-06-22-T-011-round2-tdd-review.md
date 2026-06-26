# Agent Outputs

## TDD Reviewer — Round 2: T-011 HTMX Plugin

**Date**: 2026-06-22  
**Reviewer**: TDD Reviewer Agent  
**Ticket**: T-011 — HTMX Plugin (`docs/context/tickets/011-plugin-htmx.md`)  
**Round**: 2 (Post-fix verification)

---

### Structured Review

```json
{
  "verdict": "READY",
  "blocking_issues": [],
  "phase_1_prior_issue_verification": [
    {
      "id": "BLOCKING-1",
      "description": "dependencies(self, spec) signature — does API spec now show `spec` param?",
      "resolved": true,
      "evidence": "Line 52-53: `def dependencies(self, spec: ProjectSpec) -> list[str]:` — `spec` parameter is present and typed."
    },
    {
      "id": "BLOCKING-2",
      "description": "Expanded ACs — are there ~18 ACs covering all mixins, error cases, and edge cases?",
      "resolved": true,
      "evidence": "18 ACs present (AC-01 through AC-18). Count verified: Discovery (1), FileProvider (2a, 2b), Configurable (3), Content — HTMX (4), Alpine.js (5, 6), Tailwind (7, 8), Bootstrap (9, 10), Directories (11), Dependencies (12), CommandRunner (13), Empty config (14), Missing key (15), Invalid value (16), Identity (17), Module (18). Covers all 4 mixins + error/edge cases."
    },
    {
      "id": "BLOCKING-3",
      "description": "jinja2 contradiction — resolved? No requirements.txt in files()?",
      "resolved": true,
      "evidence": "Design Note 7 (line 70): 'All file templates are inline module-level string constants. No Jinja2 dependency is needed.' Design Note 12 (line 80): 'No requirements.txt in files(): The backend plugin (FastAPI/Django) owns requirements.txt.' Directly addressed and resolved."
    },
    {
      "id": "BLOCKING-4",
      "description": "generate() behavior defined — is no-op documented? AC-13 present?",
      "resolved": true,
      "evidence": "Design Note 8 (line 72-73): 'generate() is no-op: HTMX has no scaffold command. CDN script tags in base.html are the delivery mechanism.' Design Note 9 (line 74): 'dependencies() always returns [].' AC-13 (line 153): explicit no-op test with mock executor."
    },
    {
      "id": "BLOCKING-5",
      "description": "Design notes — 12 present covering established patterns?",
      "resolved": true,
      "evidence": "12 numbered Design Notes at lines 56-80, covering: config access via `_config(spec)` helper, ValidationEngine ownership, entry point registration, AC-4 scanner compliance, test-first AC-16 construction, cross-method consistency, inline templates, generate() no-op, dependencies() invariants, Question.default values, include_tailwind vs css_framework, no requirements.txt."
    },
    {
      "id": "BLOCKING-6",
      "description": "AC-1 tests plugin.name, not PluginRegistry?",
      "resolved": true,
      "evidence": "AC-01 (line 109): 'Given the HtmxPlugin class, when instantiated, then plugin.name returns \"htmx\".' Tests class attribute directly, not PluginRegistry. Matches T-008/T-009/T-010 pattern."
    },
    {
      "id": "MODERATE-1",
      "description": "Content assertions specify exact CDN URLs?",
      "resolved": true,
      "evidence": "Lines 96-103 provide a dedicated 'Expected CDN URLs for Content Assertions' table with exact URLs for all four libraries (HTMX, Alpine.js, Tailwind, Bootstrap). ACs 04-09 reference the specific version strings (e.g., 'htmx.org@2.0.4', 'alpinejs@3.14.8', 'cdn.tailwindcss.com', 'bootstrap@5.3.3')."
    },
    {
      "id": "MODERATE-2",
      "description": "Content assertions for tailwind.config.js?",
      "resolved": true,
      "evidence": "AC-07 (line 133-134): 'The tailwind.config.js content includes \"./templates/**/*.html\" as a content path.'"
    },
    {
      "id": "MODERATE-3",
      "description": "Negative cases for all config flags?",
      "resolved": true,
      "evidence": "AC-06 (include_alpine=False or absent), AC-08 (include_tailwind=False or absent), AC-10 (css_framework='none'). All three config flags have negative cases."
    },
    {
      "id": "MODERATE-4",
      "description": "Bootstrap and 'none' CSS framework ACs present?",
      "resolved": true,
      "evidence": "AC-09 (line 139): css_framework='bootstrap' with include_tailwind=False → Bootstrap CDN link. AC-10 (line 141): css_framework='none' with include_tailwind=False → no CSS framework CDN."
    }
  ],
  "ac_validation": [
    {
      "criterion": "AC-01",
      "text": "Given the HtmxPlugin class, when instantiated, then plugin.name returns 'htmx'.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-02a",
      "text": "Given a ProjectSpec with frontend_id='htmx' and default config ({\"htmx\": {}}), when files() is called, then the returned list includes GeneratedFile entries for templates/base.html, templates/index.html, and static/css/style.css. All entries have Path objects as their .path attribute.",
      "testable": true,
      "issues": [
        "AC references GeneratedFile.path as Path — confirmed matching domain model (project_spec.py:217-219).",
        "The test must construct a spec with frontend_id='htmx'. The _make_react_spec pattern in test_plugin_react.py provides the template."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-02b",
      "text": "Given a ProjectSpec with frontend_id='htmx', when the generation pipeline is simulated (call files() → txn.stage_file(), directories() → txn.stage_directory(), dependencies() → txn.requirements.extend()), then core file paths are staged and txn.requirements remains empty (no dependencies).",
      "testable": true,
      "issues": [
        "Minor wording: 'txn.requirements.extend()' is descriptive, not API-exact. The existing _MockTransaction pattern uses `txn.requirements.append(dep)`. This is a documentation style choice, not a testability issue."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-03",
      "text": "Given the Configurable mixin, when questions() is called, then it returns Question objects whose .key attributes include 'include_alpine', 'include_tailwind', and 'css_framework'. include_alpine and include_tailwind must be QuestionType.BOOLEAN. css_framework must be QuestionType.CHOICE with options exactly equal to ['tailwind', 'bootstrap', 'none']. All keys must be unique.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-04",
      "text": "Given a ProjectSpec with frontend_id='htmx' and any config, when files() is called, then templates/base.html content includes htmx.org@2.0.4 in a <script> tag.",
      "testable": true,
      "issues": [
        "The 'any config' qualifier is acceptable here because HTMX CDN is unconditional. The test should verify with at minimum two configs: empty and full, but 'any config' means the assertion holds for all permutations. This is testable via parametrization."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-05",
      "text": "Given include_alpine=True in config, when files() is called, then templates/base.html content includes alpinejs@3.14.8 in a <script> tag.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-06",
      "text": "Given include_alpine=False (or absent from config), when files() is called, then templates/base.html content does NOT include alpinejs.",
      "testable": true,
      "issues": [
        "Tests both False and absent — should be a parametrized test. Follows T-009 AC-8 pattern."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-07",
      "text": "Given include_tailwind=True in config, when files() is called, then tailwind.config.js and postcss.config.js are in the returned file paths. The tailwind.config.js content includes './templates/**/*.html' as a content path. templates/base.html content includes cdn.tailwindcss.com in a <script> tag.",
      "testable": true,
      "issues": [
        "Multiple assertions bundled into one AC. This is acceptable — the test class can decompose into multiple test methods."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-08",
      "text": "Given include_tailwind=False (or absent from config), when files() is called, then tailwind.config.js is NOT in the returned file paths.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-09",
      "text": "Given css_framework='bootstrap' in config and include_tailwind=False, when files() is called, then templates/base.html content includes bootstrap@5.3.3 in a <link> tag.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-10",
      "text": "Given css_framework='none' in config and include_tailwind=False, when files() is called, then templates/base.html content does NOT include tailwindcss, bootstrap, or cdn.jsdelivr.net in a CSS framework context.",
      "testable": true,
      "issues": [
        "The phrase 'CSS framework context' is slightly ambiguous. A concrete assertion against known CDN URLs/strings would be clearer. The test should check that none of the CDN URLs from the CDN table (bootstrap@5.3.3, cdn.tailwindcss.com, cdn.jsdelivr.net) appear in base.html content."
      ],
      "suggested_fix": "Change to: 'templates/base.html content does NOT contain any of the following strings: cdn.tailwindcss.com, bootstrap@5.3.3, cdn.jsdelivr.net'"
    },
    {
      "criterion": "AC-11",
      "text": "Given the HTMX plugin, when directories() is called, then the returned list contains 'templates/', 'static/css/', and 'static/js/'.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-12",
      "text": "Given any config permutation (default, Alpine-only, Tailwind, Bootstrap, or combined), when dependencies() is called, then the returned list is empty ([]).",
      "testable": true,
      "issues": [
        "'any config permutation' is well-scoped — the subsequent parenthetical lists the specific permutations. This should be a parametrized test across at least 5+ permutations."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-13",
      "text": "Given any config permutation, when generate() is called with a mock executor, then executor.run() is NOT called.",
      "testable": true,
      "issues": [
        "Testable via `executor.run.assert_not_called()`. Follows T-010 AC-14f pattern (webpack no-op case)."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-14",
      "text": "Given config={'htmx': {}} (empty config dict — plugin uses internal defaults), when files(), directories(), and dependencies() are called, then defaults are used: include_alpine defaults to False, include_tailwind defaults to False, css_framework defaults to 'none'. No exception is raised.",
      "testable": true,
      "issues": [
        "The 'defaults are used' clause needs to be mapped to observable behavior: include_alpine=False → no Alpine CDN in base.html, include_tailwind=False → no tailwind config files, css_framework='none' → no CSS CDN. The AC could be more explicit about which specific assertions verify each default. Non-blocking — test developer can infer from other ACs."
      ],
      "suggested_fix": "Minor: Clarify that defaults are verified through observable output: 'No exception is raised. files() output matches AC-06, AC-08, and AC-10 expectations simultaneously.'"
    },
    {
      "criterion": "AC-15",
      "text": "Given config={} (no 'htmx' key in ProjectSpec.config), when files(), directories(), and dependencies() are called, then no exception is raised and default values are used (the plugin accesses config via spec.config.get('htmx', {})).",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-16",
      "text": "Given an invalid css_framework value (e.g., 'invalid') in plugin config, when ValidationEngine.validate_plugin_config() is called with the plugin's questions (constructed inline per Design Note 5), then a ValidationError with severity 'error' is returned.",
      "testable": true,
      "issues": [
        "AC says 'a ValidationError is returned' (singular). The existing test_choice_invalid_option pattern checks `len(errors) >= 1` — any number of errors ≥ 1 is acceptable. The AC language should match the 'at least one' pattern for consistency.",
        "Test must construct Question objects inline per Design Note 5 (same pattern as T-010 AC-17)."
      ],
      "suggested_fix": null
    },
    {
      "criterion": "AC-17",
      "text": "Given the HtmxPlugin class, when instantiated, then display_name returns 'HTMX' and description returns a non-empty string.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-18",
      "text": "Given the forge.plugins.htmx package, when imported, then HtmxPlugin is importable from forge.plugins.htmx.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    }
  ],
  "infrastructure_readiness": [
    {
      "requirement": "PluginBase + 4 mixins (Configurable, FileProvider, CommandRunner, DependencyProvider)",
      "status": "EXISTS",
      "location": "src/forge/plugins/base.py",
      "notes": "All mixins exist with correct abstract method signatures matching the API Spec. PluginBase defines name/display_name/description. Configurable: questions(). FileProvider: files(), directories(). CommandRunner: generate(). DependencyProvider: dependencies()."
    },
    {
      "requirement": "dependencies(self, spec) signature with spec parameter",
      "status": "EXISTS",
      "location": "src/forge/plugins/base.py:133",
      "notes": "Abstract method `def dependencies(self, spec: ProjectSpec) -> list[str]: ...` exists and the API Spec correctly matches this signature."
    },
    {
      "requirement": "Entry point registration in pyproject.toml",
      "status": "EXISTS",
      "location": "pyproject.toml:18",
      "notes": "Entry point `htmx = \"forge.plugins.htmx:HtmxPlugin\"` is already registered."
    },
    {
      "requirement": "AC-4 scanner (no forbidden infra import, domain import required)",
      "status": "EXISTS",
      "location": "tests/unit/test_plugin_base.py:187-216",
      "notes": "AST scanner checks for forbidden imports (forge.ui, forge.generation, forge.infrastructure) and requires forge.domain import. INFRA_EXEMPT_FILES={'base.py'} properly excludes base.py. Design Note 5 (line 64) correctly documents both constraints. The untyped `executor` parameter approach avoids the infra import ban."
    },
    {
      "requirement": "ValidationEngine.validate_plugin_config() CHOICE validation",
      "status": "EXISTS",
      "location": "src/forge/generation/validation.py:148-157",
      "notes": "CHOICE validation correctly rejects values not in question.options. Returns ValidationError with severity='error'."
    },
    {
      "requirement": "test_choice_invalid_option pattern for test-first AC-16",
      "status": "EXISTS",
      "location": "tests/unit/test_validation.py:226-240",
      "notes": "Pattern constructs Question objects inline, calls engine.validate_plugin_config(), asserts errors exist with matching field. Design Note 5 (line 66-67) correctly references this pattern."
    },
    {
      "requirement": "MockTransaction duck-type pattern",
      "status": "EXISTS",
      "location": "tests/unit/test_plugin_react.py:14-28 (and test_plugin_fastapi.py, test_plugin_django.py)",
      "notes": "Identical _MockTransaction class exists in all three existing plugin tests. Provides stage_file, stage_directory, and requirements list. Confirmed usable as-is for HTMX tests."
    },
    {
      "requirement": "MagicMock pattern for executor mock",
      "status": "EXISTS",
      "location": "tests/unit/test_plugin_react.py (AC-14f), test_plugin_fastapi.py (AC-7), test_plugin_django.py (AC-13)",
      "notes": "Standard `executor: MagicMock = MagicMock()` pattern used across all plugin tests. AC-13 design matches T-010 AC-14f (assert_not_called)."
    },
    {
      "requirement": "TemplateDefinition.frontend_id field",
      "status": "EXISTS",
      "location": "src/forge/domain/project_spec.py:24",
      "notes": "Field `frontend_id: str | None = None` exists and matches the architecture doc. ACs 02a/02b/04 correctly use `frontend_id='htmx'`."
    },
    {
      "requirement": "_make_htmx_spec helper pattern",
      "status": "MISSING",
      "location": "N/A — will be created in test file",
      "notes": "Follow existing pattern from test_plugin_react.py (lines 31-46). Will need _make_htmx_spec with frontend_id='htmx' and Domain import. This is expected — tests don't exist yet."
    },
    {
      "requirement": "conftest.py or shared fixtures for plugin tests",
      "status": "NOT_APPLICABLE",
      "location": "tests/fixtures/",
      "notes": "Existing plugins tests (fastapi, django, react) all use inline _MockTransaction and _make_*_spec helpers rather than shared fixtures. No conftest needed. This is the established convention."
    }
  ],
  "coverage_analysis": {
    "happy_path": "COVERED",
    "error_cases": "COVERED",
    "edge_cases": "PARTIALLY_COVERED",
    "plugin_isolation_tested": "YES (via AC-4 scanner compliance rules — Design Note 4)"
  },
  "new_issues": [
    {
      "severity": "MODERATE",
      "type": "missing_ac",
      "description": "CHOICE option 'tailwind' for css_framework has no AC coverage",
      "details": "AC-03 specifies css_framework options as [\"tailwind\", \"bootstrap\", \"none\"]. AC-09 covers css_framework='bootstrap'. AC-10 covers css_framework='none'. But css_framework='tailwind' (with include_tailwind=False) has zero AC coverage — no AC validates what templates/base.html looks like in this case. The cross-method consistency map (lines 82-94) also omits this case. A developer could skip implementing css_framework='tailwind' handling and all tests would pass.",
      "suggested_fix": "Add an AC (e.g., AC-09b) that mirrors AC-09 but for 'tailwind': 'Given css_framework=\"tailwind\" in config and include_tailwind=False, when files() is called, then templates/base.html content includes cdn.tailwindcss.com in a <script> tag.' Also add the row to the cross-method consistency map."
    },
    {
      "severity": "MODERATE",
      "type": "missing_ac",
      "description": "include_tailwind=True + css_framework='bootstrap' combination not explicitly AC'd",
      "details": "The cross-method consistency map (line 91) documents this case: 'Tailwind build files + Bootstrap CDN in base.html'. But no AC explicitly tests this combined scenario. AC-07 tests include_tailwind=True generically but without specifying css_framework. AC-09 tests css_framework='bootstrap' but constraints include_tailwind=False. The combination case falls through the cracks.",
      "suggested_fix": "Add a note to AC-07 or AC-09 that the combination test is expected as a parametrized variant, or add an explicit AC. For example, a note: 'Test parameterization should also verify include_tailwind=True + css_framework=\"bootstrap\" produces both tailwind.config.js and Bootstrap CDN in base.html.'"
    },
    {
      "severity": "LOW",
      "type": "clarity",
      "description": "AC-10 'CSS framework context' is ambiguous",
      "details": "The phrase 'does NOT include tailwindcss, bootstrap, or cdn.jsdelivr.net in a CSS framework context' could be misinterpreted. The exact exclusion strings should match the CDN URL table. For safety, test against the known CDN URLs: cdn.tailwindcss.com, bootstrap@5.3.3, and cdn.jsdelivr.net.",
      "suggested_fix": "See ac_validation entry for AC-10 — rephrase to reference specific URL strings."
    },
    {
      "severity": "LOW",
      "type": "consistency",
      "description": "AC-16 says 'a ValidationError is returned' — singular phrasing",
      "details": "The AC says 'a ValidationError' (singular) while the existing test_choice_invalid_option pattern checks `len(errors) >= 1`. Minor phrasing difference, not a testability issue.",
      "suggested_fix": "Unnecessary to fix — tests will follow the established pattern regardless."
    },
    {
      "severity": "INFO",
      "type": "documentation",
      "description": "Potential double CDN link when include_tailwind=True and css_framework='tailwind'",
      "details": "If a user sets both include_tailwind=True and css_framework='tailwind', the Tailwind CDN link (cdn.tailwindcss.com) might appear twice in base.html — once from the include_tailwind=True path and once from the css_framework='tailwind' path. The design notes and consistency map don't address deduplication.",
      "suggested_fix": "Add a Design Note clarifying whether CDN links should be deduplicated, or document that the css_framework setting is ignored when include_tailwind=True (since build tooling implies runtime CDN)."
    },
    {
      "severity": "INFO",
      "type": "consistency",
      "description": "Cross-method consistency map missing css_framework='tailwind' row",
      "details": "The consistency map (lines 82-94) has rows for css_framework='bootstrap' and css_framework='none' but not for css_framework='tailwind'. This is an omission since it's a valid CHOICE option.",
      "suggested_fix": "Add a row: 'css_framework=\"tailwind\" (without tailwind) | base.html includes Tailwind CDN link | [] | no-op'"
    }
  ],
  "files_to_create": [
    "tests/unit/test_plugin_htmx.py (from template of test_plugin_react.py)",
    "src/forge/plugins/htmx/__init__.py (domain import + re-export)",
    "src/forge/plugins/htmx/plugin.py (HtmxPlugin class)"
  ],
  "infrastructure_gaps": [],
  "recommendations": [
    "Use test_plugin_react.py as the structural template — the AC numbering and pattern are nearly identical.",
    "Create _make_htmx_spec helper with frontend_id='htmx', following _make_react_spec pattern.",
    "Use parametrized tests for AC-12 and AC-13 to cover all config permutations.",
    "For AC-14, decompose into multiple test methods following AC-06/AC-08/AC-10 patterns.",
    "Implement the two suggested ACs for css_framework='tailwind' and the combination case as part of the test suite even if not in the ticket (defensive test coverage)."
  ]
}
```

---

### Summary

**Verdict**: READY

All 6 blocking issues and 4 moderate issues from Round 1 are verified as resolved. The ticket is well-structured with 18 ACs covering all 4 mixins, proper Given/When/Then format, concrete values (exact CDN URLs), and proper error/edge cases.

**Remaining issues** (non-blocking):

| Severity | Count | Description |
|----------|-------|-------------|
| MODERATE | 2 | Missing AC for `css_framework="tailwind"` CHOICE option; missing AC for `include_tailwind=True + css_framework="bootstrap"` combination |
| LOW | 2 | Ambiguous phrasing in AC-10; minor AC-16 singular wording |
| INFO | 2 | CDN deduplication edge case; missing row in consistency map |

The moderate issues are not blocking because:
1. The test developer can add defensive test coverage for the missing CHOICE option (a responsible practice).
2. The combination case can be tested via parametrized variants of AC-07 and AC-09.

The infrastructure is fully ready: PluginBase + 4 mixins with correct signatures, entry point registered, AC-4 scanner in place, ValidationEngine with CHOICE validation, MockTransaction and MagicMock patterns established across three prior plugin test files.
