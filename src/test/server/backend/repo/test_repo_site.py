import pytest
from muistot.backend.repos.site import SiteRepo


@pytest.mark.anyio
async def test_handle_nulls():
    repo = SiteRepo(None, None)
    assert not await repo._handle_location(None, None)
    assert not await repo._handle_info(None, None)
