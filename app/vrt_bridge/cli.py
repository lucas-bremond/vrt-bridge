# MIT License

import yaml

import click

from .main import main
from .__version__ import __version__


@click.command(no_args_is_help=True)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="Configuration file.",
)
@click.version_option(__version__)
def cli(config: str) -> None:
    configuration: dict
    with open(config) as file_stream:
        configuration = yaml.load(file_stream, Loader=yaml.FullLoader)

    main(configuration)


if __name__ == "__main__":
    cli()
