# 02 — Skills with the Claude API

**URL:** https://platform.claude.com/docs/en/build-with-claude/skills-guide

## What this page is

How to use skills programmatically via the Anthropic Messages API. Only relevant if we want the tipout skill (or any skill) driven from code, not from a Cowork/Claude Code session. For Cowork itself, this page is **not** the install path — see 06.

## TL;DR

1. Enable three beta headers on the request.
2. Enable the `code_execution_20250825` tool.
3. Pass a `container.skills` array (up to 8) with each entry's `type` (`anthropic` or `custom`), `skill_id`, and `version`.
4. Skills run in a sandboxed code-execution VM. Files they create come back as `file_id` refs — download via the Files API.

## Beta headers (all three required)

| Header | Purpose |
|---|---|
| `code-execution-2025-08-25` | The execution container |
| `skills-2025-10-02` | Skills feature |
| `files-api-2025-04-14` | Upload/download files to/from the container |

## Request shape

```json
{
  "model": "claude-opus-4-7",
  "max_tokens": 4096,
  "container": {
    "skills": [
      {"type": "anthropic", "skill_id": "pptx", "version": "latest"},
      {"type": "custom", "skill_id": "skill_01AbCd...", "version": "latest"}
    ]
  },
  "tools": [{"type": "code_execution_20250825", "name": "code_execution"}],
  "messages": [...]
}
```

Multi-turn: pass `container.id` from the previous response to reuse the same sandbox.

Long jobs: if `stop_reason == "pause_turn"`, resume by appending the assistant content and making another request with the same container id.

## Custom skill management (Skills API)

- **Create:** `client.beta.skills.create(display_title=..., files=files_from_dir("./my-skill"))` — uploads a directory that contains `SKILL.md`. Max **30 MB**.
- **List:** `client.beta.skills.list(source="custom"|None)`.
- **Retrieve:** `client.beta.skills.retrieve(skill_id=...)`.
- **Delete:** must delete all versions first, then the skill itself.

Skill IDs: custom skills come back as `skill_<24 chars>`. Anthropic-provided ones are short (`pptx`, `xlsx`, `docx`, `pdf`). Versions: date-based `YYYYMMDD` for Anthropic, epoch timestamp for custom; `latest` works for both.

## Important limits

| Limit | Value |
|---|---|
| Skills per request | 8 |
| Skill upload size | 30 MB |
| `name` field | ≤ 64 chars, lowercase alphanumeric + hyphens |
| `description` field | ≤ 1024 chars |
| ZDR eligibility | **Not eligible** — standard retention only |

## Sharing model

Custom skills uploaded via the API are **workspace-wide** — every workspace member can use them.

## Where to find things on this page

| Need | Section on the page |
|---|---|
| Minimum request body that actually works | "API Request Shape" |
| How to reuse a container across turns | "Multi-Turn with Container Reuse" |
| Pulling generated files out of a response | "File Management" / `extract_file_ids` example |
| Pagination/listing uploaded skills | "Listing Skills" |
| Deleting a skill cleanly | "Deleting a Skill" |
| Handling long-running skill work | "Long-Running Operations" / `pause_turn` |
