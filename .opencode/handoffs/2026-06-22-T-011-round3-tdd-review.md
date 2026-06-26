# Agent Outputs

## TDD Reviewer — Round 3: T-011 HTMX Plugin (Final)

**Date**: 2026-06-22
**Reviewer**: TDD Reviewer Agent
**Ticket**: T-011 — HTMX Plugin (`docs/context/tickets/011-plugin-htmx.md`)
**Round**: 3 (Final validation — all prior issues resolved, fresh AC assessment)

---

### Structured Review

```json
{
  "verdict": "CHANGES_REQUESTED",
  "blocking_issues": [],
  "phase_1_round2_issue_verification": [
    {
      "id": "N-1",
      "severity_original": "MODERATE",
      "description": "AC for css_framework='tailwind' (with include_tailwind=False) missing",
      "resolved": true,
      "evidence": "AC-09 (line 139-140): 'Given css_framework=\"tailwind\" in config and include_tailwind=False, when files() is called, then templates/base.html content includes cdn.tailwindcss.com in a <script> tag.' Explicitly added."
    },
    {
      "id": "N-2",
      "severity_original": "MODERATE",
      "description": "Combined AC for include_tailwind=True + css_framework='bootstrap' missing",
      "resolved": true,
      "evidence": "AC-12 (line 149): 'Given include_tailwind=True and css_framework=\"bootstrap\" in config, when files() is called, then templates/base.html content includes both cdn.tailwindcss.com <script> and bootstrap@5.3.3 <link> CDN tags; tailwind.config.js and postcss.config.js are in the returned file paths.' Explicitly added."
    },
    {
      "id": "N-3",
      "severity_original": "LOW",
      "description": "AC-10 (now AC-11) ambiguous 'CSS framework context' — not referencing exact CDN URLs",
      "resolved": true,
      "evidence": "AC-11 (line 145): 'templates/base.html content does NOT include cdn.tailwindcss.com, cdn.jsdelivr.net/npm/bootstrap, or any CSS framework CDN URL.' Now references specific CDN URL strings."
    },
    {
      "id": "N-4",
      "severity_original": "LOW",
      "description": "AC-16 (now AC-18) says 'a ValidationError' — singular, not matching >=1 pattern",
      "resolved": true,
      "evidence": "AC-18 (line 169): 'then at least one ValidationError with severity \"error\" is returned (i.e., len(errors) >= 1).' Explicit parenthetical matching the established test pattern."
    },
    {
      "id": "N-5",
      "severity_original": "INFO",
      "description": "Cross-method consistency map missing css_framework='tailwind' row",
      "resolved": true,
      "evidence": "Consistency map (line 89): Row present for 'css_framework=\"tailwind\" (without tailwind build tooling) | base.html includes Tailwind CDN script (CDN-only, no config files) | [] | no-op'."
    },
    {
      "id": "N-6",
      "severity_original": "INFO",
      "description": "DN 11 does not address CDN duplication guard for include_tailwinbd=True + css_framework='tailwind'",
      "resolved": true,
      "evidence": "DN 11 (lines 78-79): 'When both include_tailwind=True and css_framework=\"tailwind\" are set, the Tailwind CDN script must appear in base.html exactly once — the implementation must guard against duplicate CDN entries.' Explicit duplication guard guidance added."
    }
  ],
  "phase_2_ac_validation": [
    {
      "criterion": "AC-01",
      "text": "Given the HtmxPlugin class, when instantiated, then plugin.name returns 'htmx'.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 AC-01",
      "test_method_suggestions": [
        "test_name_returns_htmx — simple assert plugin.name == 'htmx'"
      ]
    },
    {
      "criterion": "AC-02a",
      "text": "Given a ProjectSpec with frontend_id='htmx' and default config ({\"htmx\": {}}), when files() is called, then the returned list includes GeneratedFile entries for templates/base.html, templates/index.html, and static/css/style.css. All entries have Path objects as their .path attribute.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 AC-02a",
      "test_method_suggestions": [
        "test_files_core_paths_present — assert set of path strings includes expected paths",
        "test_files_returns_generated_file_list — assert isinstance list and all GeneratedFile",
        "test_file_paths_are_path_objects — assert all isinstance(f.path, Path)"
      ]
    },
    {
      "criterion": "AC-02b",
      "text": "Given a ProjectSpec with frontend_id='htmx', when the generation pipeline is simulated (call files() → txn.stage_file(), directories() → txn.stage_directory(), dependencies() → txn.requirements.extend()), then core file paths are staged and txn.requirements remains empty (no dependencies).",
      "testable": true,
      "issues": [
        "'txn.requirements.extend()' is descriptive language, not API-exact. The established _MockTransaction pattern uses txn.requirements.append(dep). This is a documentation style choice, not a testability blocker."
      ],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 AC-02b",
      "test_method_suggestions": [
        "test_engine_stages_core_files_and_deps — iterate files/dirs/deps through MockTransaction, assert staged paths present and requirements empty",
        "test_engine_empty_config_no_error — same with empty config, assert no exception"
      ]
    },
    {
      "criterion": "AC-03",
      "text": "Given the Configurable mixin, when questions() is called, then it returns Question objects whose .key attributes include 'include_alpine', 'include_tailwind', and 'css_framework'. include_alpine and include_tailwind must be QuestionType.BOOLEAN. css_framework must be QuestionType.CHOICE with options exactly equal to ['tailwind', 'bootstrap', 'none']. All keys must be unique.",
      "testable": true,
      "issues": [
        "Requires exact order match on options list: ['tailwind', 'bootstrap', 'none']. This is testable but the implementation must match the specified order."
      ],
      "suggested_fix": "Clarify that the options list must contain exactly these three values (order is a convention, not a contract) or keep as-is (order is contract).",
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 AC-03 with CHOICE option",
      "test_method_suggestions": [
        "test_questions_keys_include_all_three — assert 'include_alpine', 'include_tailwind', 'css_framework' in keys",
        "test_boolean_questions_are_boolean — assert include_alpine and include_tailwind are BOOLEAN",
        "test_css_framework_is_choice_with_options — assert CHOICE type and options == ['tailwind', 'bootstrap', 'none']",
        "test_question_keys_are_unique — assert len(keys) == len(set(keys))"
      ]
    },
    {
      "criterion": "AC-04",
      "text": "Given a ProjectSpec with frontend_id='htmx' and any config, when files() is called, then templates/base.html content includes htmx.org@2.0.4 in a <script> tag.",
      "testable": true,
      "issues": [
        "'any config' is acceptable — HTMX CDN is unconditional. Should be tested with at minimum 2 configs (default + one variant) via parametrization."
      ],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — unconditional content assertion (see T-004 pattern)",
      "test_method_suggestions": [
        "test_base_html_includes_htmx_cdn — parametrized over ['empty', 'with_alpine', 'with_tailwind'] to verify unconditional presence"
      ]
    },
    {
      "criterion": "AC-05",
      "text": "Given include_alpine=True in config, when files() is called, then templates/base.html content includes alpinejs@3.14.8 in a <script> tag.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — config-dependent content assertion (see T-008 AC-4)",
      "test_method_suggestions": [
        "test_alpine_true_includes_cdn — assert 'alpinejs@3.14.8' in base.html content"
      ]
    },
    {
      "criterion": "AC-06",
      "text": "Given include_alpine=False (or absent from config), when files() is called, then templates/base.html content does NOT include alpinejs.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-009 AC-8 / T-010 AC-07 (parametrized False + absent)",
      "test_method_suggestions": [
        "test_alpine_false_or_absent_excludes_cdn — parametrized over [{'include_alpine': False}, {}]"
      ]
    },
    {
      "criterion": "AC-07",
      "text": "Given include_tailwind=True in config, when files() is called, then tailwind.config.js and postcss.config.js are in the returned file paths. The tailwind.config.js content includes './templates/**/*.html' as a content path. templates/base.html content includes cdn.tailwindcss.com in a <script> tag.",
      "testable": true,
      "issues": [
        "Multiple bundled assertions (3 distinct behavioral requirements). Decomposable into separate test methods within one test class."
      ],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-010 AC-06 (multiple assertions in one AC, decomposed via class methods)",
      "test_method_suggestions": [
        "test_tailwind_true_includes_config_files — assert tailwind.config.js and postcss.config.js in paths",
        "test_tailwind_true_content_paths — assert './templates/**/*.html' in tailwind.config.js content",
        "test_tailwind_true_base_html_includes_tailwind_cdn — assert 'cdn.tailwindcss.com' in base.html content"
      ]
    },
    {
      "criterion": "AC-08",
      "text": "Given include_tailwind=False (or absent from config), when files() is called, then tailwind.config.js is NOT in the returned file paths.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-010 AC-07 (parametrized False + absent)",
      "test_method_suggestions": [
        "test_tailwind_false_or_absent_excludes_config — parametrized over [{'include_tailwind': False}, {}]"
      ]
    },
    {
      "criterion": "AC-09",
      "text": "Given css_framework='tailwind' in config and include_tailwind=False, when files() is called, then templates/base.html content includes cdn.tailwindcss.com in a <script> tag. tailwind.config.js and postcss.config.js are NOT in the returned file paths (build tooling is controlled by include_tailwind, not css_framework).",
      "testable": true,
      "issues": [
        "This AC (css_framework='tailwind' without build tooling) was added in Round 2 to resolve N-1. It correctly asserts CDN presence AND build file absence — two orthogonal dimensions."
      ],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — mirrors AC-10 (bootstrap) and AC-11 (none) structure",
      "test_method_suggestions": [
        "test_css_framework_tailwind_includes_cdn — assert 'cdn.tailwindcss.com' in base.html",
        "test_css_framework_tailwind_no_build_files — assert tailwind.config.js NOT in paths"
      ]
    },
    {
      "criterion": "AC-10",
      "text": "Given css_framework='bootstrap' in config and include_tailwind=False, when files() is called, then templates/base.html content includes bootstrap@5.3.3 in a <link> tag.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — CDN content assertion",
      "test_method_suggestions": [
        "test_css_framework_bootstrap_includes_cdn — assert 'bootstrap@5.3.3' in base.html content"
      ]
    },
    {
      "criterion": "AC-11",
      "text": "Given css_framework='none' in config and include_tailwind=False, when files() is called, then templates/base.html content does NOT include cdn.tailwindcss.com, cdn.jsdelivr.net/npm/bootstrap, or any CSS framework CDN URL.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — negative CDN content assertion (resolved N-3)",
      "test_method_suggestions": [
        "test_css_framework_none_no_cdn — assert all(CDN_URL not in content for known CDN URLs). Use the CDN URL table for the exact list."
      ]
    },
    {
      "criterion": "AC-12",
      "text": "Given include_tailwind=True and css_framework='bootstrap' in config, when files() is called, then templates/base.html content includes both cdn.tailwindcss.com <script> and bootstrap@5.3.3 <link> CDN tags; tailwind.config.js and postcss.config.js are in the returned file paths.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — combined config AC (added to resolve N-2)",
      "test_method_suggestions": [
        "test_combined_tailwind_bootstrap_has_both_cdns — assert both CDN URLs in base.html content",
        "test_combined_tailwind_bootstrap_has_build_files — assert tailwind.config.js and postcss.config.js in paths"
      ]
    },
    {
      "criterion": "AC-13",
      "text": "Given the HTMX plugin, when directories() is called, then the returned list contains 'templates/', 'static/css/', and 'static/js/'.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 directories AC",
      "test_method_suggestions": [
        "test_directories_returns_expected_dirs — assert all expected dirs in plugin.directories(spec)"
      ]
    },
    {
      "criterion": "AC-14",
      "text": "Given any config permutation (default, Alpine-only, Tailwind, Bootstrap, or combined), when dependencies() is called, then the returned list is empty ([]).",
      "testable": true,
      "issues": [
        "'any config permutation' is scoped by the parenthetical examples (5 specific permutations). Testable via parametrization."
      ],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — invariant dependency AC, parametrized pattern",
      "test_method_suggestions": [
        "test_dependencies_empty_for_all_configs — parametrized over 5+ config dicts, assert each returns []"
      ]
    },
    {
      "criterion": "AC-15",
      "text": "Given any config permutation, when generate() is called with a mock executor, then executor.run() is NOT called.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-010 AC-14f (webpack no-op pattern): executor.run.assert_not_called()",
      "test_method_suggestions": [
        "test_generate_noop_for_all_configs — parametrized, MagicMock executor, assert_not_called()"
      ]
    },
    {
      "criterion": "AC-16",
      "text": "Given config={'htmx': {}} (empty config dict — plugin uses internal defaults), when files(), directories(), and dependencies() are called, then defaults are used: include_alpine defaults to False, include_tailwind defaults to False, css_framework defaults to 'none'. No exception is raised.",
      "testable": true,
      "issues": [
        "The 'defaults are used' clause requires mapping defaults to observable behavior: include_alpine=False → AC-06 expectations, include_tailwind=False → AC-08 expectations, css_framework='none' → AC-11 expectations. The AC could cross-reference these for clarity."
      ],
      "suggested_fix": "Minor: Clarify that defaults are verified through observable output: 'No exception is raised. files() output matches AC-06 (no Alpine CDN), AC-08 (no tailwind config files), and AC-11 (no CDN framework CDNs) expectations simultaneously.'",
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 empty config ACs",
      "test_method_suggestions": [
        "test_empty_config_no_exception — call all three methods",
        "test_empty_config_defaults_no_alpine — assert no Alpine CDN",
        "test_empty_config_defaults_no_tailwind — assert no tailwind config",
        "test_empty_config_defaults_css_none — assert no CSS framework CDN"
      ]
    },
    {
      "criterion": "AC-17",
      "text": "Given config={} (no 'htmx' key in ProjectSpec.config), when files(), directories(), and dependencies() are called, then no exception is raised and default values are used (the plugin accesses config via spec.config.get('htmx', {})).",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 missing key ACs",
      "test_method_suggestions": [
        "test_missing_htmx_key_uses_defaults — same assertions as AC-16 but with empty outer config",
        "test_missing_htmx_key_does_not_raise — call all three methods safely"
      ]
    },
    {
      "criterion": "AC-18",
      "text": "Given an invalid css_framework value (e.g., 'invalid') in plugin config, when ValidationEngine.validate_plugin_config() is called with the plugin's questions (constructed inline per Design Note 5), then at least one ValidationError with severity 'error' is returned (i.e., len(errors) >= 1).",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — test_validation.py:test_choice_invalid_option pattern (line 226-240). Design Note 5 correctly references the inline construction approach.",
      "test_method_suggestions": [
        "test_invalid_css_framework_validation_error — construct Question inline, call engine.validate_plugin_config(), assert len(errors) >= 1 and field == 'css_framework'"
      ]
    },
    {
      "criterion": "AC-19",
      "text": "Given the HtmxPlugin class, when instantiated, then display_name returns 'HTMX' and description returns a non-empty string.",
      "testable": true,
      "issues": [],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 identity AC",
      "test_method_suggestions": [
        "test_display_name — assert plugin.display_name == 'HTMX'",
        "test_description_is_non_empty — assert isinstance(plugin.description, str) and len(plugin.description) > 0"
      ]
    },
    {
      "criterion": "AC-20",
      "text": "Given the forge.plugins.htmx package, when imported, then HtmxPlugin is importable from forge.plugins.htmx.",
      "testable": true,
      "issues": [
        "Will fail before the htmx module exists. This is expected (test-first)."
      ],
      "suggested_fix": null,
      "infrastructure_ready": true,
      "pattern_match": "MATCH — T-008/T-009/T-010 module export AC",
      "test_method_suggestions": [
        "test_module_export — from forge.plugins.htmx import HtmxPlugin; assert HtmxPlugin is not None"
      ]
    }
  ],
  "phase_3_infrastructure_readiness": [
    {
      "requirement": "PluginBase + 4 mixins with correct signatures",
      "status": "EXISTS",
      "location": "src/forge/plugins/base.py",
      "notes": "All 5 classes (PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider) exist with correct abstract method signatures. PluginBase defines name/display_name/description. Configurable: questions() -> list[Question]. FileProvider: files(spec) -> list[GeneratedFile]; directories(spec) -> list[str]. CommandRunner: generate(spec, target_dir, executor). DependencyProvider: dependencies(spec) -> list[str]."
    },
    {
      "requirement": "dependencies(self, spec) signature with spec parameter",
      "status": "EXISTS",
      "location": "src/forge/plugins/base.py:50-51",
      "notes": "Abstract method `def dependencies(self, spec: ProjectSpec) -> list[str]: ...` correctly includes `spec` parameter."
    },
    {
      "requirement": "Entry point registration in pyproject.toml",
      "status": "EXISTS",
      "location": "pyproject.toml:18",
      "notes": "Entry point `htmx = \"forge.plugins.htmx:HtmxPlugin\"` is registered as provided."
    },
    {
      "requirement": "AC-4 scanner (forbidden import detection, domain import requirement)",
      "status": "EXISTS",
      "location": "tests/unit/test_plugin_base.py:164-216",
      "notes": "Scanner uses rglob('*.py'), INFRA_EXEMPT_FILES={'base.py'}, checks all plugin files. Forbidden prefixes: forge.ui, forge.generation, forge.infrastructure. Enforces forge.domain import in every plugin file. Design Note 4 (line 64) correctly documents the untyped `executor` approach to avoid infra import ban."
    },
    {
      "requirement": "__init__.py domain import pattern for AC-4",
      "status": "EXISTS",
      "location": "src/forge/plugins/{fastapi,react}/__init__.py",
      "notes": "Established pattern: `from forge.domain import ProjectSpec as _  # noqa: F401`. The htmx/__init__.py must follow the same pattern."
    },
    {
      "requirement": "ValidationEngine.validate_plugin_config() CHOICE validation",
      "status": "EXISTS",
      "location": "src/forge/generation/validation.py:148-157",
      "notes": "CHOICE validation correctly rejects values not in question.options list. Returns ValidationError with severity='error'. Tested in test_validation.py:226-240 (test_choice_invalid_option)."
    },
    {
      "requirement": "MockTransaction duck-type pattern",
      "status": "EXISTS",
      "location": "tests/unit/test_plugin_react.py:14-28 (and test_plugin_fastapi.py, test_plugin_django.py)",
      "notes": "Identical _MockTransaction class in all 3 test files. API: stage_file(path, content) -> Path, stage_directory(path) -> Path, requirements: list[str]. Usable as-is for HTMX tests."
    },
    {
      "requirement": "MagicMock executor pattern for generate() tests",
      "status": "EXISTS",
      "location": "Multiple locations (test_plugin_react.py AC-14f, test_plugin_fastapi.py AC-7, test_plugin_django.py AC-13)",
      "notes": "Standard: `executor: MagicMock = MagicMock()`. AC-15 (no-op) uses `executor.run.assert_not_called()` — matches T-010 AC-14f webpack pattern."
    },
    {
      "requirement": "TemplateDefinition.frontend_id field",
      "status": "EXISTS",
      "location": "src/forge/domain/project_spec.py:24",
      "notes": "Field `frontend_id: str | None = None` exists. ACs 02a/02b/04 correctly use `frontend_id='htmx'`."
    },
    {
      "requirement": "CDN URL table for content assertions",
      "status": "EXISTS",
      "location": "docs/context/tickets/011-plugin-htmx.md:96-105",
      "notes": "4 CDN URLs documented with exact versions: HTMX @2.0.4, Alpine.js @3.14.8, Tailwind CSS (CDN), Bootstrap @5.3.3."
    },
    {
      "requirement": "Cross-method consistency map",
      "status": "EXISTS",
      "location": "docs/context/tickets/011-plugin-htmx.md:82-94",
      "notes": "9-row consistency map covering all documented config permutations. All rows show dependencies=[], generate=no-op, files() varies by config. Includes css_framework='tailwind' row (resolved N-5). Includes include_tailwind=True + css_framework='tailwind' row with CDN dedup note."
    },
    {
      "requirement": "Design Note 5 — test-first AC-18 construction guidance",
      "status": "EXISTS",
      "location": "docs/context/tickets/011-plugin-htmx.md:66-68",
      "notes": "Explicitly states: 'The AC-18 test must construct Question objects inline (not call plugin.questions()) to avoid a circular dependency.' Correctly references existing test_validation.py:test_choice_invalid_option pattern."
    },
    {
      "requirement": "Design Note 11 — CDN duplication guard",
      "status": "EXISTS",
      "location": "docs/context/tickets/011-plugin-htmx.md:78-79",
      "notes": "Explicitly states: 'When both include_tailwind=True and css_framework=\"tailwind\" are set, the Tailwind CDN script must appear in base.html exactly once — the implementation must guard against duplicate CDN entries.'"
    }
  ],
  "phase_3_identified_gaps": [
    {
      "requirement": "AC for include_tailwind=True + css_framework='tailwind' CDN deduplication",
      "status": "MISSING",
      "location": "N/A — no AC exists",
      "notes": "DN 11 documents the deduplication requirement and the consistency map includes the row, but no AC explicitly tests this configuration. See NEW-1 in phase_5."
    }
  ],
  "phase_4_coverage_analysis": {
    "happy_path": {
      "status": "COVERED",
      "ac_refs": ["AC-01", "AC-02a", "AC-02b", "AC-03", "AC-04", "AC-13", "AC-19", "AC-20"],
      "notes": "Plugin identity, core file paths, engine integration, questions, unconditional CDN, directories, identity metadata, module export."
    },
    "error_cases": {
      "status": "COVERED",
      "ac_refs": ["AC-16", "AC-17", "AC-18"],
      "notes": "Empty config dict (AC-16), missing plugin config key (AC-17), invalid css_framework value (AC-18). Three distinct error categories covered."
    },
    "edge_cases": {
      "status": "MOSTLY_COVERED",
      "ac_refs": ["AC-06", "AC-08", "AC-09", "AC-10", "AC-11", "AC-12"],
      "notes": "Boolean true/false/absent (AC-06, AC-08), all 3 CHOICE options (AC-09 tailwind, AC-10 bootstrap, AC-11 none), combined config variant (AC-12 bootstrap combo). ONE GAP: include_tailwind=True + css_framework='tailwind' CDN dedup (see NEW-1)."
    },
    "plugin_isolation_tested": {
      "status": "YES",
      "evidence": "AC-4 scanner (test_plugin_base.py:164-216) enforces: no forge.ui/forge.generation/forge.infrastructure imports in plugin files, all files import from forge.domain. Design Note 4 documents exemption for base.py (INFRA_EXEMPT_FILES). The untyped `executor` parameter in generate() avoids the infra import ban."
    },
    "cross_method_consistency": {
      "status": "COVERED",
      "evidence": "Consistency map (lines 82-94) documents 9 config permutations, all with dependencies()=[] and generate()=no-op. AC-14 (parametrized across permutations) tests dependencies invariant. AC-15 (parametrized) tests generate no-op invariant. AC-07/AC-08/AC-09/AC-10/AC-11/AC-12 test files() branching. Only files() is config-dependent, which is explicitly documented and tested."
    },
    "previously_uncovered_areas": {
      "css_framework_tailwind": {
        "status": "COVERED",
        "ac_ref": "AC-09",
        "notes": "Round 2 N-1 (MODERATE): css_framework='tailwind' with include_tailwind=False now covered."
      },
      "combined_tailwind_bootstrap": {
        "status": "COVERED",
        "ac_ref": "AC-12",
        "notes": "Round 2 N-2 (MODERATE): include_tailwind=True + css_framework='bootstrap' now covered."
      },
      "cdn_deduplication_guard": {
        "status": "DOCUMENTED_BUT_NOT_TESTED",
        "notes": "Round 2 N-6 (INFO): DN 11 documents deduplication. Consistency map has row. But no AC enforces it. See NEW-1."
      }
    },
    "consistency_map_audit": {
      "rows": 9,
      "covered_by_acs": 8,
      "uncovered_rows": [
        {
          "row": "include_tailwind=True + css_framework='tailwind'",
          "behavior": "Tailwind build files + Tailwind CDN in base.html (CDN added once, not duplicated)",
          "missing_ac": "No AC enforces the 'exactly once' deduplication behavior"
        }
      ]
    }
  },
  "phase_5_issues": [
    {
      "id": "NEW-1",
      "severity": "MODERATE",
      "type": "missing_testable_behavior",
      "description": "No AC for include_tailwinbd=True + css_framework='tailwind' CDN deduplication",
      "details": "Design Note 11 explicitly requires that 'the Tailwind CDN script must appear in base.html exactly once' when both include_tailwind=True and css_framework='tailwind' are set. The consistency map documents this case. However, no AC (AC-01 through AC-20) actually tests this configuration. AC-12 covers the analogous case with css_framework='bootstrap' (two different CDNs, no dedup concern), but the tailwind variant (same CDN could appear twice) is untested. A naive implementation could add the CDN script twice and pass all 20 ACs.",
      "impact": "Real bug (CDN duplication) would not be caught by the current AC suite.",
      "suggested_fix": "Add a new AC (e.g., AC-12b) or extend AC-12 with a parametrized variant: 'Given include_tailwind=True and css_framework=\"tailwind\" in config, when files() is called, then cdn.tailwindcss.com appears exactly once in base.html content.'",
      "location_in_ticket": "Between line 149 (AC-12) and line 153 (AC-13)"
    },
    {
      "id": "MINOR-1",
      "severity": "LOW",
      "type": "clarity",
      "description": "AC-02b uses 'txn.requirements.extend()' — not API-exact",
      "details": "The AC says 'dependencies() → txn.requirements.extend()' but the established _MockTransaction pattern uses `txn.requirements.append(dep)`. This is documentation style, not a testability blocker, but could cause minor confusion during test authoring.",
      "impact": "Negligible — test developer will follow established patterns.",
      "suggested_fix": "Change to 'dependencies() → txn.requirements.append()' for API accuracy, or leave as-is."
    },
    {
      "id": "MINOR-2",
      "severity": "LOW",
      "type": "clarity",
      "description": "AC-16 defaults verification not cross-referenced",
      "details": "AC-16 lists expected defaults (include_alpine=False, include_tailwind=False, css_framework='none') but does not explicitly map these to observable output. A developer must infer that these are verified through AC-06/AC-08/AC-11 expectations.",
      "impact": "Minor — experienced test developer will understand the mapping.",
      "suggested_fix": "Cross-reference AC-06, AC-08, AC-11 in AC-16 for clarity."
    },
    {
      "id": "INFO-1",
      "severity": "INFO",
      "type": "suggestion",
      "description": "AC-03 option order — specification or convention?",
      "details": "AC-03 specifies options=['tailwind', 'bootstrap', 'none'] with exact equality. This means order is part of the contract. If order is intentional (e.g., matching UI display order), this is fine. If not, consider relaxing to set equality.",
      "impact": "Informational — no change needed if order is intentional.",
      "suggested_fix": "None if order is intentional. Otherwise, document that options must contain exactly these three values (order is a UI convention, not a test contract)."
    }
  ],
  "coverage_summary": {
    "total_acs": 20,
    "testable": 20,
    "with_issues": 0,
    "infrastructure_gaps": 0,
    "uncovered_behavior": 1,
    "verdict_rationale": "The ticket is well-structured with 20 testable ACs, all 6 Round 2 issues resolved, and all infrastructure ready. One moderate gap remains: the CDN deduplication behavior (include_tailwind=True + css_framework='tailwind') is documented (DN 11) but not AC'd. Adding one AC for this case would make the suite complete."
  },
  "recommendations": [
    "Add AC-12b (or extend AC-12): 'Given include_tailwind=True and css_framework=\"tailwind\" in config, when files() is called, then cdn.tailwindcss.com appears exactly once in base.html content.'",
    "Use test_plugin_react.py as structural template (same AC numbering patterns).",
    "Create _make_htmx_spec helper with frontend_id='htmx', following _make_react_spec pattern (tests/unit/test_plugin_react.py:31-46).",
    "Use parametrized tests for AC-14 (dependencies empty) and AC-15 (generate no-op) across all 5+ permutations.",
    "For AC-16, decompose into multiple test methods following AC-06/AC-08/AC-11 patterns.",
    "Ensure htmx/__init__.py follows the established pattern: `from forge.domain import ProjectSpec as _  # noqa: F401` + plugin re-export.",
    "Ensure htmx/plugin.py uses untyped `executor` parameter in generate() to comply with AC-4 scanner (no forge.infrastructure import).",
    "For AC-18, construct Question objects inline per Design Note 5 (do not call plugin.questions())."
  ],
  "verdict": "CHANGES_REQUESTED",
  "blocking_issues": []
}
```

---

### Summary

**Round 2 Issue Verification**: All 6 issues (2 moderate, 2 low, 2 info) are RESOLVED. AC-09 covers `css_framework="tailwind"`. AC-12 covers the `include_tailwinbd=True + css_framework="bootstrap"` combination. AC-11 references exact CDN URLs. AC-18 uses `len(errors) >= 1`. The consistency map has the `css_framework="tailwind"` row. DN 11 addresses CDN duplication guard.

**Round 3 New Findings**: One moderate issue discovered: the CDN deduplication behavior for `include_tailwind=True + css_framework="tailwind"` is documented in DN 11 but has no AC enforcing it. AC-12 covers the analogous bootstrap combination, but the tailwind deduplication case (same CDN URL appearing exactly once) is the critical edge case that warrants its own AC.

**Infrastructure**: Fully ready. All 5 base classes exist with correct signatures. Entry point registered. AC-4 scanner enforces isolation. ValidationEngine validates CHOICE. MockTransaction and MagicMock patterns established. TemplateDefinition.frontend_id exists.

| Severity | New | Remaining |
|----------|-----|-----------|
| BLOCKING | 0 | 0 |
| MODERATE | 1 | CDN deduplication (NEW-1) |
| LOW | 2 | AC-02b wording (MINOR-1), AC-16 cross-references (MINOR-2) |
| INFO | 1 | AC-03 option order suggestion (INFO-1) |

Adding one AC (e.g., AC-12b) for the `include_tailwinbd=True + css_framework="tailwind"` case would resolve the last gap and make the verdict **READY**.
