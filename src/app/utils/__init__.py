import re
from typing import Optional, Set

from fastapi import Request

from ..headers import ACCEPT_LANGUAGE

ALLOWED_CHARS = re.compile(r'^[a-zA-Z0-9_:-]+$')


def get_languages() -> Set[str]:
    from ..config import Config
    return set(Config.languages)


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


def check_file(compressed_data: str) -> Optional[bytes]:
    try:
        import base64
        import imghdr
        from ..config import Config
        raw_data = base64.b64decode(compressed_data, validate=True)
        file_type = imghdr.what(None, h=raw_data)
        if file_type in Config.files.allowed_filetypes:
            return raw_data
    except Exception as e:
        from ..logging import log
        log.exception('Failed file validation', exc_info=e)


__all__ = [
    'get_languages',
    'extract_language_or_default',
    'url_safe',
    'check_file'
]
