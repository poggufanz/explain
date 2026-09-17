# skills

[![skills.sh](https://skills.sh/b/poggufanz/skills)](https://skills.sh/poggufanz/skills)

A collection of agent skills for coding harnesses. Each skill is a small,
self-contained folder that an agent discovers through its frontmatter
`description` and loads when the situation matches. This repo starts with
`explain`.

## Skills

| Skill | Path | What it does |
|---|---|---|
| `explain` | `skills/explain/` | Explains a single change after the spec/plan is written or after the implementation is done, so the user can run the manual steps themselves, verify the result, and understand the impact. |

Skill page: https://skills.sh/poggufanz/skills/explain

## Install

List what the repo offers, then install just the skill you want:

```bash
npx skills add poggufanz/skills --list
npx skills add poggufanz/skills --skill explain
```

## Layout

```text
.
├── README.md                 <- this file
├── LICENSE                   <- MIT
├── .gitignore
├── skills/
│   └── explain/              <- the skill package (installed as-is)
│       ├── SKILL.md
│       ├── README.md
│       └── CHANGELOG.md
└── evals/                    <- evaluation harness (NOT part of the skill package)
    ├── evals.json
    ├── run_evals.py
    └── results/
```

The installer copies the whole `skills/<name>/` directory. Evaluation harnesses
live at the repository root, outside the skill folder, so they are **not**
installed with the skill. Run results under `evals/results/` are kept as
evidence and are committed.

## Adding a new skill

A skill is just a folder: create `skills/<name>/SKILL.md` with `name` and
`description` frontmatter (the description is what the harness matches on), add
a row to the table above, and commit. A per-skill `README.md` and
`CHANGELOG.md` are optional but recommended. Put any evaluation harness in
`evals/` at the repository root, never inside the skill folder.

## License

MIT — see [LICENSE](LICENSE).
