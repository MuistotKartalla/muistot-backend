from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

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
