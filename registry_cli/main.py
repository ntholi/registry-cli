import click


@click.group()
def cli() -> None:
    """CLI tool with pull and push commands"""
    pass


@cli.command()
@click.argument("name", type=str)
def pull(name: str) -> None:
    """Pull command that displays 'pulling {name}...'"""
    click.echo(f"pulling {name}...")


@cli.command()
@click.argument("name", type=str)
def push(name: str) -> None:
    """Push command that displays 'pushing {name}...'"""
    click.echo(f"pushing {name}...")


if __name__ == "__main__":
    cli()
