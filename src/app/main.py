from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from .api import *
from .config import Config
from .errors import register_error_handlers, modify_openapi
from .logins import *
from .security import *

description = (
    """
    Backend for the https://www.muistojakartalla.fi service.
    
    
    Notes:
    - Image upload is handled as Base64 String at the moment
      => This might change to signed urls in the future
    """
)

tags = [
    {
        "name": "Common",
        "description": "Common unauthenticated endpoints without actual use"
    },
    {
        "name": "Projects",
        "description": "For viewing, creating, and managing Projects"
    },
    {
        "name": "Sites",
        "description": "CRUD for sites"
    },
    {
        "name": "Memories",
        "description": "User created memories"
    },
    {
        "name": "Comments",
        "description": "User comments"
    },
    {
        "name": "Admin",
        "description": "Administration utilities"
    }
]

app = FastAPI(
    title="Muistoja Kartalla",
    description=description,
    version="1.1.0",
    docs_url="/docs",
    # root_path="/api", # Doesn't work without proxy
    redoc_url=None,
    default_response_class=JSONResponse,
    openapi_tags=tags
)

# ERROR HANDLERS

register_error_handlers(app)

# START ROUTERS

app.include_router(common_paths)
app.include_router(api_paths)
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
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_methods={"GET", "POST", "PATCH", "PUT", "DELETE"},
        allow_headers=['*'],
        expose_headers=['*']
    )


    @app.middleware('http')
    async def timed(r, cn):
        from .logging import log
        from time import time_ns
        start = time_ns()
        try:
            return await cn(r)
        finally:
            log.info(f'{r.method} request to {r.url} took {(time_ns() - start) / 1E6:.3f} millis')


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
