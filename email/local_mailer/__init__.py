from .local import DefaultMailer


def get(**kwargs):
    return DefaultMailer(**kwargs)


__all__ = ["get"]
