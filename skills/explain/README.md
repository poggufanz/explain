# explain

A skill for explaining a single change after the spec/plan is written or after the implementation is done. It has one goal: the user can run the manual steps themselves, verify the result, and understand the impact — not merely receive a copy of the spec.

## When it activates (three moments)

| Moment | Situation | Behavior |
|---|---|---|
| A | A spec/plan was just written, no code yet | Ask **once** whether to explain now or wait for implementation, then **stop**. This also applies to a spec/plan that is **not yet approved**; no part of an explanation appears before the user answers |
| B | Implementation just finished | **Explain immediately** in the same turn; no permission question |
| C | The user asks on their own | The request = consent; start right away. A narrow request (e.g. only a diagram) is handled within that scope alone, and the rest is offered in one line |

Moments are determined from the work phase of this session, not from the presence or absence of old code in the repo.

## What it produces

- **Five sections:** as-is/to-be ASCII diagrams, the user's hands (manual steps), feature relationships (upstream/downstream/shared), implementation explanation + coverage map, and business impact.
- **Three presentation layers:** ELI5 → scope-appropriate → per-feature detail (the detail layer contains all five sections).
- **Coverage map** as proof of completeness: every inventory item and every spec/plan point has a row and a place in the output.
- **Evidence status** per item: `planned:` (still only in spec/plan), `code-available:` (code exists in the repo; deployment & verification not yet established), `verified:` (there is proof it runs or the user states it — the source is named).

## Limits

- This skill is **read-only**: it composes a list of steps, it does not execute them — it runs no deploy, migration, or restart on the user's behalf.
- Exact commands are written only when they can be read from the repo; otherwise only the setting name + location + `source: not in repo` is given. Unknown values are written `<value from you>`.
- Negative claims are bounded by the stated search scope (e.g. the `git grep` command + scope + residual risk, or `not traced yet`); there are no absolute claims such as "safe" or "no consumers".
- On a **non-git** repo, diffs are unavailable entirely: material comes from the spec/plan + direct file reads, and that is stated as-is. On a git repo **with no commits** (HEAD not yet born), diffs are still available for content already staged via `git diff --cached` plus reading working files from disk; commands that mention `HEAD` (`git diff HEAD`, `git show HEAD:...`) cannot be used there.

## Discovery and installation

This skill relies on **automatic discovery** by the harness: the harness reads the frontmatter `description` and loads `SKILL.md` when it matches the situation. That is not a deterministic hook — whether it triggers automatically depends on the harness in use and whether this folder is already in that harness's skill index. Trigger cues are also available in Indonesian in the `description` (e.g. "as-is ke to-be", "langkah manual", "dampak bisnis", "relasi fitur", "ELI5") to help match situations; triggering itself still follows the harness mechanism, not a manual action guaranteed by this skill.

The `skills/explain/` folder is **self-contained** and can be copied to any skill path supported by the target harness. This skill is **not installed globally** on this system, and there is no claim of automatic installation outside that harness mechanism.

## Folder contents

- `SKILL.md` — the skill's main instructions. English translation, no semantic changes: sha256 `f60f1cafcf567a1b1c29046b2a2e9e5e492bf2a2c8859e429301325e82802d14` (366 lines).
- `evals/` — evaluation harness kept at the **repository root**, outside this folder: `evals/evals.json` holds the evaluation definitions (20 output scenarios + 8 trigger queries in `description` proxy mode) and `evals/run_evals.py` runs them against fixture repos. Run results are recorded separately in `evals/results/` by the evaluator; this README makes no claim about those results. It is not part of the skill package and is not shipped when the skill is installed.
- `CHANGELOG.md` — history of fixes.

Full mechanical audit (findings, evidence, checklist): see `explain-review.md` at the repository root.
