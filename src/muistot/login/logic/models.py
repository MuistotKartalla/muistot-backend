from typing import Optional

from pydantic import BaseModel, root_validator, EmailStr


class LoginQuery(BaseModel):
    username: Optional[str]
    email: Optional[EmailStr]
    password: str

    @root_validator(pre=False, skip_on_failure=True)
    def check_one(cls, value):
        u = value.get("username", None)
        e = value.get("email", None)
        assert (u is not None or e is not None), "Identifier Required"
        return value

    @root_validator(pre=False, skip_on_failure=True)
    def check_only_one(cls, value):
        u = value.pop("username", None)
        e = value.pop("email", None)
        assert not (u is not None and e is not None), "Only one identifier allowed"
        if u is not None:
            return dict(username=u, enail=None, **value)
        else:
            return dict(email=e, username=None, **value)


class RegisterQuery(BaseModel):
    username: str
    email: EmailStr
    password: str
