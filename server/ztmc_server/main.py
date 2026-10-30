"""서버 진입점.  실행:  python -m ztmc_server   (server/ 폴더에서, 또는 README 참고)

흐름: MQTT {prefix}/{device}/{status|hello|detect} → Engine(판정) → /ws/player 브라우저 + MQTT {prefix}/state
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .config import REPO_ROOT, Settings, load_settings
from .hub import PlayerHub
from .mqtt_in import Inbound, MqttBridge
from .presence import PresenceConfig, PresenceTracker
from .protocol import (
    Detect,
    DetectOut,
    DeviceInfo,
    Hello,
    Ping,
    PlayerEvent,
    Pong,
    StateMsg,
    Trace,
    now_ms,
    parse_topic,
)

log = logging.getLogger("ztmc.server")

TICK_SEC = 0.1


class Engine:
    """MQTT 입력을 판정 상태기계에 넣고, 바뀐 결과를 브라우저와 MQTT로 내보낸다."""

    def __init__(self, settings: Settings, hub: PlayerHub) -> None:
        self.s = settings
        self.hub = hub
        self.tracker = PresenceTracker(
            PresenceConfig(
                face_on_ms=settings.face_on_ms,
                face_off_ms=settings.face_off_ms,
                min_score=settings.min_score,
                device_timeout_ms=settings.device_timeout_ms,
            ),
            now=now_ms(),
        )
        self.device = DeviceInfo()
        self.mqtt: Optional[MqttBridge] = None
        self._last_detect_sent = 0.0
        self.stats = {"detect": 0, "bad": 0, "state_changes": 0}

    # ---- 출력 ----

    def state_msg(self) -> StateMsg:
        self.device.connected = self.tracker.state != "no_device"
        return StateMsg(state=self.tracker.state, since=self.tracker.since, device=self.device)

    async def _publish_state(self, state: str) -> None:
        self.stats["state_changes"] += 1
        msg = self.state_msg()
        msg.state = state  # 한 번에 여러 단계가 바뀌면 중간 상태도 순서대로 보낸다
        text = msg.model_dump_json()
        log.info("state -> %s", state)
        await self.hub.broadcast(text)
        if self.mqtt:
            self.mqtt.publish(f"{self.s.mqtt_topic_prefix}/state", text, qos=1, retain=True)

    # ---- 입력 ----

    async def handle_mqtt(self, item: Inbound) -> None:
        topic, payload, recv = item
        parsed = parse_topic(topic, self.s.mqtt_topic_prefix)
        if parsed is None:
            return
        device_id, kind = parsed
        changes: list = []
        try:
            if kind == "status":
                status = payload.decode("utf-8", "replace").strip()
                log.info("device %s status=%s", device_id, status)
                self.device.id = device_id
                changes = self.tracker.on_status(status, recv)
            elif kind == "hello":
                h = Hello.model_validate_json(payload)
                self.device.id, self.device.fw, self.device.model = h.device_id, h.fw, h.model
                log.info("device hello %s", h.model_dump())
            elif kind == "detect":
                d = Detect.model_validate_json(payload)
                self.stats["detect"] += 1
                self.device.id = d.device_id
                changes = self.tracker.on_detect(d.face, d.score, recv)
                await self._forward_detect(d, recv)
        except (ValidationError, ValueError) as e:
            self.stats["bad"] += 1
            log.warning("bad message on %s: %s", topic, e)
            return
        for state in changes:
            await self._publish_state(state)

    async def _forward_detect(self, d: Detect, recv: float) -> None:
        # 화면 표시용이라 PLAYER_DETECT_HZ로 줄여 보낸다. 판정에는 모든 detect를 쓴다.
        if self.s.player_detect_hz <= 0 or recv - self._last_detect_sent < 1000.0 / self.s.player_detect_hz:
            return
        self._last_detect_sent = recv
        out = DetectOut(**d.model_dump(), trace=Trace(gw_recv=recv, gw_sent=now_ms()))
        await self.hub.broadcast(out.model_dump_json())

    async def tick(self) -> None:
        for state in self.tracker.tick(now_ms()):
            await self._publish_state(state)

    def handle_player(self, text: str) -> None:
        try:
            data = json.loads(text)
            kind = data.get("type")
            if kind == "player":
                ev = PlayerEvent.model_validate(data)
                log.info("player event %s (state=%s)", ev.event, self.tracker.state)
            elif kind == "pong":
                p = Pong.model_validate(data)
                log.debug("clock rtt %.1f ms", now_ms() - p.t0)
        except (ValueError, ValidationError, AttributeError):
            pass  # 모르는 메시지는 무시


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    hub = PlayerHub()
    engine = Engine(settings, hub)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Inbound] = asyncio.Queue()
        if settings.mqtt_enabled:
            engine.mqtt = MqttBridge(
                settings.mqtt_host, settings.mqtt_port, settings.mqtt_topic_prefix,
                loop, queue.put_nowait,
            )
            engine.mqtt.start()

        async def consume():
            while True:
                await engine.handle_mqtt(await queue.get())

        async def ticker():
            while True:
                await asyncio.sleep(TICK_SEC)
                await engine.tick()

        tasks = [asyncio.create_task(consume()), asyncio.create_task(ticker())]
        try:
            yield
        finally:
            for t in tasks:
                t.cancel()
            if engine.mqtt:
                engine.mqtt.stop()

    app = FastAPI(title="Zero-Touch Media Control", lifespan=lifespan)
    app.state.engine = engine

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "mqtt": bool(engine.mqtt and engine.mqtt.connected),
            "state": engine.tracker.state,
            "device": engine.device.model_dump(),
            "players": hub.count,
            "stats": engine.stats,
        }

    @app.get("/api/config")
    def api_config():
        return {
            "default_video_id": settings.default_video_id,
            "face_on_ms": settings.face_on_ms,
            "face_off_ms": settings.face_off_ms,
            "min_score": settings.min_score,
            "device_timeout_ms": settings.device_timeout_ms,
        }

    @app.websocket("/ws/player")
    async def ws_player(ws: WebSocket):
        await ws.accept()
        await hub.add(ws)
        await ws.send_text(engine.state_msg().model_dump_json())

        async def pinger():
            while True:
                await asyncio.sleep(settings.clock_ping_interval_sec)
                await ws.send_text(Ping(t0=now_ms()).model_dump_json())

        ping_task = asyncio.create_task(pinger())
        try:
            while True:
                engine.handle_player(await ws.receive_text())
        except WebSocketDisconnect:
            pass
        finally:
            ping_task.cancel()
            await hub.remove(ws)

    # 웹 페이지(web/)는 / 에서 정적 제공. API 경로보다 뒤에 둔다.
    app.mount("/", StaticFiles(directory=REPO_ROOT / "web", html=True), name="web")
    return app
