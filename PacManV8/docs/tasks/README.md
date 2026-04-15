# Task Workflow

This directory is the execution queue for Pac-Man for Vanguard 8. Every unit of
engineering work corresponds to exactly one task file in `planned/`,
`active/`, `blocked/`, or `completed/`. `INDEX.md` is the at-a-glance
master list.

## States

```
planned/    Spec'd but not started. Ordered by intended execution.
active/     Currently being worked on. At most ONE task here at a time.
blocked/    Started but can't proceed due to an external dependency.
completed/  Accepted by human reviewer. Immutable — do not edit.
```

## Lifecycle

```
              create new task
                    |
                    v
               +---------+
               | planned |
               +----+----+
                    |  user authorizes start
                    v
               +---------+       +---------+
               | active  |------>| blocked |
               +----+----+       +----+----+
                    |                 | blocker resolved
                    |  evidence       |
                    |  produced       +---> back to active
                    v
          (stop for review)
                    |
                    |  user approves
                    v
               +-----------+
               | completed |
               +-----------+
```

## Rules

### One active task at a time

Moving a second task to `active/` while one is already there is forbidden.
If the active task is stalled, either complete it (with reduced scope
documented in the task file) or move it to `blocked/`. Never leave two
tasks open.

### Every task has human-verifiable acceptance evidence

The task file must have an **Acceptance Evidence** section describing:

- What artifact(s) the reviewer will inspect
- Where those artifacts live (path under `tests/evidence/`)
- What the reviewer should be looking for (explicit checklist)

A task that compiles but has no reviewable artifact is **not complete**.

### Stop for review at every boundary

When the active task's evidence is ready, the agent stops and reports to
the user. The agent does not pick up a new task on its own. The user
explicitly approves (-> move to `completed/`) and then designates the next
task to activate.

### Task files are append-mostly

While a task is active, update its **Progress Log** with a timestamped
entry each session. Do not rewrite history. Do not delete a task file
that was worked on — mark it completed (with a "scope: abandoned" note)
or move it to `blocked/` with context.

### Blockers name the blocker precisely

If an error from an external tool, emulator, dependency, or documented workflow
prevents the active task from continuing, the task must be moved to
`blocked/`. Do not leave a task in `active/` when progress is blocked by an
error the agent cannot resolve within the repo's allowed scope.

A blocked task must state:

- Which external system is blocking
- The exact symptom (error message, incorrect output, etc.)
- The minimal repro (inputs + commands)
- What resolution would unblock it

Vague "doesn't work" blockers are rejected — either diagnose further or
mark the task complete with reduced scope.

## Task ID convention

Tasks are numbered `T###` in creation order. IDs are never reused. The file
name is `T###-short-kebab-name.md`. The `T###` prefix and short name
together identify the task; keep the short name stable across state moves.

## Creating a new task

1. Copy `task-template.md` to `planned/T###-name.md` using the next free
   number.
2. Fill out all sections. Required sections cannot be left empty.
3. Add a one-line entry to `INDEX.md` under the appropriate phase.
4. Stop and get user approval of the task spec before activating.

## Activating a task

1. `mv planned/T###-name.md active/T###-name.md`
2. Update `INDEX.md` state column.
3. Add the first Progress Log entry with today's date.
4. Begin work.

## Completing a task

1. Produce all artifacts listed in Acceptance Evidence.
2. Store artifacts under `tests/evidence/T###-name/`.
3. Fill in the **Acceptance Evidence** section's reviewer checklist with
   actual paths and values.
4. Add a final Progress Log entry summarizing what was done.
5. **Stop and report to the user.** Do not move the file yet.
6. On user approval: `mv active/T###-name.md completed/T###-name.md` and
   update `INDEX.md`.

## Blocking a task

1. In the task file, add a **Blocker** section with the details described
   above.
2. `mv active/T###-name.md blocked/T###-name.md`
3. Update `INDEX.md` state column with a one-line blocker summary.
4. Report to the user and stop.
