from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from .api import *
from .api_old import *
from .config import Config
from .errors import register_error_handlers, modify_openapi
from .logins import *
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

# ERROR HANDLERS

register_error_handlers(app)

# START ROUTERS

app.include_router(common_paths)
app.include_router(api_paths)
app.include_router(old_router, deprecated=True)

app.include_router(default_login)

# Add OAUTH
register_oauth_providers(app)

# END ROUTERS


# START MIDDLEWARE
#
# THE ORDER IS VERY IMPORTANT
#
# Currently it works like adding layers to an onion.
# The latest gets executed first.


register_csrf_middleware(app)
register_auth_middleware(app)

if not Config.testing:
    app.add_middleware(
        CORSMiddleware,
        allow_methods=set()
    )
    app.add_middleware(HTTPSRedirectMiddleware)


# END MIDDLEWARE


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


# This goes last
# Modifies openapi definitions
modify_openapi(app)
