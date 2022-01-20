import aiohttp
from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter(prefix="/login")
CLIENT_ID = 123
CLIENT_SECRET = ""
STATE_COOKIE = "muistot-login-state-param"
REDIRECT_PATH = ""


class FacebookConfig(BaseModel):
    client_secret: str
    client_id: str


class Error:
    INVALID_SESSION = 460
    DE_AUTHORIZED = 458
    TOKEN_EXPIRED = 463

    message: str
    code: int
    type: str
    fbtrace_id: str
    error_subcode: int


class Token:
    value: str
    expires: int
    type: str


def generate_state() -> str:
    pass


async def exchange_for_token(code: str) -> Token:
    url = (
        "https://graph.facebook.com/v12.0/oauth/access_token?"
        f"client_id={CLIENT_ID}"
        f"&redirect_uri={router.url_path_for(REDIRECT_PATH)}"
        f"&client_secret={CLIENT_SECRET}"
        f"&code={code}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            json = await response.json()


@router.post("/facebook/delete")
def fb_delete():
    pass


@router.post("/facebook/uninstall")
def fb_uninstall():
    pass


@router.delete("/facebook/delete")
def fb_delete_self():
    pass


@router.post("/facebook/login")
def fb_login(resp: Response):
    state = generate_state()
    resp.headers["Location"] = (
        "https://www.facebook.com/v12.0/dialog/oauth?"
        f"client_id={CLIENT_ID}"
        f"&redirect_uri={router.url_path_for(REDIRECT_PATH)}"
        f"&state={state}"
    )
    return resp
