from typing import Optional, Iterable, Set

from headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class LanguageChecker:
    __slots__ = ["supported"]

    def __init__(self, supported: frozenset):
        self.supported = supported

    def check(self, language: str):
        if language is None or language not in self.supported:
            raise HTTPException(status_code=406, detail="Language not supported")


class LanguageMiddleware(BaseHTTPMiddleware):

    @staticmethod
    def get(r: Request) -> str:
        return r.state.language if r.state.language else r.state.default_language

    @staticmethod
    def checker(r: Request) -> Set[str]:
        return r.state.language_checker

    def __init__(self, app, default_language: str, languages: Iterable[str]):
        super(LanguageMiddleware, self).__init__(app)
        self.default_language = default_language
        self.languages = frozenset(languages)
        self.checker = LanguageChecker(self.languages)

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
        request.state.language_checker = self.checker
        return await call_next(request)
