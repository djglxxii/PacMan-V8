# T### — Short Title

| Field | Value |
|---|---|
| ID | T### |
| State | planned / active / blocked / completed |
| Phase | 0 Scaffold / 1 Visual / 2 Movement / 3 Ghost AI / 4 Life cycle / 5 Scoring / 6 Audio / 7 Polish |
| Depends on | T###, T### (or "none") |
| Plan reference | `docs/VANGUARD8_PORT_PLAN.md` §N |
| Spec reference | `/home/djglxxii/src/Vanguard8/docs/spec/...` |

## Goal

One or two sentences. What does this task deliver, and why is it the next
meaningful step?

## Scope

- In scope: bulleted list of what this task will change or produce.
- Out of scope: bulleted list of things that might look related but are
  explicitly NOT being done here.

## Implementation notes

Relevant code paths, algorithms, register writes, file locations. Not a
full design doc — just enough for the next-session agent to pick up
without re-deriving everything. Reference the architectural plan for
anything substantial.

## Acceptance Evidence

**Artifact(s):**

- `vanguard8_port/tests/evidence/T###-name/<file>` — what it is + how it
  was produced

**Reviewer checklist** (human ticks these):

- [ ] Artifact 1 shows <expected visible/audible feature>
- [ ] Artifact 2 matches <expected hash / value / state>
- [ ] No regression in previously-completed tasks' evidence

**Rerun command:**

```
<exact command line the reviewer can run to regenerate the evidence>
```

## Progress log

- YYYY-MM-DD — created, state: planned.
- YYYY-MM-DD — activated.
- YYYY-MM-DD — ...

## Blocker (only if state = blocked)

- **Blocking system:** (e.g. emulator, missing spec)
- **Symptom:** exact observed failure
- **Minimal repro:** commands + expected vs. actual
- **Resolution needed:** what would unblock
