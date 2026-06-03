---
name: clear-review
description: C.L.E.A.R. checklist framework for AI-generated code review
---

# C.L.E.A.R. Code Review Skill

Structured code review framework optimized for AI-generated code.

## Purpose

Provide a systematic checklist for reviewing code, with special attention to AI-specific failure modes.

## Trigger

When user asks to review code, or before any commit.

## Dimensions

### C — Context
Does implementation match original intent?
- [ ] Check story file / acceptance criteria
- [ ] Verify commit message reflects actual changes
- [ ] Confirm no feature creep (scope expanded beyond ticket)

### L — Logic
Is business logic correct?
- [ ] Trace happy path manually
- [ ] Trace at least one error path
- [ ] Check edge cases are handled
- [ ] For generation: validate plugin output correctness

### E — Efficiency
Are there performance issues?
- [ ] Unnecessary loops or repeated computation
- [ ] Redundant filesystem operations
- [ ] Subprocess calls without timeout

### A — Architecture
Does code respect project patterns?
- [ ] Layer separation (ui → generation → plugins)
- [ ] No circular imports
- [ ] Plugin isolation (plugins never import from ui/)
- [ ] Domain models contain zero UI logic

### R — Reliability
Are error cases handled?
- [ ] Exceptions caught at appropriate layer
- [ ] Plugin failures don't crash the UI
- [ ] Filesystem operations have rollback/error handling

## AI-Specific Checks

- [ ] **Duplication**: Search for similar code blocks that could be extracted
- [ ] **Shallow tests**: Assertions check values, not just status codes
- [ ] **Missing guards**: Null checks, early returns, type validation
- [ ] **Unused imports**: All imports are actually used
- [ ] **Consistent patterns**: Matches existing codebase conventions
- [ ] **Plugin isolation**: Verify plugin code doesn't import from `forge.ui`

## Output

Generate structured review with:
- Verdict: APPROVE | REQUEST_CHANGES | BLOCK
- Findings per dimension
- Specific file:line citations
- Actionable recommendations

## Workflow

After completing the checklist:
1. Summarize findings by dimension
2. Prioritize blocking issues vs. suggestions
3. Provide specific file:line references
4. Offer actionable recommendations
