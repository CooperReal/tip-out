# 01 — Agent Skills overview

**URL:** https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

## What this page is

The conceptual foundation for Agent Skills. Tells you what a skill is, what `SKILL.md` must look like, and how skills get loaded without blowing the context window. Start here.

## Core concept

A **Skill** is a filesystem directory containing instructions, optional scripts, and optional reference files. Claude loads parts of it on demand — this is called **progressive disclosure**.

Three loading levels:

| Level | What | When loaded | Cost |
|---|---|---|---|
| 1. Metadata | YAML frontmatter (`name`, `description`) | Always, at startup | ~100 tokens per skill |
| 2. Instructions | Body of `SKILL.md` | When the skill is triggered | < 5k tokens |
| 3. Resources | Other files in the skill dir (other `.md`, scripts, data) | Only if the SKILL.md body references them | Effectively unlimited |

So: the description is what makes Claude *decide* to invoke the skill; the body is the actual playbook; everything else is pulled in on demand via bash.

## `SKILL.md` required shape

```yaml
---
name: your-skill-name
description: What it does AND when Claude should use it.
---

# Your Skill Name

## Instructions
...

## Examples
...
```

**Field constraints (these matter — validation rejects otherwise):**

- `name`: max 64 chars; lowercase letters, numbers, hyphens only; cannot contain XML tags; cannot contain "anthropic" or "claude".
- `description`: max 1024 chars, non-empty, no XML tags. **Must say both what the skill does and when to use it** — this is the trigger text Claude matches against user intent.

## Surface compatibility

| Surface | Custom skills | Pre-built skills | Notes |
|---|---|---|---|
| Claude.ai | yes (zip upload) | yes (pptx, xlsx, docx, pdf) | Per-user, not org-shared. |
| Claude API | yes (Skills API upload) | yes | Workspace-wide. Requires beta headers. |
| Claude Code | yes (filesystem) | no | Personal `~/.claude/skills/` or project `.claude/skills/`; can also ship via a plugin. |

Skills **do not** sync across surfaces. A skill uploaded to claude.ai is not available in the API; claude.ai custom skills are per-user (no centralized admin management).

## Runtime constraints by surface

- **claude.ai:** variable network access depending on user/admin settings.
- **Claude API:** no network, no runtime package installs, only pre-installed packages from the code execution tool.
- **Claude Code:** full network access; packages should be installed locally, not globally.

## Where to find things on this page

| Need | Section on the page |
|---|---|
| Frontmatter rules for `SKILL.md` | "Skill structure" |
| Why my skill's not getting invoked | "Level 1: Metadata" — rewrite the description |
| How Claude actually reads the skill | "The Skills architecture" |
| What can safely live in the skill folder | "Level 3: Resources and code" |
| Which surface supports what | "Where Skills work" and "Limitations and constraints" |
| Security review checklist for an untrusted skill | "Security considerations" |
| Pre-built skill IDs (pptx, xlsx, docx, pdf) | "Available Skills" |
