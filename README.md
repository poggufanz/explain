# explain

A skill that explains a single change after the spec/plan is written or after the
implementation is done, so the user can run the manual steps themselves, verify the
result, and understand the impact.

This repository holds one skill:

| Skill | Path | What it does |
|---|---|---|
| `explain` | `skills/explain/` | Produces five sections (as-is/to-be diagrams, the user's hands, feature relationships, implementation + coverage map, business impact) with evidence status per item. Read-only: it composes manual steps, it does not execute them. |

## Layout

```text
.
├── README.md                 <- this file
├── LICENSE
├── .gitignore
├── skills/
│   └── explain/              <- the skill package
│       ├── SKILL.md
│       ├── README.md
│       └── CHANGELOG.md
└── evals/                    <- evaluation harness (NOT part of the skill package)
    ├── evals.json
    ├── run_evals.py
    └── results/
```

`evals/` lives at the repository root on purpose. The installer copies the whole
`skills/explain/` directory, so the evaluation harness and its run results are kept
outside the skill folder and are **not** installed with the skill. Results under
`evals/results/` are kept as evidence and are committed.

## Install

Replace `<owner>` and `<repo>` with the GitHub owner and repository name:

```bash
npx skills add <owner>/<repo> --list
npx skills add <owner>/<repo> --skill explain
```

## Badge

Replace `<owner>` and `<repo>` as above:

```markdown
[![skills.sh](https://skills.sh/b/<owner>/<repo>)](https://skills.sh/<owner>/<repo>)
```
