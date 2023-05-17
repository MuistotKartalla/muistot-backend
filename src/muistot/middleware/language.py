from typing import Optional, Iterable

from headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class LanguageMiddleware(BaseHTTPMiddleware):

    @staticmethod
    def get(r: Request) -> str:
        return r.state.language if r.state.language else r.state.default_language

    @staticmethod
    def supported(r: Request) -> str:
        lang = r.state.language
        if not lang:
            raise HTTPException(status_code=406, detail="Language not supported")
        return lang

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
        """Extract language from request.
        """
        try:
            language_header = request.headers.get("Muistot-Language", None)
            if not language_header:
                if request.method == "GET":
                    language_header = request.headers[ACCEPT_LANGUAGE]
                else:
                    language_header = request.headers[CONTENT_LANGUAGE]
            return self.validate_language(language_header)
        except KeyError:
            return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.language = self.extract_language(request)
        request.state.default_language = self.default_language
        return await call_next(request)
