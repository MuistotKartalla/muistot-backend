from typing import Optional, Iterable

from headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class LanguageMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, default_language: str, languages: Iterable[str]):
        super(LanguageMiddleware, self).__init__(app)
        self.default_language = default_language
        self.languages = {*languages}

    def validate_language(self, lang: str) -> Optional[str]:
        """Validates a language is in supported languages
        """
        langs = [lang.split("-")[0] for lang in lang.strip().split(",")]
        for lang in langs:
            if lang in self.languages:
                return lang

    def extract_language(self, request: Request):
        """
        Extract language from request.

        Default if it is not specified or not allowed

        This will return default on:
        - empty
        - missing

        And raise and error on:
        - invalid
        """
        try:
            language_header = request.headers.get("Muistot-Language", None)
            if language_header is None:
                if request.method == "GET":
                    language_header = request.headers[ACCEPT_LANGUAGE]
                else:
                    language_header = request.headers[CONTENT_LANGUAGE]
            detected_language = self.validate_language(language_header)
            if request.method != "GET" and not detected_language:
                raise HTTPException(status_code=406, detail="Language not supported")
            return detected_language
        except KeyError:
            return self.default_language

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.language = self.extract_language(request)
        return await call_next(request)
