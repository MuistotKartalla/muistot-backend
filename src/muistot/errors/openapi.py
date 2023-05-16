from fastapi import FastAPI
from pydantic.schema import schema

from .models import *


def modify_openapi(app: FastAPI):
    # BECAUSE Fastapi does this on first request only
    if app.root_path is not None and app.root_path != "":
        app.servers.insert(0, {"url": app.root_path})

    openapi = app.openapi()
    openapi["components"]["schemas"].update(
        schema([HTTPValidationError], ref_prefix="#/components/schemas/")[
            "definitions"
        ]
    )

    app.openapi_schema = openapi
