import pytest
from muistot.database import DatabaseProvider, OperationalError


def test_is_connected_detects_engine():
    d = DatabaseProvider(None)
    assert not d.is_connected(), "Was connected at creation"
    d.engine = 'a'
    assert d.is_connected(), "Was not connected with engine present"


@pytest.mark.anyio
async def test_throws_on_not_connected():
    d = DatabaseProvider(None)
    with pytest.raises(OperationalError):
        async with d():
            pass
