import asyncio
import socket
import time
from dataclasses import dataclass

import httpx

from app.models import CheckType


@dataclass
class CheckResult:
    success: bool
    latency_ms: float | None
    packet_loss: float
    message: str


async def run_check(check_type: str, target: str) -> CheckResult:
    started = time.perf_counter()
    try:
        if check_type == CheckType.ping.value:
            await asyncio.to_thread(socket.gethostbyname, target)
        elif check_type == CheckType.tcp.value:
            host, separator, port = target.partition(":")
            if not separator:
                raise ValueError("TCP targets must use host:port")
            reader, writer = await asyncio.open_connection(host, int(port))
            writer.close()
            await writer.wait_closed()
            del reader
        elif check_type == CheckType.http.value:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(target)
                response.raise_for_status()
        elif check_type == CheckType.dns.value:
            await asyncio.to_thread(socket.getaddrinfo, target, None)
        else:
            raise ValueError(f"Unsupported check type: {check_type}")
    except Exception as exc:
        return CheckResult(False, None, 100.0, str(exc))

    latency = round((time.perf_counter() - started) * 1000, 2)
    return CheckResult(True, latency, 0.0, "Check passed")
