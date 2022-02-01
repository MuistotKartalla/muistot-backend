from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .parse import parse_file
from ..core.errors import modify_openapi, register_error_handlers, ApiError, ErrorResponse
from ..core.logging import log

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

register_error_handlers(app)

TEMPLATES = parse_file('/opt/templates.txt')


def verify_request(r: Request):
    try:
        from ..core.headers import AUTHORIZATION
        from ..core.config import Config
        from secrets import compare_digest
        token = r.headers[AUTHORIZATION].split()[1]
        if compare_digest(token, Config.mailer.token):
            return True
        else:
            log.warning(f'Failed attempt to send mail: {r.client}')
            return False
    except (KeyError, IndexError):
        return False


@app.middleware('http')
async def verify_request_middleware(r: Request, call_next):
    if verify_request(r):
        return await call_next(r)
    else:
        return ErrorResponse(ApiError(code=status.HTTP_403_FORBIDDEN, message='Forbidden'))


class SendEmailOrder(BaseModel):
    user: str
    email: str
    lang: str
    url: str


class VerifyEmail(BaseModel):
    email: str


@app.post('/send', status_code=status.HTTP_202_ACCEPTED)
def send_email(model: SendEmailOrder):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from smtplib import SMTP_SSL, SMTP
    from ..core.config import Config
    cnf = Config.mailer
    sender = cnf.user if cnf.email is None else cnf.email
    template = TEMPLATES[model.lang]
    mail = MIMEMultipart('alternative')
    mail['Subject'] = template.subject
    mail['From'] = template.sender.replace('[EMAIL]', sender)
    mail['To'] = model.email
    mail.attach(MIMEText(
        template.content.replace('[URL]', model.url).replace('[USER]', model.user),
        'html'
    ))
    with (SMTP_SSL if cnf.ssl else SMTP)(cnf.url, port=cnf.port) as s:
        s.login(cnf.user, cnf.password)
        s.send_message(mail)


@app.post('/validate', response_model=VerifyEmail)
def validate_email(model: VerifyEmail):
    from email_validator import validate_email, EmailNotValidError
    try:
        valid = validate_email(model.email)
        return {
            'email': valid.email
        }
    except EmailNotValidError as e:
        return ErrorResponse(ApiError(code=status.HTTP_400_BAD_REQUEST, message=str(e)))


modify_openapi(app)
