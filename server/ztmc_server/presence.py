"""재생/정지 판정 상태기계. 재생·정지 판단은 이 파일 한 곳에서만 한다.

입력은 프레임별 판정(detect)과 장치 상태(status), 시간 흐름(tick)뿐이고 시각은 인자로 받는다.
그래서 네트워크 없이 시험할 수 있다(server/tests/test_presence.py).

규칙
- 얼굴(face=True 이고 score >= MIN_SCORE)이 FACE_ON_MS 동안 계속 보이면 present
- 얼굴이 FACE_OFF_MS 동안 계속 안 보이면 absent
- status=offline 이거나 DEVICE_TIMEOUT_MS 동안 detect가 없으면 no_device
- no_device 에서 detect가 오면 absent 에서 다시 판정을 시작한다(바로 재생하지 않음)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .protocol import PresenceState


@dataclass
class PresenceConfig:
    face_on_ms: int = 300
    face_off_ms: int = 1500
    min_score: float = 0.6
    device_timeout_ms: int = 3000


class PresenceTracker:
    def __init__(self, cfg: PresenceConfig, now: float) -> None:
        self.cfg = cfg
        self.state: PresenceState = "no_device"
        self.since: float = now
        self._last_msg: Optional[float] = None
        # 지금 이어지고 있는 "얼굴 있음" / "얼굴 없음" 구간의 시작 시각
        self._face_since: Optional[float] = None
        self._noface_since: Optional[float] = None

    # ---- 입력 ----

    def on_detect(self, face: bool, score: float, now: float) -> list[PresenceState]:
        """detect 한 건을 반영한다. 바뀐 상태들을 순서대로 돌려준다(없으면 빈 목록).
        FACE_ON_MS=0 이면 no_device → absent → present 가 한 번에 일어날 수 있어 목록으로 돌려준다."""
        self._last_msg = now
        changes: list[PresenceState] = []
        if self.state == "no_device":
            changes += self._set("absent", now)
            self._face_since = self._noface_since = None

        if face and score >= self.cfg.min_score:
            self._noface_since = None
            if self._face_since is None:
                self._face_since = now
        else:
            self._face_since = None
            if self._noface_since is None:
                self._noface_since = now

        return changes + self._evaluate(now)

    def on_status(self, status: str, now: float) -> list[PresenceState]:
        """장치 status 토픽. offline 이면 즉시 no_device. online 은 detect가 올 때까지 기다린다."""
        if status == "offline":
            self._last_msg = None
            return self._set("no_device", now)
        return []

    def tick(self, now: float) -> list[PresenceState]:
        """주기적으로 불러 시간 조건(디바운스, 장치 시간초과)을 확인한다."""
        if self.state != "no_device":
            if self._last_msg is None or now - self._last_msg >= self.cfg.device_timeout_ms:
                self._last_msg = None
                return self._set("no_device", now)
        return self._evaluate(now)

    # ---- 내부 ----

    def _evaluate(self, now: float) -> list[PresenceState]:
        if self.state == "no_device":
            return []
        if (
            self.state != "present"
            and self._face_since is not None
            and now - self._face_since >= self.cfg.face_on_ms
        ):
            return self._set("present", now)
        if (
            self.state != "absent"
            and self._noface_since is not None
            and now - self._noface_since >= self.cfg.face_off_ms
        ):
            return self._set("absent", now)
        return []

    def _set(self, state: PresenceState, now: float) -> list[PresenceState]:
        if state == self.state:
            return []
        self.state = state
        self.since = now
        return [state]
