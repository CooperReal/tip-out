from datetime import date
from pathlib import Path

import click

from tipout import __version__


@click.group()
def main():
    """Tip-out automation (Surfing Deer + Watersound)."""


@main.command()
def version():
    """Print tool version."""
    click.echo(__version__)


@main.command()
@click.option(
    "--period",
    "period_str",
    required=True,
    help="Pay period as 'YYYY-MM-DD:YYYY-MM-DD' (start:end inclusive, 14 days).",
)
@click.option(
    "--pos",
    "pos_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to POS daily workbook.",
)
@click.option(
    "--config",
    "config_path",
    default="config.yaml",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to config.yaml (default: ./config.yaml).",
)
@click.option(
    "--hours",
    "hours_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to Toast Time Clock CSV (optional). Populates per-employee Hours Worked + $/hr.",
)
@click.option(
    "--restaurant",
    type=click.Choice(["sd", "wvm"]),
    default="sd",
    show_default=True,
    help="Which restaurant's layout to parse. 'wvm' is summary-only (no --hours).",
)
def run(period_str, pos_path, config_path, hours_path, restaurant):
    """Append a pay-period tab to the 2-week summary workbook."""
    from tipout.config import Config
    from tipout.period import PayPeriod
    from tipout.runner import (
        DanglingAlias,
        L56Mismatch,
        UnresolvedHoursNames,
        UnresolvedNames,
    )
    from tipout.runner import (
        run as _run,
    )
    from tipout.wvm_parser import WvmFormatError

    if restaurant == "wvm" and hours_path is not None:
        raise click.UsageError("--hours is not supported with --restaurant wvm (summary only).")

    start_str, end_str = period_str.split(":", 1)
    period = PayPeriod.from_dates(date.fromisoformat(start_str), date.fromisoformat(end_str))
    cfg = Config.load(config_path)

    try:
        _run(cfg, pos_path, period, hours_path=hours_path, restaurant=restaurant)
    except UnresolvedNames as exc:
        unknowns_path = config_path.parent / "unknown_names.txt"
        unknowns_path.write_text("\n".join(exc.names) + "\n", encoding="utf-8")
        click.echo(
            f"Found {len(exc.names)} unknown name(s) in the POS file for this period.",
            err=True,
        )
        click.echo(f"List written to {unknowns_path}.", err=True)
        click.echo(
            "Open roster.xlsx in Excel, add each unknown name to either the "
            "Employees sheet (as a new canonical) or the Name Aliases sheet "
            "(pointing at an existing canonical). Then re-run.",
            err=True,
        )
        raise SystemExit(1) from exc
    except UnresolvedHoursNames as exc:
        unknowns_path = config_path.parent / "unknown_hours_names.txt"
        unknowns_path.write_text("\n".join(exc.names) + "\n", encoding="utf-8")
        click.echo(
            f"Found {len(exc.names)} unknown name(s) in the time clock CSV for this period.",
            err=True,
        )
        click.echo(f"List written to {unknowns_path}.", err=True)
        click.echo(
            "Open roster.xlsx in Excel, add each unknown name to either the "
            "Employees sheet (as a new canonical) or the Name Aliases sheet "
            "(pointing at an existing canonical). Then re-run.",
            err=True,
        )
        raise SystemExit(1) from exc
    except DanglingAlias as exc:
        click.echo(
            f"Roster has alias(es) pointing at a name not in Employees: {exc.names}. "
            "Fix roster.xlsx (run 'check-roster') and re-run.",
            err=True,
        )
        raise SystemExit(1) from exc
    except L56Mismatch as exc:
        click.echo(str(exc), err=True)
        click.echo(
            "The summary's daily total does not match the WVM sheet's own total — "
            "the file may be malformed for that day. No output written.",
            err=True,
        )
        raise SystemExit(1) from exc
    except WvmFormatError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc

    click.echo(f"Done. Pay period {period.start} to {period.end}. Wrote {cfg.summary_path}.")


@main.command()
@click.option(
    "--dir",
    "project_dir",
    default=".",
    type=click.Path(file_okay=False, path_type=Path),
    help="Project directory to scaffold (default: current directory).",
)
@click.option(
    "--from-summary",
    "summary_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Existing 2-week summary workbook to seed the roster from (optional).",
)
@click.option(
    "--anchor",
    "anchor",
    default="2025-12-29",
    help="Pay-period anchor date (a Monday that starts a known period). Default: 2025-12-29.",
)
@click.option(
    "--force", is_flag=True, default=False, help="Overwrite existing config.yaml / roster.xlsx."
)
def init(project_dir, summary_path, anchor, force):
    """Scaffold a fresh tipout project (config.yaml, roster.xlsx, output/)."""
    from tipout.bootstrap import RosterSnapshot, extract_roster_from_summary, write_roster

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(exist_ok=True)

    config_path = project_dir / "config.yaml"
    roster_path = project_dir / "roster.xlsx"

    existing = [p for p in (config_path, roster_path) if p.exists()]
    if existing and not force:
        names = ", ".join(p.name for p in existing)
        raise click.ClickException(
            f"{names} already exists in {project_dir}. Pass --force to overwrite."
        )

    config_path.write_text(
        f"# Tipout configuration. anchor_date must be a Monday that starts a known pay period.\n"
        f"anchor_date: {anchor}\n"
        f"roster_path: roster.xlsx\n"
        f"summary_path: output/summary.xlsx\n",
        encoding="utf-8",
    )

    if summary_path is not None:
        snapshot = extract_roster_from_summary(summary_path)
    else:
        snapshot = RosterSnapshot(employees={}, aliases={})
    write_roster(snapshot, roster_path)

    click.echo(
        f"Initialized tipout project in {project_dir} "
        f"({len(snapshot.employees)} employees, {len(snapshot.aliases)} aliases)."
    )


@main.command("bootstrap-roster")
@click.option(
    "--from-summary",
    "summary_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Seed the roster from an existing 2-week summary workbook.",
)
@click.option(
    "--from-wvm-daily",
    "wvm_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Seed the roster from a WVM daily worksheet (distinct names + role groups).",
)
@click.option(
    "--out",
    "out_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Where to write the new roster.xlsx.",
)
@click.option("--force", is_flag=True, default=False, help="Overwrite --out if it exists.")
def bootstrap_roster_cmd(summary_path, wvm_path, out_path, force):
    """Seed a roster.xlsx from an existing summary OR a WVM daily worksheet."""
    from tipout.bootstrap import (
        extract_roster_from_summary,
        extract_roster_from_wvm_daily,
        write_roster,
    )

    if bool(summary_path) == bool(wvm_path):
        raise click.UsageError("Pass exactly one of --from-summary or --from-wvm-daily.")
    if out_path.exists() and not force:
        raise click.ClickException(f"{out_path} already exists. Pass --force to overwrite.")

    if summary_path:
        snapshot = extract_roster_from_summary(summary_path)
    else:
        snapshot = extract_roster_from_wvm_daily(wvm_path)
    write_roster(snapshot, out_path)
    click.echo(
        f"Extracted {len(snapshot.employees)} employees, "
        f"{len(snapshot.aliases)} aliases. Wrote {out_path}."
    )


@main.command("check-roster")
@click.argument(
    "roster_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def check_roster_cmd(roster_path):
    """Validate a roster.xlsx for structural and semantic issues."""
    from tipout.validator import validate_roster

    issues = validate_roster(roster_path)
    if not issues:
        click.echo(f"{roster_path}: OK (no issues).")
        return

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    for i in errors:
        click.echo(f"  ERROR: {i.message}", err=True)
    for i in warnings:
        click.echo(f"  WARN:  {i.message}", err=True)

    click.echo(
        f"{roster_path}: {len(errors)} error(s), {len(warnings)} warning(s).",
        err=True,
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
