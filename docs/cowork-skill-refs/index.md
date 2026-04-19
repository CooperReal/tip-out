# Cowork / Skills reference index

Canonical sources you hand me when we're designing or building a skill/plugin for Claude Cowork. Each numbered file below is a writeup of one source: what it covers, the key facts I pulled out, and "look here when you need X".

Read order if you're new:

1. [01 — Agent Skills overview](01-agent-skills-overview.md) — what a skill *is*, SKILL.md format, progressive disclosure.
2. [04 — anthropics/skills repo](04-anthropic-skills-repo.md) — concrete examples to copy from.
3. [03 — Plugins reference](03-plugins-reference.md) — how to wrap skills as an installable plugin (this is the packaging story for Cowork).
4. [06 — Plugins in Cowork](06-use-plugins-in-cowork.md) — the user-side install UX in Cowork.
5. [05 — Skills in Claude (claude.ai)](05-use-skills-in-claude.md) — user-side UX for plain claude.ai (zip upload path).
6. [02 — Skills with the API](02-skills-with-api.md) — only relevant if we also want API-driven skill usage.

## Where each source lives

| # | Source | URL |
|---|---|---|
| 01 | Agent Skills overview | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview |
| 02 | Skills with the Claude API | https://platform.claude.com/docs/en/build-with-claude/skills-guide |
| 03 | Plugins reference (Claude Code) | https://code.claude.com/docs/en/plugins-reference |
| 04 | Example skills repo | https://github.com/anthropics/skills |
| 05 | Using Skills in Claude (product-side) | https://support.claude.com/en/articles/12512180-use-skills-in-claude |
| 06 | Plugins in Claude Cowork | https://support.claude.com/en/articles/13837440-use-plugins-in-claude-cowork |

## One-line mental model

- **Skill** = a folder with `SKILL.md` (YAML frontmatter + instructions) that Claude reads on demand.
- **Plugin** = a bundle that can ship one or more skills plus agents/hooks/MCP/LSP/monitors, installed via marketplace or local path.
- **Cowork** = the Claude Desktop "Cowork" tab; installs plugins from a marketplace UI and exposes their skills via `/` or the `+` button in a session.
- For this repo, `skills/tipout/SKILL.md` already exists as a standalone skill. Shipping it to Cowork means wrapping it in a plugin and publishing to a marketplace (or having users install locally).
