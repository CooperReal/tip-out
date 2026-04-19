# 03 — Plugins reference (Claude Code)

**URL:** https://code.claude.com/docs/en/plugins-reference

## What this page is

The exhaustive spec for the Claude Code plugin format: directory layout, `plugin.json` schema, the components a plugin can ship, and the CLI to install/enable/disable. **This is the packaging format Cowork uses too** — the install UX differs, but the on-disk format is the same.

## What a plugin can contain

A plugin is a self-contained directory. Components auto-discovered from default paths; override paths in `plugin.json` if needed.

| Component | Default path | Purpose |
|---|---|---|
| Skills | `skills/<name>/SKILL.md` | The thing we care about for tipout. |
| Commands | `commands/*.md` | Flat-file skills (older style). |
| Agents | `agents/*.md` | Subagents with frontmatter (`name`, `description`, `model`, `tools`, etc.). |
| Hooks | `hooks/hooks.json` | Event handlers (PostToolUse, SessionStart, etc.). |
| MCP servers | `.mcp.json` | Ship MCP servers with the plugin. |
| LSP servers | `.lsp.json` | Language servers for code intelligence. |
| Monitors | `monitors/monitors.json` | Background processes that pipe stdout as notifications. |
| Executables | `bin/` | Added to `PATH` inside Bash tool calls. |

## Minimum viable plugin layout

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # metadata (optional — name is derived from dir if omitted)
└── skills/
    └── my-skill/
        └── SKILL.md
```

**Critical:** everything except `plugin.json` lives at the **plugin root**, not inside `.claude-plugin/`. Putting `skills/` inside `.claude-plugin/` is a common mistake and components will silently not load.

## `plugin.json` manifest (only `name` is strictly required)

```json
{
  "name": "plugin-name",
  "version": "1.2.0",
  "description": "...",
  "author": {"name": "...", "email": "...", "url": "..."},
  "homepage": "...",
  "repository": "...",
  "license": "MIT",
  "keywords": ["..."],
  "skills": "./custom/skills/",
  "commands": ["./custom/cmd.md"],
  "agents": "./custom/agents/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "lspServers": "./.lsp.json",
  "monitors": "./monitors.json",
  "userConfig": { "api_token": {"description": "...", "sensitive": true} },
  "dependencies": [{"name": "helper", "version": "~2.1.0"}]
}
```

**`userConfig`** lets the plugin prompt for config at install time. Keys are referenced as `${user_config.KEY}` in MCP/LSP/hook/monitor configs. Sensitive values go to the OS keychain.

Version bumps matter: Claude Code caches plugins, so if you change code without bumping `version`, users won't see changes.

## Installation scopes

| Scope | Settings file | Use |
|---|---|---|
| `user` | `~/.claude/settings.json` | Default. Personal, across projects. |
| `project` | `.claude/settings.json` | Team, committed. |
| `local` | `.claude/settings.local.json` | Per-project, gitignored. |
| `managed` | Managed settings | Read-only org-provisioned. |

## Path substitution variables

Available in MCP/LSP/hook/monitor commands and skill/agent content:

- `${CLAUDE_PLUGIN_ROOT}` — absolute path of installed plugin. **Resets on update** — don't write persistent state here.
- `${CLAUDE_PLUGIN_DATA}` — persistent dir that survives updates (`~/.claude/plugins/data/<id>/`). Use for `node_modules`, caches, etc.
- `${user_config.KEY}` — from `userConfig`.
- `${ENV_VAR}` — any shell env var.

## CLI cheat sheet

```bash
claude plugin install <plugin>[@marketplace] [--scope user|project|local]
claude plugin uninstall <plugin> [--keep-data]
claude plugin enable <plugin>
claude plugin disable <plugin>
claude plugin update <plugin>
claude plugin list [--json] [--available]
```

## Debugging checklist

- `claude --debug` shows plugin load trace.
- `claude plugin validate` (or `/plugin validate`) catches manifest/frontmatter/JSON errors.
- Script not firing → `chmod +x`, check shebang, use `${CLAUDE_PLUGIN_ROOT}` for paths.
- Skills missing → components at **plugin root**, not in `.claude-plugin/`.

## Where to find things on this page

| Need | Section |
|---|---|
| Full manifest schema | "Plugin manifest schema → Complete schema" |
| What fields a shipped agent can set (security-restricted) | "Agents" — notes on `hooks`/`mcpServers`/`permissionMode` being disallowed |
| Cache/update semantics, why my edits don't show | "Plugin caching and file resolution" + "Version management" warning |
| Background monitor format | "Monitors" |
| Variable substitution reference | "Environment variables" |
| Common "nothing loads" bugs | "Directory structure mistakes" |
