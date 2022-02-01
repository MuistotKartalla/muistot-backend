import httpx

from . import Mailer, Result


class MailgunMailer(Mailer):
    domain: str
    token: str

    def __init__(self, *, domain: str, token: str):
        self.domain = domain
        self.token = token

    async def send_email(self, email: str, **data) -> Result:
        from json import dumps
        async with httpx.AsyncClient() as client:
            client: httpx.AsyncClient
            r = await client.post(
                f"https://api.mailgun.net/v3/{self.domain}/messages",
                auth=("api", self.token),
                data={
                    "from": "Muistojakartalla <no-reply@muistojakartalla.fi>",
                    "to": [email],
                    "subject": "Hello {}!".format(data.get('user', '')),
                    "template": 'basic',
                    "h:X-Mailgun-Variables": dumps({"url": data['url']})
                },
                headers={

                }
            )
            if r.status_code in {200, 202, 204}:
                return Result(success=True)
            else:
                from ...core.logging import log
                from json import dumps
                log.warning('Failed to mail:\n' + dumps(r.json(), indent=4))
                return Result(success=False, reason=r.json().get('message', ''))

    async def verify_email(self, email: str) -> Result:
        from email_validator import validate_email, EmailNotValidError
        try:
            validate_email(email, check_deliverability=False)
            return Result(success=True)
        except EmailNotValidError as e:
            return Result(success=False, reason=str(e))


def get(*, domain: str, token: str, **_):
    return MailgunMailer(domain=domain, token=token)
