# 04 — anthropics/skills repo

**URL:** https://github.com/anthropics/skills

## What this repo is

Anthropic's public reference collection of example skills. Treat this as the **copy-paste source** when authoring a new skill — real, working examples of SKILL.md frontmatter, bundled scripts, and reference docs.

## Repo layout

```
anthropics/skills/
├── .claude-plugin/           # makes the repo installable as a plugin marketplace
├── skills/
│   ├── docx/                 # source-available, production-grade
│   ├── pdf/
│   ├── pptx/
│   ├── xlsx/
│   └── <others>              # creative / technical / enterprise examples
├── spec/                     # Agent Skills spec
├── template/                 # minimal skill template to copy
├── README.md
└── THIRD_PARTY_NOTICES.md
```

Categories of examples (from README): **Creative & Design**, **Development & Technical**, **Enterprise & Communication**, plus the four **Document Skills** (pdf/docx/pptx/xlsx).

## Skill skeleton they recommend

```
my-skill/
├── SKILL.md
└── [optional assets / scripts / reference .md]
```

**`SKILL.md`:**

```yaml
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[instructions Claude should follow when this skill is active]

## Examples
- ...

## Guidelines
- ...
```

## How to install the whole repo as a marketplace

In Claude Code:

```bash
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
/plugin install example-skills@anthropic-agent-skills
```

Or via claude.ai: paid-plan users already have the document skills; custom skills are uploaded as ZIPs in the UI.

## License

- Most skills: **Apache 2.0**.
- Document skills (`docx`, `pdf`, `pptx`, `xlsx`): **source-available**, not open source. Don't redistribute as your own.

## Where to look when you need X

| Need | Where to look in the repo |
|---|---|
| A minimal starting template | `template/` |
| A production-quality skill to study | `skills/pdf/`, `skills/xlsx/` |
| How to bundle executable scripts next to SKILL.md | any document skill, e.g. `skills/pdf/scripts/` |
| How to structure the top-level `.claude-plugin/` for a marketplace | repo root `.claude-plugin/` |
| Authoring rules not on the docs pages | `spec/` |

**Disclaimer from the README:** examples are for demonstration/education — always test before production.
