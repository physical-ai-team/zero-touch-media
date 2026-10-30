"""설정값. 전부 .env(또는 환경변수)에서 읽는다. 키 설명은 .env.example."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    server_host: str = field(default_factory=lambda: _env("SERVER_HOST", "0.0.0.0"))
    server_port: int = field(default_factory=lambda: int(_env("SERVER_PORT", "8000")))

    mqtt_host: str = field(default_factory=lambda: _env("MQTT_HOST", "127.0.0.1"))
    mqtt_port: int = field(default_factory=lambda: int(_env("MQTT_PORT", "1883")))
    mqtt_topic_prefix: str = field(default_factory=lambda: _env("MQTT_TOPIC_PREFIX", "ztmc"))

    face_on_ms: int = field(default_factory=lambda: int(_env("FACE_ON_MS", "300")))
    face_off_ms: int = field(default_factory=lambda: int(_env("FACE_OFF_MS", "1500")))
    min_score: float = field(default_factory=lambda: float(_env("MIN_SCORE", "0.6")))
    device_timeout_ms: int = field(default_factory=lambda: int(_env("DEVICE_TIMEOUT_MS", "3000")))

    player_detect_hz: float = field(default_factory=lambda: float(_env("PLAYER_DETECT_HZ", "10")))
    player_frame_hz: float = field(default_factory=lambda: float(_env("PLAYER_FRAME_HZ", "5")))
    frame_max_bytes: int = field(default_factory=lambda: int(_env("FRAME_MAX_BYTES", "100000")))
    clock_ping_interval_sec: float = field(
        default_factory=lambda: float(_env("CLOCK_PING_INTERVAL_SEC", "2"))
    )
    default_video_id: str = field(default_factory=lambda: _env("DEFAULT_VIDEO_ID", "jNQXAC9IVRw"))

    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    # MQTT 연결을 끄고 싶을 때(시험용). .env 키가 아니다.
    mqtt_enabled: bool = True


def load_settings() -> Settings:
    load_dotenv(REPO_ROOT / ".env")
    return Settings()
