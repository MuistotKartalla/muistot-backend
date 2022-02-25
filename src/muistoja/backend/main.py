import os
import textwrap

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from .api import common_paths, api_paths
from ..config import Config
from ..errors import register_error_handlers, modify_openapi
from ..sessions import add_session_manager

description = textwrap.dedent(
    """
    Backend for the [Muistotkartalla](https://www.muistotkartalla.fi) service.
    
    General
    --------
    The API is fairly simple and easy to use. The common resources used in the project are:
    
    - User
    - Project
    - Site
    - Memory
    - Comment
    
    All model relations are described clearly by the URL convention.
    The content is safe to be cached, if any parent node is deleted all children can be assumed gone as well.
    This means that a project being deleted (or unpublished) will lead to all its children being deleted.
    
    Although the admin endpoint
    
    Auth
    ----
    The authentication and session management is handled by the backend server.
    The authentication model is very simple, a single user is tied to a single email address 
    and possibly multiple OAuth identities that can be used to initialize a session on the server side.
    
    The login flow is as follows:
    
    - Post a login request
    - An email will be sent
    - The email link will redirect to token exchange
    - A session is initialized
    
    OR:
    
    - Login via OAuth provider
    - OAuth provider redirects to token exchange
    - A session is initialized
    
    A session length is not fixed and has a maximum limit of inactivity.
    The session is extended for each authenticated request to the backend
    and an error response is returned in the event the session had expired.
    The session expiry is only possible through inactivity or session purging by the user/admin.
    
    #### Auth Errors
    
    If the session is expired a `403` code is returned. Similarly, if the session token is invalid an error is returned. 
    If an unauthenticated user is trying to access privileged endpoints a `401`is returned. 
    If the application is receiving `403` responses on `GET`requests to unprivileged endpoints, the only cause is the 
    auth token is invalid or expired and should be discarded. 
    
    Images
    ------
    Image upload is handled as Base64 String at the moment, but the implementation is planned to change to a more stable
    version in the future. The images are restricted to a subset of allowed formats (e.g. png, jpeg) that are checked
    after upload on the backend server. 
    The image format should be an ASCII base64 string using the standard base64 alphabet without any replacements.
    Error responses are returned if the image format is invalid, base64 or otherwise.
    Similarly, the returned image MIME type is dependent on the uploaded image.
    """
)

tags = [
    {"name": "Common", "description": "Common unauthenticated endpoints"},
    {"name": "Projects", "description": "For viewing, creating, and managing Projects"},
    {"name": "Sites", "description": "Site related operations"},
    {"name": "Memories", "description": "User created memories"},
    {"name": "Comments", "description": "User comments"},
    {"name": "Admin", "description": "Administrative utilities"},
    {"name": "Me", "description": "Authenticated user specific endpoints"},
]

app = FastAPI(
    title="Muistotkartalla",
    description=description,
    version="1.1.0",
    docs_url="/docs",
    redoc_url=None,
    default_response_class=JSONResponse,
    openapi_tags=tags,
    root_path=os.getenv("PROXY_ROOT", "")
)

# ERROR HANDLERS

register_error_handlers(app)

# START ROUTERS

app.include_router(common_paths)
app.include_router(api_paths)

# END ROUTERS


# START MIDDLEWARE
#
# THE ORDER IS VERY IMPORTANT
#
# Currently it works like adding layers to an onion.
# The latest gets executed first.


# This is a hack
add_session_manager(app)

if not Config.testing:
    app.add_middleware(CORSMiddleware, allow_methods=set())
    app.add_middleware(HTTPSRedirectMiddleware)
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods={"GET", "POST", "PATCH", "PUT", "DELETE"},
        allow_headers=["*"],
        expose_headers=["*"],
    )


    @app.middleware("http")
    async def timed(r, cn):
        from ..logging import log
        from time import time_ns

        start = time_ns()
        try:
            return await cn(r)
        finally:
            log.info(
                f"{r.method} request to {r.url} took {(time_ns() - start) / 1E6:.3f} millis"
            )


# END MIDDLEWARE


@app.on_event("startup")
async def start_database():
    """
    Handle startup and database url parsing
    """
    from ..database import connect
    await connect()


@app.on_event("shutdown")
async def stop_database():
    """
    Handle shutdown and database resource release
    """
    from ..database import disconnect
    await disconnect()


# LOGINS
from ..login import register_login

register_login(app)

# This goes last
# Modifies openapi definitions
modify_openapi(app)
