"""Lightweight site collector with durable local buffering."""
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx


class CollectorBuffer:
    def __init__(self, path: str = "collector-buffer.jsonl") -> None:
        self.path = Path(path)

    def append(self, payload: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload) + "\n")

    def drain(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]
        self.path.unlink()
        return records


async def sync_buffer(central_url: str, buffer: CollectorBuffer) -> int:
    records = buffer.drain()
    if not records:
        return 0
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{central_url.rstrip('/')}/api/v1/collectors/sync", json={"records": records})
            response.raise_for_status()
    except Exception:
        for record in records:
            buffer.append(record)
        return 0
    return len(records)


if __name__ == "__main__":
    asyncio.run(sync_buffer("http://127.0.0.1:8000", CollectorBuffer()))
