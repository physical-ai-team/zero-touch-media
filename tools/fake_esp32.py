"""가짜 ESP32. 보드 없이 서버·웹을 개발할 때 쓴다. 진짜 펌웨어와 같은 토픽·JSON을 보낸다(docs/03-protocol.md).

    python tools/fake_esp32.py                 # 키보드로 조작
    python tools/fake_esp32.py --scenario      # 얼굴 5초 있음 / 5초 없음 반복
    python tools/fake_esp32.py --host 192.168.0.10
    python tools/fake_esp32.py --frame-hz 0     # 카메라 영상(frame) 안 보냄

키보드(입력 후 Enter):  f = 얼굴 있음   n = 얼굴 없음   l = 낮은 신뢰도(0.4)   x = 갑자기 끊김(LWT 시험)   q = 정상 종료
"""

from __future__ import annotations

import argparse
import json
import random
import threading
import io
import time

import paho.mqtt.client as mqtt

try:
    from PIL import Image, ImageDraw
except ImportError:  # 영상 없이도 detect는 보낸다
    Image = None


def fake_frame(face: bool, seq: int) -> bytes:
    """보드 카메라 대신 320x240 흑백 JPEG. 얼굴 있음이면 웃는 얼굴을 그린다."""
    im = Image.new("L", (320, 240), 90)
    d = ImageDraw.Draw(im)
    if face:
        d.ellipse((110, 50, 210, 180), fill=200)
        d.ellipse((135, 90, 150, 105), fill=40)
        d.ellipse((170, 90, 185, 105), fill=40)
        d.arc((135, 110, 185, 155), 20, 160, fill=40, width=4)
    d.text((8, 220), f"FAKE CAM #{seq}  {'FACE' if face else 'NO FACE'}", fill=255)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--prefix", default="ztmc")
    ap.add_argument("--device", default="cam-1")
    ap.add_argument("--hz", type=float, default=5.0, help="detect 발행 빈도")
    ap.add_argument("--frame-hz", type=float, default=2.0, help="카메라 영상(JPEG) 발행 빈도, 0이면 안 보냄")
    ap.add_argument("--scenario", action="store_true", help="키보드 대신 5초마다 얼굴 있음/없음 반복")
    a = ap.parse_args()

    base = f"{a.prefix}/{a.device}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"fake-{a.device}")
    # 진짜 펌웨어와 같게: LWT로 offline 등록, keepalive 5초
    client.will_set(f"{base}/status", "offline", qos=1, retain=True)
    client.connect(a.host, a.port, keepalive=5)
    client.loop_start()
    client.publish(f"{base}/status", "online", qos=1, retain=True)
    client.publish(
        f"{base}/hello",
        json.dumps({"device_id": a.device, "fw": "fake-0.1", "model": "fake", "threshold": 0.6}),
        qos=1, retain=True,
    )
    print(f"connected to {a.host}:{a.port} as {a.device}")

    state = {"face": False, "score": 0.0, "run": True}

    def sender():
        seq = 0
        while state["run"]:
            seq += 1
            infer = random.uniform(35, 55)
            msg = {
                "device_id": a.device, "seq": seq, "face": state["face"],
                "score": round(state["score"], 2), "count": 1 if state["face"] else 0,
                "dsp_ms": 6, "infer_ms": round(infer, 1),
            }
            client.publish(f"{base}/detect", json.dumps(msg), qos=0)
            time.sleep(1.0 / a.hz)

    def frame_sender():
        seq = 0
        while state["run"]:
            seq += 1
            client.publish(f"{base}/frame", fake_frame(state["face"], seq), qos=0)
            time.sleep(1.0 / a.frame_hz)

    threading.Thread(target=sender, daemon=True).start()
    if a.frame_hz > 0:
        if Image is None:
            print("Pillow가 없어 카메라 영상은 안 보냄 (pip install -r requirements-dev.txt)")
        else:
            threading.Thread(target=frame_sender, daemon=True).start()

    def set_face(face: bool, score: float):
        state["face"], state["score"] = face, score
        print(f"→ face={face} score={score}")

    try:
        if a.scenario:
            while True:
                set_face(True, 0.85)
                time.sleep(5)
                set_face(False, 0.0)
                time.sleep(5)
        print(__doc__.split("키보드", 1)[1].strip())
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "f":
                set_face(True, 0.85)
            elif cmd == "n":
                set_face(False, 0.0)
            elif cmd == "l":
                set_face(True, 0.4)
            elif cmd == "x":
                # 전원이 갑자기 꺼진 것처럼: DISCONNECT 없이 소켓만 닫는다 → 브로커가 LWT(offline) 발행
                state["run"] = False
                client.loop_stop()
                client.socket().close()
                print("socket closed without DISCONNECT; broker will publish LWT after keepalive×1.5")
                return
            elif cmd == "q":
                break
    except (KeyboardInterrupt, EOFError):
        pass
    state["run"] = False
    client.publish(f"{base}/status", "offline", qos=1, retain=True).wait_for_publish(2)
    client.disconnect()
    client.loop_stop()


if __name__ == "__main__":
    main()
