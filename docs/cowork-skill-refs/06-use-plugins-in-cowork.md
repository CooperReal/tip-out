# 06 — Plugins in Claude Cowork

**URL:** https://support.claude.com/en/articles/13837440-use-plugins-in-claude-cowork

## What this page is

End-user doc for installing and using **plugins** inside Claude Cowork (the Cowork tab of the Claude Desktop app). This is how our tipout skill actually reaches an operator in Cowork: wrapped in a plugin, installed from a marketplace or a local file.

## Install flow (verbatim steps)

1. Open Claude Desktop, switch to the **Cowork** tab.
2. Click **Customize** in the left sidebar.
3. Click **Browse plugins** to open the plugin modal.
4. Click **Install** on the plugin you want.
5. Or upload a custom plugin file (if you built one locally or got one from a colleague).

After install, the plugin is **saved locally to the user's machine**.

## How the plugin's skills surface in a session

Once installed, during any Cowork session:

- Type `/` — lists available skills.
- Or click the `+` button — same list, graphical entry.

Each installed plugin contributes its skills to this menu.

## Personal vs. organization-managed plugins

| Type | Source | User can edit? | User can uninstall? |
|---|---|---|---|
| Personal | Self-installed | Yes | Yes |
| Org-managed (auto-install) | Pushed by org | No | Yes |
| Org-managed (required) | Pushed by org | No | **No** |

Required plugins enforce consistent team tooling and can't be removed by the user.

## Security & permissions

- Plugins can bundle **local MCP servers** that run on the user's machine with "the same permissions as any other program you run." → "Only install plugins from sources you trust."
- **Connectors** (different concept) reach external services through Anthropic's cloud and need public internet access.
- Enterprise admins can **restrict plugin installation** org-wide.

## What the page doesn't tell you

- No explicit update/upgrade flow. (Claude Code CLI has `claude plugin update`; Cowork docs don't spell out the equivalent.)
- No marketplace URL beyond referencing Anthropic's own knowledge-work-plugins GitHub collection.

## Related building blocks

- Plugin format is the same as Claude Code's — see [03-plugins-reference.md](03-plugins-reference.md).
- The official knowledge-work plugin collection: `github.com/anthropics/knowledge-work-plugins`.
- Building a custom plugin from inside Cowork: Anthropic ships a built-in "Plugin Create" helper plugin.

## Where to find things on this page

| Need | Section |
|---|---|
| Where a user clicks to install | "Installation Flow" |
| How an installed skill gets invoked in a session | "Calling Plugin Skills in Sessions" |
| Whether a user can uninstall a required plugin | "Personal vs. Team/Organization Plugins" |
| Security posture / MCP warning | "Permissions & Consent" |
