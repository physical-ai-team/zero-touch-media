"""실제 보드 정확도 측정 (팀원4). 브로커의 detect 메시지를 상황별로 모아 표로 만든다.

준비: 브로커가 켜져 있고 보드가 실제 추론 펌웨어(USE_FAKE_DETECT 0)로 MQTT에 붙어 있어야 한다.
사용: python model/testing/measure.py [--host 127.0.0.1] [--secs 20] [--out model/testing/results]

상황(시나리오)마다 Enter → 정해진 시간 동안 detect 를 모은다.
- 얼굴 있는 상황: 감지율(face=true 비율)이 높을수록 좋다.
- 얼굴 없는 상황: 오탐률(face=true 비율)이 낮을수록 좋다.
결과는 CSV(프레임별)와 요약 표(markdown)로 저장된다.
"""
import argparse
import csv
import json
import os
import statistics
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

# (이름, 얼굴 있음?, 설명)
SCENARIOS = [
    ("front_50cm", True, "정면, 카메라에서 50cm"),
    ("front_1m", True, "정면, 1m"),
    ("front_2m", True, "정면, 2m (시연 자리에서 가장 먼 위치)"),
    ("side_45", True, "고개 45도 옆으로"),
    ("down_phone", True, "휴대폰 보듯 고개 숙임"),
    ("glasses_or_mask", True, "안경·모자·마스크 중 하나"),
    ("dark", True, "조명 어둡게(불 하나 끄기)"),
    ("two_people", True, "두 명"),
    ("empty_seat", False, "빈 의자/빈 자리"),
    ("walk_by", False, "뒤로 사람이 지나감(카메라 보지 않음)"),
    ("poster_or_objects", False, "얼굴 없는 물건·옷·모니터 화면"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--prefix", default="ztmc"); ap.add_argument("--secs", type=float, default=20)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    ap.add_argument("--tag", default="", help="모델 버전 등 메모 (예: v18)")
    ap.add_argument("--only", nargs="*", help="이 이름의 상황만")
    a = ap.parse_args()

    lock = threading.Lock()
    buf = []
    info = {}

    def on_msg(_c, _u, m):
        try:
            d = json.loads(m.payload)
        except Exception:
            return
        if m.topic.endswith("/hello"):
            info.update(d); return
        d["_t"] = time.time()
        with lock:
            buf.append(d)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.on_message = on_msg
    c.connect(a.host, a.port)
    c.subscribe(f"{a.prefix}/+/detect"); c.subscribe(f"{a.prefix}/+/hello")
    c.loop_start()
    time.sleep(1.5)
    with lock:
        n0 = len(buf)
    if not n0:
        print("detect 메시지가 안 들어온다. 브로커 주소·보드 전원·Wi-Fi 를 확인하고 다시 실행.")
        return
    print(f"보드 연결됨: {info.get('device_id', '?')} 모델={info.get('model', '?')} fw={info.get('fw', '?')}")

    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    rows, summary = [], []
    for name, has_face, desc in SCENARIOS:
        if a.only and name not in a.only:
            continue
        r = input(f"\n[{name}] {desc}\n  준비되면 Enter (s=건너뛰기, q=끝): ").strip().lower()
        if r == "q":
            break
        if r == "s":
            continue
        with lock:
            buf.clear()
        t0 = time.time()
        while time.time() - t0 < a.secs:
            time.sleep(0.5)
            with lock:
                k = sum(1 for d in buf if d.get("face"))
                n = len(buf)
            print(f"\r  {time.time() - t0:4.1f}s  프레임 {n}  얼굴 {k}", end="", flush=True)
        with lock:
            got = list(buf)
        print()
        if not got:
            print("  프레임이 없다 — 건너뜀"); continue
        pos = [d for d in got if d.get("face")]
        rate = len(pos) / len(got)
        infer = [d["infer_ms"] for d in got if d.get("infer_ms") is not None]
        scores = [d.get("score", 0) for d in pos]
        s = dict(scenario=name, desc=desc, has_face=has_face, frames=len(got), face_frames=len(pos),
                 rate=rate, good=rate if has_face else 1 - rate,
                 score_avg=statistics.mean(scores) if scores else 0,
                 infer_ms=statistics.median(infer) if infer else None,
                 fps=len(got) / a.secs)
        summary.append(s)
        kind = "감지율" if has_face else "오탐률"
        print(f"  → {kind} {rate * 100:.0f}%  (평균 점수 {s['score_avg']:.2f}, 추론 {s['infer_ms']} ms, {s['fps']:.1f} fps)")
        for d in got:
            rows.append(dict(scenario=name, has_face=has_face, t=round(d["_t"] - t0, 3), face=d.get("face"),
                             score=d.get("score"), count=d.get("count"), infer_ms=d.get("infer_ms"),
                             dsp_ms=d.get("dsp_ms"), seq=d.get("seq")))
    c.loop_stop()
    if not summary:
        return

    base = os.path.join(a.out, f"{stamp}{'-' + a.tag if a.tag else ''}")
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    face_s = [s for s in summary if s["has_face"]]; none_s = [s for s in summary if not s["has_face"]]
    lines = [f"# 정확도 측정 {stamp} {a.tag}", "",
             f"보드 {info.get('device_id', '?')}, 모델 {info.get('model', '?')}, 상황당 {a.secs:.0f}초", "",
             "| 상황 | 설명 | 얼굴 | 프레임 | 얼굴 판정 | 감지율/오탐률 | 평균 점수 | 추론 ms | fps |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        kind = "감지" if s["has_face"] else "오탐"
        lines.append(f"| {s['scenario']} | {s['desc']} | {'O' if s['has_face'] else 'X'} | {s['frames']} | {s['face_frames']} "
                     f"| {kind} {s['rate'] * 100:.0f}% | {s['score_avg']:.2f} | {s['infer_ms']} | {s['fps']:.1f} |")
    lines.append("")
    if face_s:
        lines.append(f"- 얼굴 있는 상황 평균 감지율: **{statistics.mean(s['rate'] for s in face_s) * 100:.0f}%**")
    if none_s:
        lines.append(f"- 얼굴 없는 상황 평균 오탐률: **{statistics.mean(s['rate'] for s in none_s) * 100:.0f}%**")
    open(base + ".md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n저장: {base}.md, {base}.csv")


if __name__ == "__main__":
    main()
