import os

import click
from config import load_config, find_config
from install.command import install


@click.group()
@click.option('--config',
              type=click.Path(exists=True),
              help='Path to config file. If none is given assumes config file is in current directory.')
@click.pass_context
def cli(ctx, config):
    if config:
        ctx.obj = load_config(config)
    else:
        click.echo('No config file given. Looking for config file in current directory.')
        ctx.obj = find_config(os.getcwd())

@cli.command()
@click.pass_context
def uninstall(ctx):
    print(ctx.obj)


@cli.command()
@click.pass_context
def update(ctx):
    pass


@cli.command()
@click.pass_context
def services(ctx):
    pass

cli.add_command(install)


if __name__ == '__main__':
    cli()
