# 05 — Using Skills in Claude (product-side, claude.ai)

**URL:** https://support.claude.com/en/articles/12512180-use-skills-in-claude

## What this page is

End-user documentation for how skills appear and get installed inside the **claude.ai** web product (not Cowork — see 06 for Cowork specifically). Useful when we need to tell a non-technical operator how to use a skill we ship, and for understanding the zip-upload path.

## Prereqs on the user's side

- **Code execution** must be enabled first.
  - Free / Pro / Max: Settings → Capabilities → toggle "Code execution and file creation."
  - Team / Enterprise: an Owner must enable both "Code execution and file creation" AND "Skills" in Organization settings → Skills.
- Then: Customize → Skills → toggle individual skills on/off.

## Built-in vs. custom — the two flows

### Built-in Anthropic skills (pptx, xlsx, docx, pdf)

- No install step. They activate the moment Skills is enabled.
- Claude picks them up contextually when the user asks for a document.

### Custom user-uploaded skills

1. Customize → Skills.
2. Click `+` → `+ Create skill` → `Upload a skill`.
3. Upload a **ZIP** of the skill folder. Folder must contain a **`SKILL.md`**.
4. Skill appears in the list, can be toggled on/off.

Common upload-failure reasons:
- ZIP is too large.
- Folder name doesn't match skill name.
- `SKILL.md` missing.
- Invalid characters in name/description.

### Org-shared skills (Team/Enterprise, from a directory)

1. Customize (left sidebar) → `+` → Skills tab.
2. Find the skill in the org directory → click **Install**.

## Sharing model

- Custom skills default to **private to the uploader**.
- To share: Customize → Skills → open a skill → **Share**.
  - Specific people: enter names/emails. They see the skill greyed out until they enable it.
  - Whole org: publishes to the organization directory (Owner toggle required).
- Shared skills are **view-only** for recipients. They cannot edit but automatically pick up updates.

## Org/permission matrix

| Plan | Who controls enablement | Can share org-wide |
|---|---|---|
| Free / Pro / Max | Self | No |
| Team | Org (enabled by default) | Yes, if peer-sharing toggle on |
| Enterprise | Owner via Org settings | Owner |

## Skills list categories (Team/Enterprise UI)

- **Personal** — you created/uploaded.
- **Shared** — a colleague shared (greyed out until you toggle on).
- **Organization** — org-wide or provisioned skills you can install from the directory.

## Where to find things on this page

| Need | Section |
|---|---|
| Step-by-step for an end user installing a zip | "Installation Flow → For custom user-uploaded skills" |
| Why my upload fails | "File Format Requirements" |
| Sharing a skill with one person vs. whole org | "Sharing Skills" |
| Permission differences across plans | "Organizational/Permission Considerations" |
| Deleting a skill | Screenshot note near the end — `...` menu → Delete |
