from .server import ServerMailer
from .zoner import ZonerMailer

DRIVERS = {
    "smtp": ZonerMailer,
    "server": ServerMailer,
    "zoner": ZonerMailer,
}


def get(*, driver: str = "smtp", **kwargs):
    return DRIVERS[driver](**kwargs)


__all__ = ["get"]
