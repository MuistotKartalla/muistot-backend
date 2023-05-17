from httpx import AsyncClient

from .abstract import Mailer, Result


class ServerMailer(Mailer):
    host: str
    token: str
    reroute: str

    def __init__(self, *, host: str, token: str, reroute: str, **_):
        self.host = host
        self.token = token
        self.reroute = reroute

    async def send_email(self, email: str, email_type: str, **data) -> Result:
        if email_type != "login":
            return Result(success=False)
        from urllib.parse import urlencode
        token = data.pop("token")
        url = urlencode(dict(user=data["user"], token=token, verified=data["verified"]))
        data["url"] = f'{self.reroute}#email-login:{url}'
        async with AsyncClient() as client:
            r = await client.post(
                f"{self.host}/send",
                json={"email": email, **data},
                headers={"Authorization": f"bearer {self.token}"},
            )
            if 199 < r.status_code < 300:
                return Result(success=True)
            else:
                return Result(success=False)
