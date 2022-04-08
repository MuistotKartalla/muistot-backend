from .local import LocalMailer
from .server import ServerMailer
from .zoner import ZonerMailer

DRIVERS = {
    "local": LocalMailer,
    "smtp": LocalMailer,
    "server": ServerMailer,
    "zoner": ZonerMailer,
}


def get(*, driver: str = "smtp", **kwargs):
    return DRIVERS[driver](**kwargs)


__all__ = ["get"]
