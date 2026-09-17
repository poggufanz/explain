---
name: explain
description: Use when a spec or implementation plan has just been written, when its implementation has just completed, or when the user asks to be shown the change — "explain the spec that was just written", "walk me through the plan", "explain what changed in this implementation", "explain the as-is/to-be of this change", "handover of a just-completed implementation", "as-is ke to-be", "langkah manual yang harus dijalankan sendiri", "dampak bisnis", "relasi fitur", "fitur yang terdampak", "ELI5". Not for explaining one function or file, code review, API docs, concept questions, diagrams without a code change, mapping a whole codebase, or conversation summaries (that is the handoff skill).
---

# Explain

## Overview

**Core principle:** a change is not finished until the user can run it themselves, verify it, and understand its impact. This skill turns a freshly written spec, plan, or implementation into five parts: an as-is/to-be diagram, a list of user hands, a feature relations map (upstream/downstream/shared), an implementation explanation + coverage map, and business impact. It is presented in three layers: ELI5 → within scope → per-feature detail.

Two rules decide whether the whole output is right:

1. **Inventory first, graphics later.** The Moment A permission gate still comes first; once the gate is done (or from the start in Moment B/C), build a complete list of changes (including committed, staged, and untracked) before writing a single sentence of explanation.
2. **Every change carries an evidence status.** `planned:` (still in the spec/plan, no code yet), `code-available:` (code exists in the repo; deployment and verification are not established), `verified:` (there is run evidence, or the user states it — name the source). No status without a basis.

## When to Use

Three trigger moments:

1. **A spec or plan was just written, no implementation yet** — ask one permission question, then stop.
2. **A spec or plan was just implemented** — start explaining immediately; no permission question.
3. **The user asks for the explanation themselves** — that request is already permission; start immediately.

Other symptoms: the user asks "what was just built", "why did it change", asks for a handover of the implementation delta, asks for an as-is/to-be diagram, is unsure which manual steps they must run themselves, or asks which other features are affected.

**When NOT to use:**
- A one-off experiment or spike whose code gets thrown away — a short findings report is enough.
- The user only needs one fact ("which files changed?") — answer directly.
- A general concept or terminology question ("what is dependency injection") — there is no spec/implementation delta.
- Mapping the architecture of the whole codebase — that needs a mapping skill, not the as-is/to-be of one change.
- A diagram drawn without a code change (e.g. an ERD from an existing schema).
- A conversation summary for the next session — that is the handoff skill, not a feature delta.

## Quick Reference

| Observed situation | What to do |
|---|---|
| Spec/plan just written, no code yet | Moment A: ask permission, stop. Material = spec/plan + as-is code; every line is labeled `planned:` |
| The repo already has old code, but this session only wrote a spec | Still Moment A: the moment comes from the work phase, not from code existing in the repo |
| Implementation just finished (dirty or already committed) | Moment B: start immediately, no permission question |
| User asks on their own | Moment C: permission already exists, start immediately |
| User asks for only one part | Do that part, offer the rest in one line |
| Working tree is clean but the implementation is in commits | Use `git log` + `git diff <baseline>..HEAD`; never conclude "no changes" |
| Changes are staged or untracked | `git status --porcelain -uall` + `git diff HEAD`; read `??` files directly |
| The repo is not git (or has no commits) | Check the spec/plan + file structure first; ask the user only if the baseline cannot be found |
| Working-tree changes outside the spec/plan scope | Record `out of scope` + reason; do not flip the moment |
| Changes touch relevant docs/config/tests | They enter the coverage map like code files |
| No manual steps | Write one line "No manual steps" + reason |
| Genuinely no business behavior changed | Write one line "No business impact" + reason |

## Workflow

Copy this checklist into a todo and tick it as you go. Each step has a "Done when"; the next step starts only after its criteria are met.

### Step 0 — Determine the moment, then open the permission gate

**Material change** = a code/asset change outside the spec/plan documents **that falls within the spec/plan scope (or the user's request)**, whether in the working tree or in implementation commits. Writing the spec/plan itself is not a material change. Out-of-scope changes — build/generated artifacts, local files, unrelated other modules — are recorded as `out of scope` and do **not** flip the moment; if the scope cannot be established, ask the user one short question.

- **Moment A — spec/plan just written, no material change yet.** Write one question, then stop:

  > "Spec/plan `<path>` is ready. Should I explain it now (still a plan), or wait until the implementation is done?"

  Not a single part of the explanation may be written before the user answers. A freshly written spec is not necessarily approved — this gate still applies; state in the question that the explanation is still a plan. User says no or not yet? Stop; the explanation can be requested at any time.
- **Moment B — implementation just finished.** Start immediately; no permission question. Announce in one line: "I'm using the explain skill."
- **Moment C — the user asks on their own.** The user's request is already permission; start immediately. This also holds when the spec/plan is not approved yet: explain its contents as decision material, do not withhold the explanation until the spec is approved. If the request is narrow (e.g. only a diagram), do that part then offer the rest in one line.

The moment is determined by the **work phase** — what just happened in this session: a spec was just written (A), an implementation just finished (B), the user asked (C). Old code existing in the repo does not make the moment B. Material change is used to gather material and to correct when the phase is unclear: phase B but no in-scope material change → ask one short question ("which commit/range should I explain?"), not conclude "no changes".

**Done when:** in Moment A the question has been sent and there is no output; in Moments B and C the work has started without a gate question.

### Step 1 — Inventory the changes (complete before writing)

Never conclude "no changes" from a single command. Walk through in order:

1. **Pick the path first; do not run `HEAD` commands blindly:**
   - **Git repo with commits:** the full path — `git status --porcelain -uall`, `git diff HEAD`, history (`git log` / `git show`).
   - **Git repo without commits (unborn HEAD):** do not use commands that mention `HEAD` (`git diff HEAD` and `git show HEAD:...` fail here). Use `git diff --cached` for indexed contents and read working files directly from disk.
   - **Not git:** skip git entirely. Explore the spec/plan, the folder structure, and the files that appear involved; ask the user only if the baseline (what changed) cannot be found yourself, and state that no diff is available.
2. **Working tree (git-repo path):** `git status --porcelain -uall`. One line per path: `M` modified, `A` added, `D` deleted, `R` renamed (two paths, `old -> new`), `??` untracked. All these lines are inventory items except spec/plan paths; clearly out-of-scope items (build artifacts, local files, other modules) are still recorded with the `out of scope` label + a short reason.
3. **Change contents:** `git diff HEAD` (covers staged and unstaged relative to HEAD). `??` files do not appear in the diff → read them directly. Low-similarity renames may appear as `A` + `D` rather than `R` — before concluding "new file + missing file", check `git diff -M --name-status <baseline>..HEAD` (or a lower threshold, e.g. `-M5%`). Deleted files are read from the **revision that contains them** — the baseline (`git show <baseline>:<path>`) or the rename source; `HEAD:<path>` only if the file still exists at HEAD. Files that do not exist yet (still a plan) are read from the spec/plan. `out of scope` items only need recording — unrelated user work does not need to be read.
4. **Baseline and range.** Determine the baseline: the commit before the spec/plan was written, the branch point, or a commit the user names. Material = the **union** of `git diff <baseline>..HEAD` (already committed) + `git diff HEAD` and `??` files (still local) — not just the last commit. With no commits at all there is no range: the material is the working tree. `git log --oneline -n 20` to find candidates and `git show --stat <sha>` to see contents. Baseline cannot be established from the repo → ask the user one question: "Which commit/range is the implementation of this feature?" Never invent a range.
5. **Relevant docs, config, and tests:** spec/plan that now differs from the code, README, config keys/env, schema, and tests that still expect the old behavior. These items enter the inventory like code files.
6. **Symbols:** functions, classes, endpoints, columns/tables, events, config keys.
7. **Status of each item:** `planned:` no code yet (only in the spec/plan), `code-available:` code exists in the repo but there is no run evidence and deployment is not established, `verified:` there is evidence you saw (command + result) or the user states they verified it — name the source, e.g. `verified: user's word`.

**Done when:** the material is complete as the **union** of three sources — (a) local changes from `git status --porcelain -uall` + `git diff HEAD` (or `git diff --cached` in a repo without commits) outside spec/plan paths, (b) the commit range since the baseline (`git diff <baseline>..HEAD`), (c) spec/plan items that have no code yet; every item has a row in the Step 5 coverage map with its source (staged / unstaged / untracked / `commit <sha>` / `revision <baseline>` / spec); every in-scope item has been read in the version available (now, the containing revision for deleted ones, the spec for ones that do not exist yet); `out of scope` items are recorded; the list of new/changed symbols is written.

### Step 2 — Draw as-is and to-be

Draw both states side by side in one ASCII block (Template 1). What must be visible:

- The entry point (request, CLI, UI, event) and the final effect (response, DB row, file, notification, external call).
- Every file/module involved, with its real file name, marked `(~)` changed or `(+)` new.
- The direction of data flow between boxes, including the storage (table/column) or config used.
- The point where the old and new behavior start to differ.

**Scale:** one block per feature. If a feature has more than eight boxes, draw only the main path and merge similar files into one labeled box, e.g. `src/report/*.js (4 files, ~) — see coverage map`. The Step 5 coverage map guarantees completeness, not the diagram.

**Done when:** there is at least one complete path from the entry point to the final effect; there is one "behavior difference point" box; every material item is in the diagram or in a merged box that points at the coverage map; boxes use real file names with `(~)`/`(+)` markers.

### Step 3 — Build the user hands list

Check these eight categories one by one, then write the real findings (Template 2):

1. New dependency/install (runtime version, package manager).
2. New env/secrets (credentials, tokens, value limits).
3. Data schema (migrations, new columns, backfilling old data).
4. Cache/config/route/view (the cleanup commands for this stack).
5. Asset build (only if the repo has a build step).
6. Restarting processes that hold old code (web, worker, scheduler, container).
7. Third-party dashboard configuration (webhook URL, OAuth redirect, DNS, cron).
8. Feature flags, roles, or permissions that must be turned on.

Each step is written with: **type** (CLI / dashboard / manual), **place** (local/staging/production), **step**, **impact if skipped**, **verification**.

Grounding rules:

- **Exact commands only if they are readable from the repo** — `package.json` scripts, Makefile, taskfile, composer/artisan, alembic, Dockerfile, CI, README. If not readable, **do not write any command at all**, including estimated commands with a source marker: write the step type + setting name + its location (vendor dashboard, cloud console) + `source: not in repo`.
- **Impact if skipped only if it can be inferred from the code.** If not → write `impact: cannot be determined from the repo`. Never invent error messages.
- **Unknown values are written as `<value from you>`** (e.g. discount limit, client ID). Never invent numbers, credentials, or URLs.
- **Never run anything that changes the system** — deploy, migrate, restart — and never tell the user to run it now. This skill builds the list, it does not execute.

If there are no manual steps: write one line "No manual steps" with the reason.

**Done when:** all eight categories have been checked one by one; every step has a type, place, impact (or the reason it is unknown), and verification; commands not readable from the repo are not written at all (just the setting name + location + `source: not in repo`).

### Step 4 — Map feature relations (upstream, downstream, shared)

Answer with evidence, not guesses (Template 3):

1. **What does it attach to?** A new feature C is usually an add-on to feature A: `A` + `C` becomes `A.c`. Name the attachment point (column, method, endpoint, event, config key) and name feature A as the owner.
2. **Downstream — who reads `A.c`?** Callers, queries, reports, jobs, exports/imports, cache keys, API contracts, external consumers.
3. **Upstream — who writes/supplies `A.c`?** Import jobs, other features, admin actions, seeds/backfills, input screens. This direction is what makes B affect A.c: name the mechanism (`B -> A.c`), not just `A.c -> B`.
4. **Shared — contracts used by both.** Columns, config keys, events, job payloads, response formats: name the owner and the users, plus who must change when the contract changes.
5. **Bounded negatives.** Never write absolute claims like "no consumers", "safe", or "other features are unaffected". Write the bounded form: "Not found within the scope of `git grep -n "<symbol>"` (whole repo, excluding generated files)" + what is not covered (external clients, BI/SQL, jobs outside the repo). Not checked → write `not yet traced`.

**Done when:** every attachment point has a downstream, upstream, and shared row with evidence matching the state — `path:line` when the code exists, `as-is <path:line>` or `spec §<n>` when it does not, `not yet traced` for anything outside the repo; every consumer is labeled **direct** (reads/writes `A.c`) or **indirect** (feature B uses A's output, which has now changed); every negative claim names the command + scope + residual risk.

### Step 5 — Write the implementation explanation + coverage map

Per feature, then per file (Template 4). Every changed/new/deleted file — in Moment A: every file that will be touched — gets: what changed, why, which symbols, a short flow, error handling, and one way to test it. The status column uses `planned:` / `code-available:` / `verified:` (Step 1 item 7).

The **coverage map** (coverage ledger) is proof of completeness, not a count of status rows:

| Item | Source | Status | Symbol / spec item | Output part |
|---|---|---|---|---|
| `src/cart.js` | unstaged | `code-available:` | `Cart::total` | Layer 3 §1 |
| `docs/specs/x.md` item 3 | spec | `planned:` | — | Layer 3 §4 |

- Every Step 1 item has a row; every row has a place in the output. No item without an explanation, no explanation without an item.
- `out of scope` items need just one row labeled `out of scope: <reason>` — they do not need a full explanation, but must not vanish without a trace.
- Every numbered item/requirement in the spec/plan has a row with a disposition: **as planned** (with evidence), **deviated: <what differs>**, or **not yet done** + reason. Plan-vs-reality divergence must appear here and in layer 2.
- Merged items are still named; no "etc.", "...", or "and so on".
- Claims of "it works" or "verified" require evidence; without evidence, use `code-available:`.

**Done when:** the coverage map covers all Step 1 items (including `out of scope` ones) and all spec/plan items; every Step 1 symbol is explained; no entry is summarized away; no verification claim lacks evidence. Before closing this step, re-read the evidence already gathered **along the Step 1 path** — `git diff HEAD`, the commit range, `git diff --cached`, or direct file reads in a non-git case.

### Step 6 — Assess the business side

The trigger is a **process**, not a keyword in the code. Ask four things; in Moment A answer from the spec/plan contents, not from a diff that does not exist yet:

1. Is any behavior seen by a customer/operator/cashier changing?
2. Is any money amount, price, discount, tax, invoice, report, or metric changing?
3. Is any access, role, permission, or personal data changing?
4. Does any manual/operational process have to change too?

At least one "yes" → write a **Business Impact** block: the business process that changes, the actors involved, the decisions that can or cannot now be made, the reports/metrics that change too, operational risk + its mitigation.

None at all → write one line `No business impact: <reason>` (e.g. internal refactor, dependency version bump, helper rename).

**Done when:** every user-visible behavior has been translated into a business sentence, or the change is marked "No business impact" with a checkable reason; no actor/money/access claim lacks a basis in the code or spec.

### Step 7 — Write the three layers

Compose 3 → 2 → 1 (the material is already complete), present 1 → 2 → 3.

- **Layer 1 — ELI5:** at most five sentences, zero file names/symbols/technical terms, use everyday analogies. Answers: "what can now be done that could not before?"
- **Layer 2 — Within scope:** one to two paragraphs for the product owner: the problem solved, the capability limits, what is not included yet, side effects, what has not been verified, and **plan vs reality** (planned items that deviated or were not done).
- **Layer 3 — Per-feature detail:** all five parts — diagram (Step 2), user hands (Step 3), feature relations (Step 4), explanation + coverage map (Step 5), business impact (Step 6).

**Done when:** the three headings appear in order ELI5 → scope → detail; layer 1 is free of technical terms; layer 2 states the limits + what is unverified; every feature and file from Step 5 appears in layer 3.

### Step 8 — Self-check, then hand over

Narrow request (Moment C, e.g. only a diagram): tick only the requested part + one line offering the rest; all other items below are marked N/A — do not force them.

- [ ] Moment A: question sent and no output yet. Moment B/C: started without a gate question.
- [ ] Five parts present. Narrow Moment C: the requested part is complete + one line offering the rest (five parts not required).
- [ ] Three layers present and in order (N/A if not requested).
- [ ] Coverage map covers all Step 1 items (including `out of scope`) and all spec/plan items (N/A if not requested).
- [ ] Every file row has a status `planned:`/`code-available:`/`verified:` with its evidence.
- [ ] Every user hands step has type + place + impact (or the reason it is unknown) + verification; no invented commands.
- [ ] Every negative claim uses the bounded form + search command + scope.
- [ ] There is a Business Impact block or one line "No business impact" (N/A if not requested).
- [ ] The spec/plan path is referenced at the start of the explanation (N/A if there is no spec/plan).
- [ ] No TBD/TODO/"etc."; the `<value from you>` marker is only for input that really must come from the user.

Present in chat. Large output may be split into several coherent parts with explicit coverage markers (e.g. `Part 1/3`, the list of items that part covers) — never cut silently. Write to a file only if the user asks (e.g. a handover of the implementation delta); a conversation-summary request is the handoff skill's job.

## Template Output

### Template 1 — As-is / To-be (ASCII)

```
AS-IS                                TO-BE
+------------------+                 +-------------------+
| Entry: <...>     |                 | Entry: <...>      |
+--------+---------+                 +---------+---------+
         v                                     v
+------------------+                 +-------------------+
| file.ext    (~)  |                 | file.ext     (~)  |
+------------------+                 +---------+---------+
                                               v
                                     +-------------------+
                                     | new.ext      (+)  |
                                     +---------+---------+
                                               v
                                     +-------------------+
                                     | DB: column   (+)  |
                                     +-------------------+
```

Drawing rules: a box = a file/module with its real file name (not "service"/"layer"); arrows `v` and `-->` = data flow; columns are aligned so the difference is visible at a glance; one block per feature; >8 boxes → main path + merged boxes that point at the coverage map.

### Template 2 — User hands

````markdown
## User Hands (human hands)

Order is mandatory, do not skip a number.

1. **<step name>** — CLI, in <local|staging|production>
   ```
   <exact command from the repo>   (this block only if the command is readable from the repo)
   ```
   - Impact if skipped: <concrete symptom> | cannot be determined from the repo
   - Verification: `<command>` produces <expected result>

2. **<step name>** — <vendor name> dashboard, in staging + production
   - Setting: <setting name> = `<value from you>` (`source: not in repo`)
   - Impact if skipped: <symptom that can be inferred> | cannot be determined from the repo
   - Manual verification: <what the user sees>
````

### Template 3 — Feature relations (upstream, downstream, shared)

````markdown
## Feature Relations

Parent feature A: <name> (<path>)
  +-- A.c (NEW FEATURE C): <attachment point>  [<path:line>]
        |
        +-- Downstream (reads/writes A.c):
        |     +-- <consumer>  [<path:line>] -> <effect>          (direct)
        |     +-- Feature B: <name> -> INDIRECT IMPACT
        |           <mechanism: B reads A's output, which has now changed>  [<path:line>]
        |
        +-- Upstream (supplies/writes A.c):
        |     +-- <job/admin feature> [<path:line>] -> <effect on A.c>   (B -> A.c)
        |
        +-- Shared: <contract: column/config key/event/payload> -> owner <..>, users <..>

Negative: `git grep -n "<symbol>"` (whole repo, excluding generated files) -> no other consumers found within that scope.
  Not covered: <external clients/BI/jobs outside the repo> — not yet traced.
````

### Template 4 — Implementation explanation + coverage map

````markdown
### Feature: <name>

| File | Status | Symbols | What changed | Why | How to test |
|---|---|---|---|---|---|
| `path/file.ext` | `code-available:` | `Class::method` | <change> | <reason> | `<command>` |

Flow: <entry> -> <step> -> <effect>
Design decision: <choice> because <reason>; rejected alternative: <alternative>
Error handling: <failure condition> -> <behavior>

### Coverage map

| Item | Source | Status | Symbol / spec item | Output part |
|---|---|---|---|---|
| `path/file.ext` | unstaged | `code-available:` | `Class::method` | Layer 3 §<n> |
| `path/spec.md` item <n> | spec | `planned:` | — | Layer 3 §<n> |
````

## Example

Hypothetical example (numbers and paths are illustrations — not the result of a real repo). Change: the **per-item discount** feature (C) attaches to the **Cart** feature (A) to become `Cart.itemDiscount`. The **Tax/Invoice** feature (B) reads the cart total, so B is indirectly affected.

State in this example: the implementation is still in the working tree — `app/Cart.php` and `app/Http/CartController.php` are unstaged, the migration is untracked, the spec `docs/specs/item-discount.md` is untracked. (If the implementation were already committed and the working tree clean, the material would come from the commit range — see Step 1.)

```
AS-IS                  TO-BE
+-----------------+    +--------------------------+
| POST /cart      |    | POST /cart               |
+--------+--------+    +------------+-------------+
         v                          v
+-----------------+    +--------------------------+
| CartController  |    | CartController      (~)  |
| Cart::addItem   |    | pass discount_amount     |
|                 |    | (validation: not done)   |
+--------+--------+    +------------+-------------+
         v                          v
+-----------------+    +--------------------------+
| cart_items      |    | cart_items          (~)  |
| qty, price      |    | + discount_amount (+)    |
+--------+--------+    +------------+-------------+
         v                          v
+-----------------+    +--------------------------+
| Cart::total()   |    | Cart::total()       (~)  |
| sum(qty*price)  |    | sum(qty*price - disc)    |
+-----------------+    | cap from env             |
                       +--------------------------+
```

User hands (excerpt): `php artisan migrate` (`source: artisan exists in repo`; local→production, impact: the cart page errors on a missing column, verification: `migrate:status` → "Ran") and a dashboard step: add `MAX_ITEM_DISCOUNT` = `<value from you>` in the platform env (`source: not in repo`).

Coverage map (excerpt): `app/Cart.php` (unstaged, `verified:` after `php artisan test --filter=CartTest` passes) · `app/Http/CartController.php` (unstaged, `code-available:` — no test evidence yet) · `database/migrations/*_add_discount.php` (untracked, `code-available:`) · spec item 1 → **as planned** · spec item 2 (limit validation in the controller) → **not yet done**.

Relations (excerpt): downstream `Cart::total()` → `Tax::forCart()` [app/Tax.php:88] indirect; upstream `ImportPromo` writes `cart_items.discount_amount` [app/Jobs/ImportPromo.php:41] → `B -> A.c`; shared: `cart_items.discount_amount` is used by Cart, Tax, and the report export.

Business impact (excerpt): a per-item discount changes the tax base and the revenue report; actors: the cashier (can give a discount), finance (tax figures and reports drop by the discount amount).

Three layers: ELI5 "each item can carry a discount label like a price sticker on a shelf; tax is computed from what is actually paid" → scope (the limit comes from env, there is no UI or per-campaign rule yet, limit validation is not done) → detail (file table + coverage map).

## Gotchas

Everything below is stack-dependent. Establish it from the repo first; if it is not that stack, skip it — and never write commands that do not exist in the repo.

- **Laravel with cached config/env:** changes to `config/*` and `.env` are not picked up until the cache is cleared — only if the repo actually has `artisan` and its config is cached (e.g. `bootstrap/cache/config.php`) or the runbook/CI mentions it. Take the exact command from the repo/runbook, not from habit.
- **Env read at process start (Node dotenv, Python settings):** new values take effect after the process restarts; check `package.json`/`Procfile`/systemd unit for the right start command.
- **Long-running processes (queue worker, scheduler, container) hold old code** until restarted, even when the files on disk are new.
- **Migrations:** check backward compatibility and data constraints first (required vs nullable columns, defaults, backfill, old code versions still running) before proposing a release order; do not assume one pattern is safe for every case.
- **Historical data needs a backfill;** without it old reports look full of holes even though the column exists.
- **Frontend assets** only take effect after the build step runs; its location follows the pipeline/runbook (CI or server), not assumption — and only if the repo actually has a build script.
- **Some production platforms do not inject new env on restart** — new env sometimes needs a redeploy; that is a platform matter, not a repo command.
- **Webhooks, OAuth redirect URLs, DNS, and cron** usually need user access/permission or third-party dashboard configuration; this skill is read-only, so write them as user/dashboard steps without invented commands, and state which part can still be helped through code/doc changes.
- **Changes to the API response shape** involve external consumers (old mobile app versions) that do not deploy along with it.
- **Jobs already in the queue hold old payload versions;** payloads should be versioned so old jobs stay valid.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Concluding "no changes" because `git status` is empty | Check the commits: `git log --oneline -n 20` then `git show <sha>` |
| Using only `git diff` for material | `git diff HEAD` covers staged + unstaged; read `??` files directly |
| Counting `git status` lines as the number of files | Use `-uall`; a rename holds two paths (`old -> new`), a delete only one path (the old file) |
| Labeling working code `planned:` | Three statuses: `planned:` / `code-available:` / `verified:` + evidence |
| Treating `code-available:` as deployed or verified | `code-available:` only means the code exists in the repo; deployment and verification have their own statuses |
| Treating the plan contents as reality | Disposition per spec/plan item: as planned / `deviated:` / not yet done |
| Reading a deleted file from the working tree | Read the revision that contains it: `git show <baseline>:<path>` or the rename source; `HEAD:<path>` only if it still exists at HEAD |
| Running `git diff HEAD` / `git show HEAD:...` in a repo without commits | Repo without commits: `git diff --cached` + read working files; `HEAD` commands fail |
| Asking the user for a file list in a non-git repo when it can be explored | Check the spec/plan + file structure first; ask only if the baseline cannot be found |
| Asking for permission after the implementation is done | Moment B starts immediately; the gate is only in Moment A |
| Refusing to explain an unapproved spec when the user asks | The user's request = permission; explain it as decision material |
| Forcing all five parts for a narrow request | Do the requested part + offer the rest in one line |
| Writing commands/numbers/symbols that are not in the repo | Do not write the command at all — just the setting name + location + `source: not in repo`; unknown value → `<value from you>` |
| Running deploy/migrate/restart on the user's behalf | This skill builds the list; execution stays with the user |
| Business impact from a list of keywords in the code | Trigger on process: user behavior, money/reports, access/data, manual processes |
| Absolute claims "other features are safe" / "no consumers" | Use the bounded form: search command + scope + residual risk, or `not yet traced` |
| A full diagram for a large change | One block per feature; merged boxes that point at the coverage map |
| Copying the spec/plan into the output | The spec is material; the output is diagram + user hands + impact map + explanation + business |
| Saving the output to a file without being asked | Present in chat; write a file only if the user asks |
