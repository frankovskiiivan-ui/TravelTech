"""Логгер без внешних зависимостей."""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

_FMT = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
    datefmt="%H:%M:%S",
)


class _Logger:
    def __init__(self, name: str):
        self._log = logging.getLogger(name)
        if not self._log.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(_FMT)
            self._log.addHandler(handler)
            self._log.setLevel(logging.INFO)
            self._log.propagate = False

    def info(self, msg, *a, **kw): self._log.info(msg)
    def warning(self, msg, *a, **kw): self._log.warning(msg)
    def error(self, msg, *a, **kw): self._log.error(msg)
    def debug(self, msg, *a, **kw): self._log.debug(msg)


def get_logger(service_name: str):
    return _Logger(service_name)
