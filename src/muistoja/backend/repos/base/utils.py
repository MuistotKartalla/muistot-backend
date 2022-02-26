import re
from typing import Set, Optional

from fastapi import HTTPException, status
from fastapi import Request
from headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE

from ....config import Config

ALLOWED_CHARS = re.compile(r"^[a-zA-Z0-9_:-]+$")


def not_implemented(f):
    """
    Marks function as not used and generates a warning on startup

    Should only be used on Repo instance methods
    """
    from ....logging import log
    from functools import wraps

    log.warning(f"Function not implemented {repr(f)}")

    @wraps(f)
    async def decorator(*_, **__):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not Implemented"
        )

    return decorator


def get_languages() -> Set[str]:
    return set(Config.localization.supported)


def _validate_lang(lang: str) -> Optional[str]:
    langs = [lang.split("-")[0] for lang in lang.strip().split(",")]
    available = get_languages()
    for lang in langs:
        if lang in available:
            return lang


def extract_language(r: Request) -> str:
    """Extract language from request.

    Default if it is not specified or not allowed
    """

    try:
        if r.method == "GET":
            out = r.headers[ACCEPT_LANGUAGE]
        else:
            out = r.headers[CONTENT_LANGUAGE]
        if out is not None:
            out = out.strip()
            if len(out) > 0:
                out = _validate_lang(out)
            else:
                out = Config.localization.default
        if out is None:
            raise ValueError("bad-lang")
        else:
            return out
    except KeyError:
        return Config.localization.default


def check_language(lang: str):
    """Check that language is available in config.
    """
    if lang not in get_languages():
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Language not supported"
        )


__all__ = [
    "get_languages",
    "extract_language",
    "check_language",
    "not_implemented"
]
