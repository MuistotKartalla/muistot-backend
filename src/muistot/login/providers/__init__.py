from importlib import import_module
from typing import List

from pydantic import BaseModel

from ._default import router as default_login
from ._email_only import router as email_login
from ._status import router as status_router
from ...config import Config
from ...logging import log


def register_oauth_providers(app):
    class OAuthProviders(BaseModel):
        oauth_providers: List[str]

    providers = list()

    @app.get("/auth/oauth", tags=["Auth"])
    async def get_providers() -> OAuthProviders:
        return OAuthProviders(oauth_providers=[k for k in providers])

    for oauth_provider, config in Config.security.oauth.items():
        try:
            oauth_module = import_module(oauth_provider, __name__)
            app.include_router(
                getattr(oauth_module, "initialize")(**config),
                tags=["Auth"],
                prefix="/auth/oauth"
            )
            log.info(f"Loaded: {oauth_provider}")
            providers.append(oauth_provider.lstrip("."))
        except Exception as e:
            log.warning(f"Failed to load OAuth provider: {oauth_provider}", exc_info=e)


def register_default_providers(app):
    app.include_router(default_login, prefix="/auth")
    app.include_router(email_login, prefix="/auth")
    app.include_router(status_router, prefix="/auth")


__all__ = ["register_default_providers", "register_oauth_providers"]
