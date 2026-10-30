# 2. 구조

```
ESP32-S3 (카메라 + FOMO 추론)          firmware/
   │ MQTT publish  ztmc/cam-1/{status,hello,detect}
   ▼
Mosquitto 브로커 (PC :1883)           broker/mosquitto.conf
   │ MQTT subscribe  ztmc/+/#
   ▼
서버 (FastAPI + paho-mqtt)            server/ztmc_server/
   │  presence.py  판정 안정화(디바운스) — 재생/정지 판단은 여기 한 곳
   │  → MQTT ztmc/state (retain)
   │ WebSocket /ws/player
   ▼
브라우저 (유튜브 IFrame API)           web/   (서버가 http://localhost:8000/ 로 제공)
```

| 서버 파일 | 역할 |
|---|---|
| `config.py` | `.env` 읽기 |
| `protocol.py` | 메시지 형식(pydantic). 규격의 기준 코드 |
| `presence.py` | 상태기계 no_device / absent / present. 시각을 인자로 받아 네트워크 없이 시험 |
| `mqtt_in.py` | paho 스레드 → asyncio 큐 |
| `hub.py` | 브라우저 연결 목록, 전체 발송 |
| `main.py` | Engine(입력→판정→출력), HTTP·WebSocket 경로 |

HTTP: `GET /health`(상태·통계), `GET /api/config`(웹이 쓰는 설정), `/`(web/ 정적 파일).
