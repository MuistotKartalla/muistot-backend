from importlib import import_module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse, Response

from .config import Config
from .old import *
from .routes import *
from .security import *

app = FastAPI(
    title="Muitoja Kartalla",
    description="Backend for the https://www.muitojakartalla.fi service.",
    version="1.0.1",
    docs_url="/doc",
    root_path="/api",
    openapi_url=None,
    redoc_url=None,
    default_response_class=JSONResponse
)
app.include_router(default_paths)
app.include_router(old_router, deprecated=True)

for oauth_provider in Config.oauth:
    try:
        oauth_module = import_module(f".logins.{oauth_provider}")
        app.include_router(oauth_module.router)
    except Exception as e:
        import logging

        logging.getLogger("uvicorn.error").warning(f"Failed to load OAuth provider: {oauth_provider}", exc_info=e)

if not Config.testing:
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_methods=set()
    )
register_csrf_middleware(app)


@app.on_event("startup")
async def start_database():
    """
    Handle startup and database url parsing
    """
    from . import database
    await database.start()


@app.on_event("shutdown")
async def stop_database():
    """
    Handle shutdown and database resource release
    """
    from . import database
    await database.close()


@app.get("/login")
async def get_providers():
    return {"oauth-providers": [k for k in Config.oauth]}


EMPTY = Response(status_code=204)


@app.get("/refresh", status_code=204)
async def refresh():
    return EMPTY
