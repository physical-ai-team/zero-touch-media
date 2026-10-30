"""MQTT 모니터. 브로커를 직접 구독해 ESP32가 보내는 얼굴 감지 신호를 터미널에 실시간으로 보여 준다.
서버 없이 브로커만 켜도 된다 → 보드 연결 확인·디버깅용. 규격: docs/03-protocol.md

    python tools/monitor.py                    # 상태 한 줄 + 바뀔 때만 기록
    python tools/monitor.py --all              # detect 메시지를 전부 한 줄씩
    python tools/monitor.py --host 192.168.0.10

기본값(MQTT_HOST, MQTT_PORT, MQTT_TOPIC_PREFIX, DEVICE_TIMEOUT_MS)은 루트 .env에서 읽는다. Ctrl+C로 종료.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]

GREEN, RED, YELLOW, GRAY, BOLD, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m"


class Device:
    def __init__(self) -> None:
        self.status = "?"
        self.hello: dict = {}
        self.face: bool | None = None
        self.last: dict = {}
        self.last_at = 0.0          # 마지막 detect 받은 시각(time.monotonic)
        self.times: deque[float] = deque(maxlen=50)
        self.count = 0
        self.lost = 0               # seq 건너뜀으로 추정한 유실 수
        self.frames: deque[tuple[float, int]] = deque(maxlen=50)  # (받은 시각, JPEG 바이트)


class Monitor:
    def __init__(self, a: argparse.Namespace) -> None:
        self.a = a
        self.devices: dict[str, Device] = {}
        self.server_state = "-"
        self.connected = False
        self.lock = threading.Lock()
        self.color = not a.no_color

    def c(self, code: str, text: str) -> str:
        return f"{code}{text}{RESET}" if self.color else text

    def log(self, text: str) -> None:
        # 상태 줄을 지우고 기록 한 줄을 찍은 뒤, 상태 줄은 다음 redraw에서 다시 그린다.
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\r\033[K{self.c(GRAY, ts)} {text}", flush=True)

    # ---- paho 스레드 ----

    def on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            self.log(self.c(RED, f"브로커 접속 실패: {reason_code}"))
            return
        self.connected = True
        client.subscribe(f"{self.a.prefix}/#", qos=1)
        self.log(self.c(GREEN, f"브로커 접속 {self.a.host}:{self.a.port}, 구독 {self.a.prefix}/#"))

    def on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        self.connected = False
        self.log(self.c(RED, f"브로커 끊김: {reason_code} (재접속 시도 중)"))

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage) -> None:
        parts = msg.topic.split("/")
        text = msg.payload.decode("utf-8", "replace")
        with self.lock:
            if parts == [self.a.prefix, "state"]:
                self.on_server_state(text)
            elif len(parts) == 3 and parts[0] == self.a.prefix:
                dev = self.devices.setdefault(parts[1], Device())
                kind = parts[2]
                if kind == "status":
                    dev.status = text.strip()
                    code = GREEN if dev.status == "online" else RED
                    self.log(f"[{parts[1]}] status = {self.c(code, dev.status)}")
                elif kind == "hello":
                    dev.hello = self.parse(text, msg.topic) or {}
                    self.log(f"[{parts[1]}] hello {dev.hello}")
                elif kind == "frame":
                    dev.frames.append((time.monotonic(), len(msg.payload)))
                elif kind == "detect":
                    d = self.parse(text, msg.topic)
                    if d is not None:
                        self.on_detect(parts[1], dev, d)

    def parse(self, text: str, topic: str) -> dict | None:
        try:
            return json.loads(text)
        except ValueError:
            self.log(self.c(YELLOW, f"JSON 아님 ({topic}): {text[:80]}"))
            return None

    def on_server_state(self, text: str) -> None:
        d = self.parse(text, "state") or {}
        state = d.get("state", "?")
        if state != self.server_state:
            self.server_state = state
            self.log(f"[server] 판정 = {self.c(BOLD, state)}")

    def on_detect(self, dev_id: str, dev: Device, d: dict) -> None:
        now = time.monotonic()
        seq = d.get("seq")
        prev = dev.last.get("seq")
        if isinstance(seq, int) and isinstance(prev, int):
            if seq > prev + 1:
                dev.lost += seq - prev - 1
            elif seq <= prev:
                self.log(self.c(YELLOW, f"[{dev_id}] seq {prev} → {seq} (보드 재시작?)"))
        face = bool(d.get("face"))
        if face != dev.face:
            self.log(f"[{dev_id}] {self.face_label(face)}  score {d.get('score', 0):.2f}  #{seq}")
        elif self.a.all:
            self.log(f"[{dev_id}] {self.face_label(face)}  score {d.get('score', 0):.2f}  "
                     f"infer {d.get('infer_ms', '?')}ms  #{seq}")
        dev.face, dev.last, dev.last_at = face, d, now
        dev.times.append(now)
        dev.count += 1

    def face_label(self, face: bool) -> str:
        return self.c(GREEN + BOLD, "Face Detected    ") if face else self.c(RED + BOLD, "Face Not Detected")

    # ---- 메인 스레드: 상태 줄 ----

    def status_line(self) -> str:
        if not self.connected:
            return self.c(RED, "브로커 연결 안 됨")
        if not self.devices:
            return self.c(GRAY, f"장치 신호 기다리는 중… ({self.a.prefix}/+/detect)")
        now = time.monotonic()
        parts = []
        for dev_id, dev in self.devices.items():
            if not dev.last_at:
                parts.append(f"{dev_id}: status {dev.status}, detect 없음")
                continue
            age_ms = (now - dev.last_at) * 1000
            if age_ms > self.a.timeout_ms:
                parts.append(self.c(YELLOW, f"{dev_id}: 신호 없음 {age_ms / 1000:.1f}s"))
                continue
            recent = [t for t in dev.times if now - t <= 2.0]
            hz = len(recent) / 2.0
            frames = [b for t, b in dev.frames if now - t <= 2.0]
            video = f"영상 {len(frames) / 2.0:.1f}fps {sum(frames) // max(1, len(frames)) // 1024}KB" if frames else "영상 없음"
            d = dev.last
            parts.append(f"{dev_id}: {self.face_label(bool(d.get('face')))} "
                         f"score {d.get('score', 0):.2f} · {hz:.1f}Hz · infer {d.get('infer_ms', '?')}ms "
                         f"· 받음 {dev.count} 유실 {dev.lost} · {video}")
        return " | ".join(parts) + f" | 판정 {self.server_state}"

    def run(self) -> None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ztmc-monitor-{os.getpid()}")
        client.on_connect, client.on_disconnect, client.on_message = (
            self.on_connect, self.on_disconnect, self.on_message)
        client.reconnect_delay_set(min_delay=1, max_delay=5)
        client.connect_async(self.a.host, self.a.port, keepalive=10)
        client.loop_start()
        try:
            while True:
                with self.lock:
                    line = self.status_line()
                print(f"\r\033[K{line}", end="", flush=True)
                time.sleep(0.2)
        except KeyboardInterrupt:
            print()
        finally:
            client.disconnect()
            client.loop_stop()


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("MQTT_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    ap.add_argument("--prefix", default=os.environ.get("MQTT_TOPIC_PREFIX", "ztmc"))
    ap.add_argument("--timeout-ms", type=int, default=int(os.environ.get("DEVICE_TIMEOUT_MS", "3000")),
                    help="이 시간 동안 detect가 없으면 '신호 없음' 표시")
    ap.add_argument("--all", action="store_true", help="detect 메시지를 전부 한 줄씩 기록")
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args()
    os.system("")  # Windows 콘솔에서 ANSI 색·줄 지우기 켜기
    Monitor(a).run()


if __name__ == "__main__":
    main()
