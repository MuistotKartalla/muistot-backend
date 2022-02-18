from secrets import compare_digest

from email_validator import validate_email, EmailNotValidError
from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .parse import parse_file
from ..core.errors import modify_openapi, register_error_handlers, ApiError, ErrorResponse
from headers import AUTHORIZATION
from ..core.logging import log


class MailConfig(BaseModel):
    user: str
    password: str
    email: str
    url: str
    port: int
    token: str


class SendEmailOrder(BaseModel):
    user: str
    email: str
    lang: str
    url: str


class VerifyEmail(BaseModel):
    email: str


TEMPLATES = parse_file('/opt/templates.txt')
with open("/opt/mailer-config.json") as f:
    CONFIG = MailConfig.parse_raw(f.read())

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


def verify_request(r: Request):
    try:
        token = r.headers[AUTHORIZATION].split()[1]
        if compare_digest(token, CONFIG.token):
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


@app.post('/send', status_code=status.HTTP_202_ACCEPTED)
def endpoint_send_email(model: SendEmailOrder):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from smtplib import SMTP
    cnf = CONFIG
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
    with SMTP(cnf.url, port=cnf.port) as s:
        s.login(cnf.user, cnf.password)
        s.send_message(mail)


@app.post('/validate', response_model=VerifyEmail)
def endpoint_validate_email(model: VerifyEmail):
    try:
        valid = validate_email(model.email)
        return VerifyEmail(email=valid.email)
    except EmailNotValidError as e:
        return ErrorResponse(ApiError(code=status.HTTP_400_BAD_REQUEST, message=str(e)))


modify_openapi(app)
