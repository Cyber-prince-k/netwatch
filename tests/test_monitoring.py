import pytest

from app.monitoring import run_check


@pytest.mark.asyncio
async def test_ping_check_success():
    result = await run_check("ping", "127.0.0.1")
    assert result.success is True
    assert result.packet_loss == 0
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_unknown_check_fails_without_raising():
    result = await run_check("unsupported", "example")
    assert result.success is False
    assert result.packet_loss == 100
