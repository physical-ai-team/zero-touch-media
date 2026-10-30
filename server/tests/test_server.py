"""MQTT 없이 Engine에 메시지를 직접 넣어 브라우저 WebSocket까지 확인한다."""

import asyncio
import json

from fastapi.testclient import TestClient

from ztmc_server.config import Settings
from ztmc_server.main import create_app
from ztmc_server.protocol import now_ms, parse_topic


def make_client():
    s = Settings(mqtt_enabled=False, face_on_ms=0, player_detect_hz=1000, clock_ping_interval_sec=60)
    app = create_app(s)
    return TestClient(app), app.state.engine


def push(client, engine, topic: str, payload):
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    client.portal.call(engine.handle_mqtt, (topic, data, now_ms()))


def test_parse_topic():
    assert parse_topic("ztmc/cam-1/detect", "ztmc") == ("cam-1", "detect")
    assert parse_topic("ztmc/state", "ztmc") is None
    assert parse_topic("other/cam-1/detect", "ztmc") is None


def test_health_and_config():
    client, _ = make_client()
    with client:
        assert client.get("/health").json()["state"] == "no_device"
        assert "default_video_id" in client.get("/api/config").json()


def test_player_gets_state_and_detect_flow():
    client, engine = make_client()
    with client, client.websocket_connect("/ws/player") as ws:
        first = json.loads(ws.receive_text())
        assert first == {**first, "type": "state", "state": "no_device"}

        push(client, engine, "ztmc/cam-1/hello", {"device_id": "cam-1", "fw": "0.1.0", "model": "m"})
        push(client, engine, "ztmc/cam-1/detect",
             {"device_id": "cam-1", "seq": 1, "face": True, "score": 0.9, "infer_ms": 40, "extra": 1})

        got = [json.loads(ws.receive_text()) for _ in range(3)]
        states = [m["state"] for m in got if m["type"] == "state"]
        detects = [m for m in got if m["type"] == "detect"]
        assert states == ["absent", "present"]  # face_on_ms=0 이라 바로 present
        assert detects[0]["seq"] == 1 and detects[0]["trace"]["gw_recv"] is not None
        assert got[-1]["device"]["fw"] == "0.1.0"

        push(client, engine, "ztmc/cam-1/status", b"offline")
        msg = json.loads(ws.receive_text())
        assert msg["state"] == "no_device" and msg["device"]["connected"] is False


def test_bad_payload_is_counted_not_crashing():
    client, engine = make_client()
    with client:
        push(client, engine, "ztmc/cam-1/detect", b"not json")
        push(client, engine, "ztmc/cam-1/detect", {"device_id": "cam-1"})  # face 없음
        assert client.get("/health").json()["stats"]["bad"] == 2
