"""시연 데이터 수집 (팀원4). 보드 카메라가 모델에 넣는 그림 그대로를 PNG로 저장한다.

보드에 캡처 모드 펌웨어(-DCAPTURE_MODE, 팀원2)를 올리면 시리얼로 'FRAME W H <hex>' 줄이 나온다.
사용: python model/testing/capture.py COM10 --label face   (얼굴 있는 장면)
      python model/testing/capture.py COM10 --label none   (얼굴 없는 배경)
저장: model/testing/captures/<label>/<시각>_<번호>.png  (git에 안 올라감 → 모아서 팀원1에게 전달)

시리얼 포트는 한 프로그램만 열 수 있다. Arduino 시리얼 모니터는 닫고 실행한다.
"""
import argparse
import os
import time

import serial
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port"); ap.add_argument("--label", required=True)
    ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures"))
    a = ap.parse_args()
    out = os.path.join(a.out, a.label); os.makedirs(out, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    n = 0
    with serial.Serial(a.port, a.baud, timeout=2) as s:
        print(f"{a.port} 읽는 중 — Ctrl+C 로 끝. 저장 위치 {out}")
        try:
            while not a.max or n < a.max:
                line = s.readline().decode("ascii", "ignore").strip()
                if not line.startswith("FRAME "):
                    continue
                parts = line.split(" ")
                if len(parts) < 4:
                    continue
                w, h, hx = int(parts[1]), int(parts[2]), parts[3]
                if len(hx) != w * h * 2:
                    continue          # 줄이 잘렸다
                img = Image.frombytes("L", (w, h), bytes.fromhex(hx))
                p = os.path.join(out, f"{stamp}_{n:04d}.png")
                img.save(p); n += 1
                print(f"\r  {n}장", end="", flush=True)
        except KeyboardInterrupt:
            pass
    print(f"\n{n}장 저장: {out}")


if __name__ == "__main__":
    main()
