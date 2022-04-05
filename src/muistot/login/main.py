from fastapi import FastAPI
from fastapi.responses import JSONResponse

description = """
    Login service for Muistojakartalla

    This is to make it easier to deploy a login server.
    """

tags = [{"name": "Common", "description": "All endpoints"}]

app = FastAPI(
    title="Muistoja Kartalla Login",
    description=description,
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    default_response_class=JSONResponse,
    openapi_tags=tags,
)
