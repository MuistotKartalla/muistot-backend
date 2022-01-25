import httpx

from . import Mailer, Result
from ...core.logging import log


class DefaultMailer(Mailer):
    host: str
    token: str

    def __init__(self, *, host: str, token: str):
        self.host = host
        self.token = token

    async def send_verify_email(self, username: str, email: str) -> Result:
        async with httpx.AsyncClient() as client:
            r = await client.post(f'{self.host}/send', json={
                'email': email,
                'user': username
            })
            if 199 < r.status_code < 300:
                return Result(success=True)
            else:
                log.exception(f'Failed mail:\n{r.text}')
                return Result(success=False)

    async def verify_email(self, email: str) -> Result:
        async with httpx.AsyncClient() as client:
            r = await client.post(f'{self.host}/validate', json={
                'email': email
            })
            if r.status_code == httpx.codes.OK:
                return Result(success=True)
            elif r.status_code == httpx.codes.BAD_REQUEST:
                return Result(success=False, reason=r.json()['error']['message'])
            else:
                return Result(success=False)


def get(*, host: str, token: str) -> Mailer:
    return DefaultMailer(host=host, token=token)


__all__ = ['get']
