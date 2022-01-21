import re
from typing import Optional, Set, Tuple

from fastapi import Request

from ..headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE

ALLOWED_CHARS = re.compile(r'^[a-zA-Z0-9_:-]+$')


def get_languages() -> Set[str]:
    from ..config import Config
    return set(Config.languages)


def _validate_lang(lang: str) -> Optional[str]:
    langs = [lang.split('-')[0] for lang in lang.strip().split(',')]
    available = get_languages()
    for lang in langs:
        if lang in available:
            return lang


def extract_language(r: Request) -> str:
    """
    Extract language from request.

    Default if it is not specified or not allowed
    """
    from ..config import Config
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
                out = Config.default_language
        if out is None:
            raise ValueError('bad-lang')
        else:
            return out
    except KeyError:
        return Config.default_language


def url_safe(name: str) -> bool:
    return name is not None and ALLOWED_CHARS.fullmatch(name) is not None


def check_file(compressed_data: str) -> Optional[Tuple[bytes, str]]:
    from ..logging import log
    try:
        import base64
        import imghdr
        from ..config import Config
        raw_data = base64.b64decode(compressed_data, validate=True)
        file_type = imghdr.what(None, h=raw_data)
        if file_type in Config.files.allowed_filetypes:
            return raw_data, file_type
        else:
            log.info(f'Failed file validation: {file_type}')
    except Exception as e:
        log.exception('Failed file validation', exc_info=e)
    return None, None


__all__ = [
    'get_languages',
    'extract_language',
    'url_safe',
    'check_file'
]
