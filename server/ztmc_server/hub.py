"""브라우저(/ws/player) 연결 관리: 접속 목록과 전체 발송."""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

log = logging.getLogger("ztmc.hub")


class PlayerHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def count(self) -> int:
        return len(self._clients)

    async def add(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.add(ws)
        log.info("player connected (total %d)", self.count)

    async def remove(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        log.info("player disconnected (total %d)", self.count)

    async def broadcast(self, data: str | bytes) -> None:
        """str은 텍스트(JSON), bytes는 바이너리(보드 카메라 JPEG) 메시지로 보낸다."""
        async with self._lock:
            clients = list(self._clients)
        dead = []
        for ws in clients:
            try:
                if isinstance(data, bytes):
                    await ws.send_bytes(data)
                else:
                    await ws.send_text(data)
            except Exception:  # 끊긴 연결은 조용히 정리
                dead.append(ws)
        for ws in dead:
            await self.remove(ws)
