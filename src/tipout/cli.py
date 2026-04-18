import click

@click.group()
def main():
    """Surfing Deer tip-out automation."""

@main.command()
def version():
    """Print tool version."""
    from tipout import __version__
    click.echo(__version__)

if __name__ == "__main__":
    main()
