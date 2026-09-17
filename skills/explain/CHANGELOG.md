# Changelog — `explain` skill

Fixes follow the mechanical audit in `explain-review.md` at the repository root (blocking findings about the `description` trigger, moment predicates, the direct-request gate, and the absence of tests). This file records changes to the skill's content; evaluation test results are not claimed here — `evals/evals.json` holds the scenario definitions and run results are recorded separately by the evaluator.

## Revision 2 — 2026-09-17 (sha256 `e0186f2afa2cecd277b5d89ab8a31557d7547f1fe87249c8bc82366e11c10bc5`, 366 lines)

**Permission gate & moments**

- Moments come from the **work phase**, not from the presence or absence of code in the repo: writing a spec/plan yourself does not count as a material change, so the "no implementation yet" branch is no longer dead.
- Moment B no longer asks permission; the gate exists only at Moment A.
- Moment C is explicit: a user request = consent, including for a not-yet-approved spec/plan (explained as decision material). A narrow request is handled partially + one offer for the rest.
- The boundary with the `handoff` skill is stated (a conversation summary is not a feature delta).
- `description` starts with "Use when…"; over-broad synonyms (plain `"jelaskan"`, `"how does this work"`, `"handover"`) were removed, replaced with event + object phrases, plus Indonesian equivalents for the core terms: `dampak bisnis`, `langkah manual`, `relasi fitur`/`fitur yang terdampak`, `as-is ke to-be`.

**Change inventory (git)**

- Material = the **union** of local changes (staged + unstaged + untracked) **and** the commit range since baseline (`git diff <baseline>..HEAD`) **and** spec/plan points with no code — not just `git status` or only the last commit.
- The git path is chosen per state: repo with commits, repo without commits (no `HEAD` commands, uses `git diff --cached` + file reads), and non-git (skip git; inspect spec/plan + file structure, ask the user only when the baseline cannot be found).
- Low-similarity renames are confirmed with `git diff -M --name-status` before concluding "new file + deleted file"; deleted files are read from the revision that contains them, not always `HEAD:<path>`.

**Evidence, completeness, relationships**

- The `terpasang:` label (implying deployed) was replaced with `code-available:`; three evidence statuses `planned:` / `code-available:` / `verified:` + evidence source.
- Completeness is guaranteed by a **coverage map** (item × source × status × output section) + per-point spec disposition: as planned / `deviates:` / not yet done; diagrams are limited to one block per feature and may use a combined box that points to the coverage map.
- Feature relationships add an **upstream** direction (`B -> A.c`) and **shared** contracts, not just downstream consumers; every consumer is labeled direct/indirect.
- **Unknowns are bounded:** absolute claims are forbidden; the required form is "Not found within the scope of `<command>` (<scope>)" + residual risk not covered, or `not traced yet`.

**User's hands, business impact, gotchas**

- **No invented commands:** exact commands only when readable from the repo (scripts/Makefile/CI/README/Dockerfile); otherwise write the step type + setting name + dashboard location + `source: not in repo`; unknown values `<value from you>`; steps with no inferable consequence are marked `consequence: cannot be determined from repo`. The skill does not execute deploy/migrate/restart.
- **Business impact from process**, not a list of code keywords: the trigger is behavior seen by customers/operators, money/tax/reporting, access/private data, or manual processes; at Moment A it is answered from the spec/plan. None of these → a single line `No business impact: <reason>`.
- Gotchas are made conditional per stack and tied to repo evidence (Laravel config cache, worker/queue restart, migration & backfill, asset build, third-party dashboards, external consumer API contracts) — non-universal architecture recipes were removed.

**Output shape**

- Narrow request: only the requested section + one offer line; the remaining self-check items are N/A.
- The "one block" constraint was removed: large output may be paginated with explicit scope markers, without silent truncation.
- Examples were made hypothetical and consistent with a single state; unsupported claims were removed.

## Revision 1 — 2026-09-17

Initial version (333 lines): five sections + three layers, four output templates, permission gates at Moments A and B, material from `git status --porcelain` + `git diff`, only the `planned:` label, human-hands commands with no grounding rules, business impact based on a list of areas.
