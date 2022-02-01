from fastapi import FastAPI

from .logic import *
from .providers import *


def register_login(app: FastAPI):
    app.include_router(default_login)
    app.include_router(email_login)
    register_oauth_providers(app)


__all__ = ['register_login']
