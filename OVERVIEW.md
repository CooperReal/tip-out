# Tip-Out Spreadsheets — Overview

This folder holds the working tip-out spreadsheets for two restaurants:

- **Surfing Deer (SD)** — dinner-only, single shift per day.
- **Village Market at Watersound (WVM)** — split AM and PM shifts, so its layout is different.

The files form a small pipeline. Numbers are entered once on the daily worksheet, and every other report is downstream of that.

---

## File 1 — `2026 SD Daily Tipout Worksheet.xlsx` *(source of truth)*

The day-by-day cash and credit-card tip-out for Surfing Deer. Everything else in this folder is rolled up from this file.

- One **tab per workweek** (Mon–Sun), 16 weeks so far for 2026, plus a `Bank Master` template tab and an empty `Sheet1`.
- Each weekly tab is laid out as **seven day-blocks** side-by-side. Each block has roughly:
  - Header: `Date`, day of week.
  - Columns per worker: `CC Tips`, `Party`, `Cash RCP`, `SA Tip Out`, `Bar Tipout`, `Total Tip Out`, `Barback`, `Bartender`, `Net Tip`.
  - Servers/bartenders are listed first; below them are support roles (food runners, hosts, SA / service assistants, expo, "Xen" staff) who receive an allocated cut.
- The `Bank Master` tab is the blank template (PM tip-out / cash deposit / cash POS reconciliation block) that gets copied to make each new weekly tab.

This is where someone hand-keys numbers from the POS each shift. **If the totals here are wrong, every other report is wrong.**

## File 2 — `2026 SD 2 WK Tip Summary By employee.xlsx` *(payroll report)*

Bi-weekly pay-period summary, one row per employee, one column per day across 14 days, with a total in the right-most column.

- One **tab per pay period** (eight pay periods so far: 12.29 → 04.19).
- Column A is the canonical employee name; column B is whatever name spelling appeared on the daily sheet (so misspellings can be tracked back).
- The number in each daily cell is that employee's **Net Tip** for that day, pulled from File 1.
- Row near the bottom totals each day across all employees; the right-most column totals each employee across the whole pay period.

**Purpose (your words):** used to run payroll and to confirm "tips payable" matches what the POS reports for the same period.

## File 3 — `Yvonne.xlsx` *(per-employee statement — example)*

A per-employee, per-pay-period statement. `Yvonne.xlsx` is one example; the same template would exist for every tipped employee.

- One **tab per pay period** (`Yvonne 12.29 to 01.11.2026`, etc.).
- Columns: `Date`, `Hours Worked`, `CC Tips`, `SA Tip Out`, `Bar Tipout`, `Total Tip Out`, `Serv As`, `Bartender`, `Net Tip`. "Party" days (large private events) are flagged in column J.
- Bottom row totals each column for the pay period.
- A separate row (R23) divides total Net Tip by Hours Worked to give an **effective $/hour** for the period (Yvonne is running ~$33–$41/hr).

**Purpose (your words):** if an employee questions their tips, send them their sheet so they can see exactly what they were paid each shift and why.

## File 4 — `2026 WVM Daily Tip out Worksheet.xlsx` *(Watersound — different layout)*

Same idea as File 1, but Watersound runs AM and PM service, so the layout had to change.

- One **tab per day** (not per week) — 113 daily tabs covering 12.29.25 through 04.19.26.
- Each day's tab groups workers by **role**: `WAIT AM`, `BARTNDR`, `HOST`, `SA`, `F Runner`, `To Go`.
- Tip columns are split into AM and PM:
  - `AM CC Tips` / `PM CC TIPS`
  - `AM STAFF TIP OUT` / `PM STAFF TIP OUT`
  - `AM Bar Tipout` / `PM BAR TIPOUT`
  - then `Total Tip Out`, `Serv As`, `Bartender`, `Net tip`
- The downstream by-employee, by-month, and by-year reports for WVM follow the same shape as the SD reports — only this front-end daily worksheet is shaped differently.

---

## How the files relate

```
                                    (hand-entered from POS, daily)
                                                │
                            ┌───────────────────┴───────────────────┐
                            ▼                                       ▼
            SD Daily Tipout Worksheet                 WVM Daily Tip out Worksheet
                  (week per tab)                            (day per tab,
                                                          AM + PM columns)
                            │                                       │
                            └───────────────────┬───────────────────┘
                                                ▼
                         ┌────────────────────┬─┴──────────────────────────┐
                         ▼                    ▼                            ▼
               2 WK Tip Summary       Per-employee sheet            Monthly + Yearly
               by Employee            (e.g. Yvonne.xlsx)            tip totals per
               (payroll + POS         (sent on request to           employee
               reconciliation)        the employee)                 (not in this folder yet)
```

## What I think we're doing

You're maintaining the books for tipped staff at two restaurants. The daily worksheet is the system of record where each shift's CC tips, cash, and tip-out math gets entered. From that one source you generate:

1. A **bi-weekly payroll-facing report** that has to tie out to the POS before tips are paid.
2. **Per-employee statements** so any individual can be shown their own numbers if they ask.
3. **Monthly and yearly per-employee rollups** for higher-level tracking (mentioned but not in this folder yet).

The only structural difference between the two restaurants is the front-end daily file: WVM splits AM and PM because Watersound has two services per day, while Surfing Deer is single-service so a week fits on one tab. Everything downstream of that front-end is the same shape.

## Things worth noting / potential cleanup

- **Name normalization.** Daily sheets have inconsistent spellings (Krista / Kristin / Kristine; Doug / Dug; Corandoh / Coandoh / Corandah; Yvonne / Yvonne Lew; "Sjuitra" vs "Sujitra"; "Andrew Nieta (Xen)" vs "Andrew Neita (Xen)"). The 2-week summary already maps these to a canonical name in column A — that mapping is the closest thing to an employee master list right now.
- **Tab naming has trailing spaces** in many tabs (e.g. `'01.12 to 01.18.2026 '`). Harmless for humans, but anything that looks up tabs by name will need to handle them.
- **WVM has 113 tabs and growing** — at 365 tabs/year this will get unwieldy. Likely worth eventually consolidating into a per-month or per-week sheet structure.
- **One stray `Sheet1`** in the SD daily file is empty and can probably be deleted.
