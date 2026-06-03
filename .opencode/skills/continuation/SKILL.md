---
name: continuation
description: Generate session handoff documents for seamless transitions between agent sessions
---

# Continuation Skill

Generate session handoff documents that enable seamless transitions between agent sessions.

## Purpose

Preserve context and progress between sessions so the next session can continue without rework or confusion.

## Trigger

Before ending any session, generate a continuation prompt if work is incomplete.

## Session Folder Structure

Each session produces a single flat file at `.opencode/handoffs/YYYY-MM-DD-title.md` with all content inline:

```
.opencode/handoffs/
├── 2024-03-25-forge-init.md
├── 2024-03-26-plugin-system.md
└── session-handoff.md              # Template
```

## Document Structure (handoff.md)

Each handoff file follows the template at `.opencode/handoffs/session-handoff.md`. All agent outputs (reviews, decisions, analysis) are appended inline under `## Agent Outputs` rather than saved to separate files.

## How Agents Get Code Context

For review agents that need to see code:
1. Run `git diff HEAD~1` to see changes from previous session
2. Run `git diff --name-only` for a list of changed files
3. Use `git show HEAD:path/to/file.py` to see file contents

## Storage

Save handoff as `.opencode/handoffs/YYYY-MM-DD-title.md` using the template.

## Usage

To start a new session from handoff:
1. Read the handoff file from `.opencode/handoffs/YYYY-MM-DD-title.md`
2. Check specs in `docs/context/`
3. Run `git diff HEAD~1` to see what was implemented
4. Check `## Agent Outputs` section for previous review outputs
5. `/clear` context and start fresh

## Context Management

- Compact at 60% context, not 90%
- Fresh session with written handoff > resuming stale context
- Fewer tokens = fewer errors = higher accuracy
