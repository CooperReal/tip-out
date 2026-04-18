import json
import click
from datetime import date
from pathlib import Path


@click.group()
def main():
    """Surfing Deer tip-out automation."""


@main.command()
def version():
    """Print tool version."""
    from tipout import __version__
    click.echo(__version__)


def _write_pending_names(config_path: Path, names: list[str]) -> Path:
    """Write a pending_names.json next to the config file describing unresolved names."""
    path = config_path.parent / "pending_names.json"
    payload = {
        "status": "awaiting_input",
        "unresolved_names": sorted(names),
        "instructions": (
            "Create pending_answers.json in the same directory with one key per "
            "unresolved name. Each value: "
            "{decision: 'new_employee'|'alias'|'ignore', canonical_name: str, role: str}. "
            "Then re-run `tipout resolve-pending` followed by `tipout run`."
        ),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


@main.command()
@click.option("--period", "period_str", required=True,
              help="Pay period as 'YYYY-MM-DD:YYYY-MM-DD' (start:end inclusive).")
@click.option("--config", "config_path", default="config.yaml",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to config.yaml (default: ./config.yaml).")
@click.option("--pos", "pos_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to POS daily workbook.")
@click.option("--hours", "hours_path", required=False, default=None,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to hours workbook. Optional; omit for summary-only runs.")
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Emit structured JSON status (for automation like Cowork).")
def run(period_str, config_path, pos_path, hours_path, json_output):
    """Run a pay period end-to-end, producing summary + per-employee files."""
    from tipout.config import Config
    from tipout.period import PayPeriod
    from tipout.runner import run as _run, UnresolvedNames

    start_str, end_str = period_str.split(":", 1)
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    period = PayPeriod.from_dates(start, end)

    cfg = Config.load(config_path)
    if hours_path is None and not json_output:
        click.echo("Running summary-only (no hours provided).")
    try:
        run_id = _run(cfg, pos_path, hours_path, period)
    except UnresolvedNames as e:
        pending_path = _write_pending_names(config_path, e.names)
        if json_output:
            click.echo(json.dumps({
                "status": "awaiting_input",
                "reason": "unresolved_names",
                "unresolved_names": sorted(e.names),
                "pending_names_path": str(pending_path),
            }))
        else:
            click.echo(
                f"Awaiting input: {len(e.names)} unresolved name(s). "
                f"See {pending_path}.",
                err=True,
            )
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({
                "status": "error",
                "error_type": type(e).__name__,
                "message": str(e),
            }))
            raise SystemExit(2)
        raise

    if json_output:
        click.echo(json.dumps({
            "status": "success",
            "period": f"{period.start.isoformat()}:{period.end.isoformat()}",
            "run_id": run_id,
        }))
    else:
        click.echo(f"Done. Pay period {period.start} to {period.end}. run_id={run_id}")


@main.command("resolve-pending")
@click.option("--config", "config_path", default="config.yaml",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to config.yaml (default: ./config.yaml).")
def resolve_pending(config_path):
    """Apply operator decisions from pending_answers.json to the roster."""
    from tipout.config import Config
    from tipout.roster import load_roster
    from tipout.runner import IGNORE_SENTINEL
    from openpyxl import load_workbook

    cfg = Config.load(config_path)
    answers_path = config_path.parent / "pending_answers.json"
    if not answers_path.exists():
        click.echo(f"No pending_answers.json at {answers_path}", err=True)
        raise SystemExit(2)
    answers = json.loads(answers_path.read_text(encoding="utf-8"))

    roster = load_roster(cfg.roster_path)
    wb = load_workbook(cfg.roster_path)
    emp_ws = wb["Employees"]
    alias_ws = wb["Name Aliases"]

    # Track known canonicals so later `alias` decisions can reference
    # `new_employee` canonicals added earlier in the same batch.
    known_canonicals = set(roster.employees)

    for raw, decision in answers.items():
        kind = decision.get("decision")
        if kind == "new_employee":
            canonical = decision["canonical_name"]
            role = decision.get("role", "")
            emp_ws.append([canonical, role, None, None, ""])
            alias_ws.append([raw, canonical])
            known_canonicals.add(canonical)
        elif kind == "alias":
            canonical = decision["canonical_name"]
            if canonical not in known_canonicals:
                raise click.ClickException(
                    f"Alias decision for {raw!r} references unknown canonical {canonical!r}"
                )
            alias_ws.append([raw, canonical])
        elif kind == "ignore":
            alias_ws.append([raw, IGNORE_SENTINEL])
        else:
            raise click.ClickException(f"Unknown decision for {raw!r}: {kind!r}")

    wb.save(cfg.roster_path)
    (config_path.parent / "pending_names.json").unlink(missing_ok=True)
    answers_path.unlink()
    click.echo(f"Roster updated with {len(answers)} decision(s).")


@main.command("test")
@click.option("--fixture", "fixture_filter", default=None,
              help="Only run fixtures matching this name (substring match).")
def test_cmd(fixture_filter):
    """Run regression harness against all period fixtures."""
    from tipout.regression import list_fixtures, run_fixture

    fixtures = list_fixtures()
    if fixture_filter:
        fixtures = [f for f in fixtures if fixture_filter in f.name]
    if not fixtures:
        click.echo("No fixtures found.", err=True)
        raise SystemExit(2)

    failed = 0
    for fx in fixtures:
        click.echo(f"Running fixture: {fx.name}")
        diffs = run_fixture(fx)
        if not diffs:
            click.echo(f"  PASS")
        else:
            failed += 1
            click.echo(f"  FAIL ({len(diffs)} diffs):")
            for d in diffs[:20]:
                click.echo(f"    {d.sheet}!{d.cell}: expected={d.expected!r} actual={d.actual!r}")
            if len(diffs) > 20:
                click.echo(f"    ... {len(diffs) - 20} more")
    if failed:
        raise SystemExit(1)


@main.command("doctor")
@click.option("--config", "config_path",
              default="config.yaml",
              type=click.Path(path_type=Path),  # allow missing for a graceful 'fail' check
              help="Path to config.yaml (default: ./config.yaml).")
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Emit structured JSON status.")
def doctor_cmd(config_path, json_output):
    """Run preflight checks on the tipout installation and configuration."""
    from tipout.doctor import run_checks

    checks = run_checks(config_path)

    if json_output:
        click.echo(json.dumps({
            "status": "pass" if all(c.status == "pass" for c in checks) else (
                "warn" if all(c.status != "fail" for c in checks) else "fail"
            ),
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail}
                for c in checks
            ],
        }, indent=2))
    else:
        for c in checks:
            badge = {"pass": "[OK]  ", "warn": "[WARN]", "fail": "[FAIL]"}[c.status]
            click.echo(f"{badge} {c.name}: {c.detail}")

    overall_fail = any(c.status == "fail" for c in checks)
    if overall_fail:
        raise SystemExit(1)


@main.command("bootstrap-roster")
@click.option("--from-summary", "summary_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_path", required=True, type=click.Path(path_type=Path))
@click.option("--force", is_flag=True, default=False,
              help="Overwrite --out if it already exists.")
def bootstrap_roster_cmd(summary_path, out_path, force):
    """Seed a roster.xlsx from an existing 2-week summary workbook."""
    from tipout.bootstrap import extract_roster_from_summary, write_roster
    if out_path.exists() and not force:
        raise click.ClickException(
            f"{out_path} already exists. Pass --force to overwrite."
        )
    snapshot = extract_roster_from_summary(summary_path)
    write_roster(snapshot, out_path)
    click.echo(
        f"Extracted {len(snapshot.employees)} employees, "
        f"{len(snapshot.aliases)} aliases. Wrote {out_path}."
    )


if __name__ == "__main__":
    main()
