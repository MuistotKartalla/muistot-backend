from collections import namedtuple

import pytest
from fastapi import HTTPException
from muistot import mailer
from muistot.login.logic.email import create_email_verifier, fetch_user_by_email, can_send_email, send_email
from muistot.mailer import Mailer, Result

User = namedtuple("User", ["username", "email"])


class Mock(Mailer):

    def __init__(self):
        self.sends = list()
        self.verifys = list()

    async def send_email(self, email: str, email_type: str, **data) -> Result:
        self.sends.append((email, data))
        return Result(success=True)


@pytest.fixture
def mail():
    i = Mock()
    old = mailer.instance
    mailer.instance = i
    yield i
    mailer.instance = old


@pytest.fixture
async def user(db, anyio_backend):
    from passlib.pwd import genword
    name = genword(length=40)
    email = f"{genword(length=20)}@example.com"
    await db.execute("INSERT INTO users (username, email) VALUE (:user, :email)", values=dict(user=name, email=email))
    yield User(username=name, email=email)
    await db.execute("DELETE FROM users WHERE username = :user", values=dict(user=name))


@pytest.mark.anyio
async def test_email(mail, db, user):
    await send_email(user.username, db)
    email, data = mail.sends[0]

    assert email == user.email, f'{email}-{data}'
    assert "token" in data
    assert data["user"] == user.username
    assert not data["verified"]


@pytest.mark.anyio
async def test_email_timeout(mail, db, user):
    await send_email(user.username, db)
    assert not await can_send_email(user.email, db)
    await db.execute(
        """
        UPDATE user_email_verifiers 
            SET created_at =  TIMESTAMPADD(MINUTE,-5,created_at) 
        WHERE user_id = (SELECT id FROM users WHERE username = :user)
        """,
        values=dict(user=user.username)
    )
    assert await can_send_email(user.email, db)


@pytest.mark.anyio
async def fetch_user(db, user):
    assert (await fetch_user_by_email(user.email, db)) == user.username
    assert (await fetch_user_by_email('a', db)) is None
    assert (await fetch_user_by_email(None, db)) is None


@pytest.mark.anyio
async def test_verifier(db, user):
    email, token, verified = await create_email_verifier(user.username, db)
    assert not verified
    assert email == user.email
    assert token is not None
    assert (await db.fetch_val(
        "SELECT COUNT(*) FROM user_email_verifiers WHERE verifier = :token",
        values=dict(token=token)
    )) == 1


@pytest.mark.anyio
async def test_create_503(db, user):
    """If generation fails

    Although the email will fail here, the username should work too
    """
    from muistot.login.logic.login import try_create_user
    with pytest.raises(HTTPException) as e:
        await try_create_user(user.email, db)
    assert e.value.status_code == 503
