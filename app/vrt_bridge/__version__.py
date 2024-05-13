# MIT License

from importlib.metadata import version, PackageNotFoundError

import logging


logger = logging.getLogger(__name__)


def get_running_version() -> str:
    try:
        return version(__package__)
    except PackageNotFoundError:
        return "dev"


__version__: str = get_running_version()
