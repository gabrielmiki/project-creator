---
name: ticket-generator
description: Convert a PRD into structured, actionable tickets for implementation
---

# Ticket Generator Skill

Convert a PRD into structured, actionable tickets for implementation.

## Purpose

Transform well-understood requirements into a backlog of implementable tickets with clear acceptance criteria, dependencies, and ordering.

## Trigger

After PRD is complete and user asks to generate tickets/stories.

## Behavior

### Step 1: Analyze PRD

Let the model reason freely about:
- Ticket boundaries (one logical unit of work per ticket)
- Dependencies between tickets (what must come first)
- Layer assignments (which src/ directory each belongs to)

### Step 2: Generate Structured Tickets

Each ticket must include:
- **title**: Concise, action-oriented
- **type**: story | task | bug
- **description**: What this ticket does, why it matters
- **acceptance_criteria**: In Given/When/Then format, with measurable outcomes
- **api_spec**: If applicable (path, method, Query/Path/Body labels)
- **complexity**: simple | medium | complex
- **dependencies**: List of blocking tickets by title
- **layer**: domain | plugins | generation | ui

### Step 3: Order Tickets

Follow foundation-first sequence:
1. Domain models (ProjectSpec, Template, Domain)
2. Infrastructure (file operations, process execution)
3. Plugin system (base class + individual plugins)
4. Generation orchestrator + Justfile generator
5. UI screens (wizard workflow)
6. Entry point + packaging

## Output Format

Generate tickets as a structured list. For Linear/GitHub integration, output one ticket at a time with the full structure.

## Constraints

- Do NOT generate tickets from partial PRDs
- Mark assumptions explicitly ("ASSUMPTION: X") rather than guessing
- Break complex tickets into smaller ones if > 200 lines of implementation
- Every ticket must have at least one acceptance criterion with a measurable outcome
