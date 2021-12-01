from importlib import import_module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from .config import Config
from .errors import register_error_handlers, modify_openapi
from .logins import *
from .old import *
from .routes import *
from .security import *

app = FastAPI(
    title="Muitoja Kartalla",
    description="Backend for the https://www.muitojakartalla.fi service.",
    version="1.0.1",
    docs_url="/docs",
    # root_path="/api", # Doesn't work without proxy
    redoc_url=None,
    default_response_class=JSONResponse
)
app.include_router(default_paths)
app.include_router(old_router, deprecated=True)

register_error_handlers(app)

for oauth_provider in Config.oauth:
    try:
        oauth_module = import_module(f".logins.{oauth_provider}")
        app.include_router(oauth_module.router)
    except Exception as e:
        import logging

        logging.getLogger("uvicorn.error").warning(f"Failed to load OAuth provider: {oauth_provider}", exc_info=e)

app.include_router(default_login)

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


# This goes last
modify_openapi(app)
