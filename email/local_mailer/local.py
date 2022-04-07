"""
This is for testing
"""
import httpx
from muistot.logging import log
from muistot.mailer import Mailer, Result


class DefaultMailer(Mailer):
    host: str
    token: str

    def __init__(self, *, host: str, token: str, reroute: str, **_):
        self.host = host
        self.token = token
        self.reroute = reroute

    async def send_email(self, email: str, **data) -> Result:
        from urllib.parse import urlencode
        token = data.pop("token")
        url = urlencode(dict(user=data["user"], token=token, verified=data["verified"]))
        data["url"] = f'{self.reroute}#email-login:{url}'
        data["lang"] = "fi"
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.host}/send",
                json={"email": email, **data},
                headers={"Authorization": f"bearer {self.token}"},
            )
            if 199 < r.status_code < 300:
                return Result(success=True)
            else:
                log.exception(f"Failed mail:\n{r.text}")
                return Result(success=False)

    async def verify_email(self, email: str) -> Result:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.host}/validate",
                json={"email": email},
                headers={"Authorization": f"bearer {self.token}"},
            )
            if r.status_code == httpx.codes.OK:
                return Result(success=True)
            elif r.status_code == httpx.codes.BAD_REQUEST:
                return Result(success=False, reason=r.json()["error"]["message"])
            else:
                return Result(success=False)
