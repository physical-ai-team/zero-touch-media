# 3. 프로토콜

- 기준 코드: [server/ztmc_server/protocol.py](../server/ztmc_server/protocol.py). 문서와 다르면 코드가 맞다(그리고 문서를 고친다).
- JSON 텍스트. 모르는 필드·모르는 `type`은 무시. 필드 **추가는 자유**, 삭제·이름 변경은 세 명 합의.
- 시각은 **서버 시계 epoch ms**. ESP32 시계는 맞추지 않으므로 ESP32는 **걸린 시간(ms)** 만 보낸다.
- 토픽 앞부분 `ztmc`는 `.env`의 `MQTT_TOPIC_PREFIX`, `cam-1`은 펌웨어 `DEVICE_ID`.

## MQTT — ESP32 → 브로커 → 서버

| 토픽 | 내용 | QoS | retain |
|---|---|---|---|
| `ztmc/{device_id}/status` | 문자열 `online` / `offline`. 접속 직후 `online`, **LWT로 `offline` 등록** | 1 | 예 |
| `ztmc/{device_id}/hello` | 장치 정보 JSON | 1 | 예 |
| `ztmc/{device_id}/detect` | 추론 결과 JSON, 추론할 때마다 | 0 | 아니오 |
| `ztmc/{device_id}/frame` | 카메라 화면 **JPEG 바이너리**(JSON 아님), 초당 1~2장 — **추가 제안, 세 명 합의 대기** | 0 | 아니오 |

```jsonc
// hello
{"device_id": "cam-1", "fw": "0.1.0", "model": "face-fomo-96", "threshold": 0.6}
// detect
{"device_id": "cam-1", "seq": 12, "face": true, "score": 0.83, "count": 1, "dsp_ms": 8, "infer_ms": 45}
```
- `face`: `threshold` 이상인 얼굴이 하나라도 있으면 true. `score`: 가장 높은 값(없으면 0). `count`: 기준 이상 얼굴 수.
- `frame`: 화면 확인용(웹 "보드 카메라"·PiP 창). **판정에는 쓰지 않는다.** 보내지 않아도 나머지는 그대로 동작한다.
  - 권장: 추론에 쓰는 그 프레임(320×240 흑백)을 `frame2jpg(fb, 60, &jpg, &len)`(`img_converters.h`)로 JPEG 변환, 수 KB.
  - PubSubClient 버퍼(512)보다 크므로 나눠 보낸다: `mqtt.beginPublish(topicFrame, len, false); mqtt.write(jpg, len); mqtt.endPublish(); free(jpg);`
  - 빈도는 `config.h`의 값으로(예 `FRAME_INTERVAL_MS 500`). Wi-Fi가 약하면 늘리거나 끈다. 서버는 `FRAME_MAX_BYTES`(기본 100000)보다 크거나 JPEG가 아니면 버린다.
- keepalive **5초** → 갑자기 끊기면 약 7.5초 뒤 브로커가 `offline` 발행. 서버는 그보다 먼저 `DEVICE_TIMEOUT_MS`(3초) 동안 detect가 없으면 장치 없음으로 본다.

## MQTT — 서버 → 브로커
- `ztmc/state` (QoS 1, retain): 아래 `state` 메시지와 같은 JSON. 다른 장치(LED 등)가 구독해 쓸 수 있다.

## WebSocket `/ws/player` — 서버 → 브라우저
```jsonc
{"type": "state", "state": "present", "since": 1761800000000,
 "device": {"id": "cam-1", "connected": true, "fw": "0.1.0", "model": "face-fomo-96"}}
{"type": "detect", "device_id": "cam-1", "seq": 12, "face": true, "score": 0.83, "count": 1,
 "dsp_ms": 8, "infer_ms": 45, "trace": {"gw_recv": 1761800000123, "gw_sent": 1761800000124}}
{"type": "ping", "t0": 1761800000000}
```
- `state`: `present`(재생) | `absent`(정지) | `no_device`(정지 + 끊김 표시). 접속 직후 1번, 바뀔 때마다.
- `detect`: 화면 표시·측정용. `PLAYER_DETECT_HZ`(기본 10)로 줄여 보낸다. 판정에는 모든 detect를 쓴다.
- **바이너리 메시지** = 보드 카메라 JPEG 한 장(MQTT `frame` 그대로). `PLAYER_FRAME_HZ`(기본 5)로 줄여 보낸다. 브라우저는 `ws.binaryType = "blob"`으로 받아 텍스트(JSON)와 구분한다.

## WebSocket — 브라우저 → 서버
```jsonc
{"type": "player", "event": "playing", "ts": 1761800000500}   // playing|paused|ended|manual_on|manual_off
{"type": "pong", "t0": 1761800000000, "t1": 1761800000003}     // ping에 바로 응답 (시계 맞추기)
```

## 판정 규칙 (server/ztmc_server/presence.py, 값은 .env)
| 키 | 기본 | 의미 |
|---|---|---|
| `FACE_ON_MS` | 300 | 얼굴이 계속 보여야 present |
| `FACE_OFF_MS` | 1500 | 얼굴이 계속 안 보여야 absent (잠깐 고개 돌림은 무시) |
| `MIN_SCORE` | 0.6 | 서버 쪽 추가 기준 |
| `DEVICE_TIMEOUT_MS` | 3000 | detect가 없으면 no_device |

no_device에서 detect가 오면 absent부터 다시 시작한다(바로 재생하지 않음).
