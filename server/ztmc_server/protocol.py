"""메시지 형식. 기준 문서는 docs/03-protocol.md — 둘이 다르면 이 코드가 맞고, 문서를 고친다.

공통 규칙: 모르는 필드는 무시(extra="ignore"). 필드 추가는 자유, 삭제·이름 변경은 팀장 확인.
"""

from __future__ import annotations

import time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


def now_ms() -> float:
    """서버 시계 기준 epoch ms. 모든 시각은 이 함수로 찍는다."""
    return time.time() * 1000.0


class _Msg(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ---------- ESP32 → 브로커 → 서버 (MQTT) ----------

class Hello(_Msg):
    """토픽 {prefix}/{device_id}/hello (retain)"""

    device_id: str
    fw: str = ""
    model: str = ""
    threshold: Optional[float] = None


class Detect(_Msg):
    """토픽 {prefix}/{device_id}/detect — 추론할 때마다"""

    device_id: str
    seq: int = 0
    face: bool
    score: float = 0.0
    count: int = 0
    dsp_ms: Optional[float] = None
    infer_ms: Optional[float] = None


DeviceStatus = Literal["online", "offline"]
"""토픽 {prefix}/{device_id}/status (retain). JSON이 아니라 문자열 그대로."""


# ---------- 서버 → 브라우저 (WebSocket /ws/player) + MQTT {prefix}/state ----------

PresenceState = Literal["present", "absent", "no_device"]


class DeviceInfo(_Msg):
    id: Optional[str] = None
    connected: bool = False
    fw: Optional[str] = None
    model: Optional[str] = None


class StateMsg(_Msg):
    type: Literal["state"] = "state"
    state: PresenceState
    since: float
    device: DeviceInfo


class Trace(_Msg):
    gw_recv: Optional[float] = None
    gw_sent: Optional[float] = None


class DetectOut(_Msg):
    type: Literal["detect"] = "detect"
    device_id: str
    seq: int
    face: bool
    score: float
    count: int = 0
    dsp_ms: Optional[float] = None
    infer_ms: Optional[float] = None
    trace: Trace


class Ping(_Msg):
    type: Literal["ping"] = "ping"
    t0: float


# ---------- 브라우저 → 서버 ----------

PlayerEventName = Literal["playing", "paused", "ended", "manual_on", "manual_off"]


class PlayerEvent(_Msg):
    type: Literal["player"]
    event: PlayerEventName
    ts: Optional[float] = None


class Pong(_Msg):
    type: Literal["pong"]
    t0: float
    t1: float


def parse_topic(topic: str, prefix: str) -> Optional[tuple[str, str]]:
    """'{prefix}/{device_id}/{kind}' → (device_id, kind). 형식이 다르면 None."""
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != prefix or not parts[1]:
        return None
    return parts[1], parts[2]
