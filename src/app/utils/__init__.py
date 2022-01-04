from typing import List

from fastapi import Request

from ..headers import ACCEPT_LANGUAGE


def get_languages() -> List[str]:
    from ..config import Config
    return list(Config.languages)


def extract_language_or_default(r: Request) -> str:
    try:
        available = get_languages()
        lang = r.headers[ACCEPT_LANGUAGE]
        if lang in available:
            return lang
        else:
            return "fi"
    except KeyError:
        return "fi"


__all__ = [
    'get_languages',
    'extract_language_or_default'
]
