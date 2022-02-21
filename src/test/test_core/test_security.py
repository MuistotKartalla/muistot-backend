def test_manager_add():
    from muistoja.sessions import add_session_manager
    from muistoja.sessions.middleware import SessionManagerMiddleware
    from starlette.middleware.authentication import AuthenticationMiddleware

    class Mock:
        @staticmethod
        def add_middleware(middleware, **opts):
            assert middleware == AuthenticationMiddleware
            assert type(opts["backend"]) == SessionManagerMiddleware
            assert "on_error" in opts

    add_session_manager(Mock)
