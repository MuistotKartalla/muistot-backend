from fastapi import FastAPI
from fastapi.responses import JSONResponse

description = (
    """
    Mailer service for Muistojakartalla

    This is to make it easier to deploy a mailing server.
    """
)

tags = [
    {
        "name": "Common",
        "description": "All endpoints"
    }
]

app = FastAPI(
    title="Muistoja Kartalla Mailer",
    description=description,
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    default_response_class=JSONResponse,
    openapi_tags=tags
)


@app.post('/send')
def send_email():
    pass


@app.post('/validate')
def validate_email():
    pass
