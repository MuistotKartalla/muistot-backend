from ._default import router as default_login


def register_oauth_providers(app):
    from ..config import Config
    from ..logging import log
    from importlib import import_module
    from pydantic import BaseModel
    from typing import List

    class OAuthProviders(BaseModel):
        oauth_providers: List[str]

    @app.get("/login")
    async def get_providers() -> OAuthProviders:
        return OAuthProviders(oauth_providers=[k for k in Config.oauth])

    for oauth_provider in Config.oauth:
        try:
            oauth_module = import_module(f".{oauth_provider}")
            app.include_router(getattr(oauth_module, 'router'))
            log.info(f'Loaded: {oauth_provider}')
        except Exception as e:
            log.warning(f"Failed to load OAuth provider: {oauth_provider}", exc_info=e)


__all__ = ['default_login', 'register_oauth_providers']
