import re
from typing import List

from fastapi import Request

from ..headers import ACCEPT_LANGUAGE

ALLOWED_CHARS = re.compile(r'^[a-zA-Z0-9_:-]+$')


def get_languages() -> List[str]:
    from ..config import Config
    return list(Config.languages)


def extract_language_or_default(r: Request) -> str:
    from ..config import Config
    try:
        available = get_languages()
        lang = r.headers[ACCEPT_LANGUAGE]
        if lang in available:
            return lang
        else:
            return Config.default_language
    except KeyError:
        return Config.default_language


def url_safe(name: str) -> bool:
    return name is not None and ALLOWED_CHARS.fullmatch(name) is not None


__all__ = [
    'get_languages',
    'extract_language_or_default',
    'url_safe'
]
