import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import WebSocket


class ConnectionManager:
    """In-memory WebSocket broadcast hub.

    Anywhere in the backend can call `broadcast(...)` synchronously; the call
    is scheduled on the captured event loop and sent to every connected client
    on a best-effort basis. Dead sockets are dropped silently.

    FastAPI runs `def` (non-async) endpoints in a worker thread, so the
    broadcast site has no running loop of its own. `bind_loop()` is called
    once at app startup to capture the main loop; `broadcast()` then uses
    `run_coroutine_threadsafe` to hop onto it.
    """

    def __init__(self) -> None:
        self._clients: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._clients:
                self._clients.remove(websocket)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def _send_all(self, message: Dict[str, Any]) -> None:
        try:
            payload = json.dumps(message, default=str)
        except Exception:
            payload = json.dumps({"type": "broadcast_error", "detail": "non-serializable payload"})
        dead: List[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._clients:
                        self._clients.remove(ws)

    def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Fire-and-forget broadcast usable from sync or async code."""
        message = {
            "type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is not None:
            running.create_task(self._send_all(message))
            return

        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._send_all(message), loop)


manager = ConnectionManager()
