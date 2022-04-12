import pytest
from fastapi import status


@pytest.mark.anyio
async def test_email_login_timeout(client, db):
    r = client.post("/login/email-only?email=testing_email@example.com")
    assert r.status_code == 204
    await db.execute("DELETE FROM user_email_verifiers")
    r = client.post("/login/email-only?email=testing_email@example.com")
    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
