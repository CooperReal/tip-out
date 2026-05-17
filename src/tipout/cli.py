from datetime import date
from pathlib import Path

import click

from tipout import __version__


@click.group()
def main():
    """Surfing Deer tip-out automation."""


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
def run(period_str, pos_path, config_path, hours_path):
    """Append a pay-period tab to the 2-week summary workbook."""
    from tipout.config import Config
    from tipout.period import PayPeriod
    from tipout.runner import run as _run, UnresolvedNames, UnresolvedHoursNames

    start_str, end_str = period_str.split(":", 1)
    period = PayPeriod.from_dates(date.fromisoformat(start_str), date.fromisoformat(end_str))
    cfg = Config.load(config_path)

    try:
        _run(cfg, pos_path, period, hours_path=hours_path)
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
        raise SystemExit(1)
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
        raise SystemExit(1)

    click.echo(f"Done. Pay period {period.start} to {period.end}. Wrote {cfg.summary_path}.")


@main.command("bootstrap-roster")
@click.option(
    "--from-summary",
    "summary_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to an existing 2-week summary workbook to harvest names from.",
)
@click.option(
    "--out",
    "out_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Where to write the new roster.xlsx.",
)
@click.option("--force", is_flag=True, default=False, help="Overwrite --out if it exists.")
def bootstrap_roster_cmd(summary_path, out_path, force):
    """Seed a roster.xlsx from an existing 2-week summary workbook."""
    from tipout.bootstrap import extract_roster_from_summary, write_roster

    if out_path.exists() and not force:
        raise click.ClickException(f"{out_path} already exists. Pass --force to overwrite.")
    snapshot = extract_roster_from_summary(summary_path)
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
