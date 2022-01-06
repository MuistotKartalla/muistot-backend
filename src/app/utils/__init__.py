import re
from typing import Optional, Set, Tuple

from fastapi import Request

from ..headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE

ALLOWED_CHARS = re.compile(r'^[a-zA-Z0-9_:-]+$')


def get_languages() -> Set[str]:
    from ..config import Config
    return set(Config.languages)


def _validate_lang(lang: str):
    langs = [lang.split('-')[0] for lang in lang.strip().split(',')]
    available = get_languages()
    for lang in langs:
        if lang in available:
            return lang


def extract_language(r: Request) -> str:
    """
    Extract language from request.

    Default if it is not specified
    """
    from ..config import Config
    try:
        if r.method == "GET":
            out = _validate_lang(r.headers[ACCEPT_LANGUAGE])
        else:
            out = _validate_lang(r.headers[CONTENT_LANGUAGE])
        if out is not None:
            return out
        else:
            return Config.default_language
    except KeyError:
        return Config.default_language


def url_safe(name: str) -> bool:
    return name is not None and ALLOWED_CHARS.fullmatch(name) is not None


def check_file(compressed_data: str) -> Optional[Tuple[bytes, str]]:
    try:
        import base64
        import imghdr
        from ..config import Config
        raw_data = base64.b64decode(compressed_data, validate=True)
        file_type = imghdr.what(None, h=raw_data)
        if file_type in Config.files.allowed_filetypes:
            return raw_data, file_type
    except Exception as e:
        from ..logging import log
        log.exception('Failed file validation', exc_info=e)


__all__ = [
    'get_languages',
    'extract_language',
    'url_safe',
    'check_file'
]
