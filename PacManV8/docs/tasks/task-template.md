# T### — Short Title

| Field | Value |
|---|---|
| ID | T### |
| State | planned / active / blocked / completed |
| Phase | (phase name) |
| Depends on | T###, T### (or "none") |
| Plan reference | `docs/PLAN.md` section name |

## Goal

One or two sentences. What does this task deliver, and why is it the next
meaningful step?

## Scope

- In scope: bulleted list of what this task will change or produce.
- Out of scope: bulleted list of things that might look related but are
  explicitly NOT being done here.

## Scope changes

*(Document any reductions or expansions to the original scope, with dates
and reasons. Leave empty if scope is unchanged.)*

## Pre-flight

- [ ] (prerequisites beyond task dependencies — tools installed, prior
  evidence verified, etc.)

## Implementation notes

Relevant code paths, algorithms, configurations, file locations. Not a full
design doc — just enough for the next-session agent to pick up without
re-deriving everything. Reference the architectural plan for anything
substantial.

## Acceptance Evidence

**Artifact(s):**

- `tests/evidence/T###-name/<file>` — what it is + how it was produced

**Reviewer checklist** (human ticks these):

- [ ] Artifact 1 shows (expected visible/audible/measurable feature)
- [ ] Artifact 2 matches (expected hash / value / state)
- [ ] No regression in previously-completed tasks' evidence

**Rerun command:**

```
(exact command line the reviewer can run to regenerate the evidence)
```

## Progress log

| Date | Entry |
|------|-------|
| YYYY-MM-DD | Created, state: planned. |
| YYYY-MM-DD | Activated. |
| YYYY-MM-DD | ... |

## Blocker (only if state = blocked)

- **Blocking system:** (e.g. external tool, missing spec, upstream bug)
- **Symptom:** exact observed failure
- **Minimal repro:** commands + expected vs. actual
- **Resolution needed:** what would unblock
