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


def extract_language(r: Request, default_on_invalid: bool = False) -> str:
    """Extract language from request.

    Default if it is not specified or not allowed

    This will return default on:
    - empty
    - missing

    And raise and error on:
    - invalid
    """
    try:
        # This is for convenience
        out = r.headers.get("Muistot-Language", None)
        if out is None:
            # Errors on no headers
            if r.method == "GET":
                out = r.headers[ACCEPT_LANGUAGE]
            else:
                out = r.headers[CONTENT_LANGUAGE]
        out = out.strip()
        if len(out) > 0:
            # Returns None on invalid
            out = _validate_lang(out)
        else:
            # Break out default if empty
            out = Config.localization.default
        if out is None:
            if default_on_invalid:
                return Config.localization.default
            else:
                raise ValueError("bad-lang")
        else:
            return out
    except KeyError:
        # This also comes from deep inside Starlette when request scope has no headers
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
