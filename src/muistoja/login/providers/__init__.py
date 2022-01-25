from importlib import import_module
from typing import List

from pydantic import BaseModel

from ._default import router as default_login
from ...core.config import Config
from ...core.logging import log


def register_oauth_providers(app, **kwargs):
    class OAuthProviders(BaseModel):
        oauth_providers: List[str]

    @app.get("/oauth", tags=["Auth"])
    async def get_providers() -> OAuthProviders:
        return OAuthProviders(oauth_providers=[k for k in Config.security.oauth])

    for oauth_provider in Config.security.oauth:
        try:
            oauth_module = import_module(f".{oauth_provider}")
            app.include_router(getattr(oauth_module, 'router'), **kwargs)
            log.info(f'Loaded: {oauth_provider}')
        except Exception as e:
            log.warning(f"Failed to load OAuth provider: {oauth_provider}", exc_info=e)


__all__ = ['default_login', 'register_oauth_providers']
