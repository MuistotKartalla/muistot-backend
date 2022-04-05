import pytest


@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"
