from fastapi import FastAPI

from .logic import *
from .providers import *


def register_login(app: FastAPI):
    register_default_providers(app)
    register_oauth_providers(app)


__all__ = ["register_login"]
