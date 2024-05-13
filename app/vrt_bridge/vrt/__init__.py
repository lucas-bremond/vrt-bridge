# MIT License

import os
import logging
import logging.config

from vrt_bridge.vrt.packet import Packet
from vrt_bridge.vrt.__version__ import __version__

__all__ = [
    "Packet",
    "__version__",
]

logging_config: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": os.getenv("VITA_VRT_LOG_LEVEL", default="DEBUG"),
            "formatter": "classic",
            "stream": "ext://sys.stderr",
        },
    },
    "formatters": {
        "classic": {
            "format": "%(asctime)s | %(levelname)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "loggers": {
        __name__: {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

logging.config.dictConfig(logging_config)
