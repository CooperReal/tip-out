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


@main.command()
@click.option("--period", "period_str", required=True,
              help="Pay period as 'YYYY-MM-DD:YYYY-MM-DD' (start:end inclusive).")
@click.option("--config", "config_path", default="config.yaml",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to config.yaml (default: ./config.yaml).")
@click.option("--pos", "pos_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to POS daily workbook.")
@click.option("--hours", "hours_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to hours workbook.")
def run(period_str, config_path, pos_path, hours_path):
    """Run a pay period end-to-end, producing summary + per-employee files."""
    from tipout.config import Config
    from tipout.period import PayPeriod
    from tipout.runner import run as _run

    start_str, end_str = period_str.split(":", 1)
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    period = PayPeriod.from_dates(start, end)

    cfg = Config.load(config_path)
    _run(cfg, pos_path, hours_path, period)
    click.echo(f"Done. Pay period {period.start} to {period.end}.")


if __name__ == "__main__":
    main()
