# Zero-Touch Media Control — 뼈대 설계

- 날짜: 2026-10-30
- 작성: 팀장(박민성) + Claude
- 근거 자료: `Zero_Touch_Media_Control.pdf`(2장), 팀프로젝트 AirStroke의 구조

## 1. 무엇을, 왜

ESP32-S3 카메라 보드가 **보드 안에서** 얼굴 인식 모델(Edge Impulse FOMO)을 돌려 얼굴이 있는지 판단한다.
얼굴이 있으면 PC 브라우저의 유튜브 영상을 자동 재생하고, 없으면 자동 일시정지한다.
3명이 하루 단위로 나눠서 동시에 개발하므로, 오늘은 **세 명이 바로 각자 작업을 시작할 수 있는 뼈대**를 세운다.
뼈대 단계에서 "가짜 ESP32 → 서버 → 유튜브 페이지 재생/정지"가 끝까지 돌아가야 한다.

## 2. 목표 / 비목표 / 실패 조건

**목표**
- 인식 모델은 ESP32 안에서 돈다(수업 요구사항).
- 얼굴이 보이면 재생, 사라지면 정지. 정지 직전 위치를 유지한다(유튜브 일시정지 그대로).
- 담당 폴더를 나눠 3명이 서로 충돌 없이 작업한다(AirStroke 방식).
- 지연 시간(추론 → 서버 → 브라우저)과 판정 통계를 측정해 발표 자료로 쓴다.

**비목표**
- 시선 방향 추적. 슬라이드에는 "시선"이라고 되어 있지만 실제 판정은 **얼굴이 있는지/없는지**만 본다.
- 여러 사람 구분, 여러 장치 동시 운용, 클라우드 배포, Docker.

**실패 조건 (동작은 해도 실패로 본다)**
- 판정이 흔들려 재생과 정지가 깜빡이듯 반복된다.
- 장치 연결이 끊겼는데 영상이 계속 재생된다.
- 한 사람의 작업이 다른 사람 폴더를 고쳐야만 진행된다(계약이 부족했다는 뜻).

## 3. 제약과 확인된 사실

- 보드: ESP32-S3, PSRAM 8MB, 플래시 8MB, COM10, USB-Serial/JTAG(esptool로 확인). 이 구성은 XIAO ESP32S3 Sense와 같다. 정확한 보드명은 펌웨어 담당이 확인한다.
- 이 PC의 아두이노 ESP32 코어는 3.3.12다. Edge Impulse의 ESP32 카메라 예제는 예전에 코어 2.0.x 기준이었다. **호환 여부를 첫 작업으로 확인한다**(→ 6절 위험).
- 모델은 Edge Impulse 공개 Face detection 프로젝트를 복제해 `Deployment → Arduino library`로 받는다(Edge Impulse 로그인 필요).
- 같은 Wi-Fi(LAN)에서만 동작한다. ESP32 → 서버 구간은 **MQTT**(강사 권장), 브로커는 PC에서 돌리는 Mosquitto(포트 1883, TLS·인증 없음, LAN 전용).
- Mosquitto 2.x는 기본 설정이면 자기 PC(localhost) 접속만 받는다. 저장소의 `broker/mosquitto.conf`로 LAN 접속을 열고, Windows 방화벽에서 1883 인바운드를 허용해야 한다(관리자 권한 1회).
- 브라우저 페이지는 PC에서 `http://localhost`로 연다. 폰 카메라를 쓰지 않으므로 HTTPS 인증서가 필요 없다.

## 4. 방식 (검토한 선택지)

| | 방식 | 장점 | 단점 |
|---|---|---|---|
| **1 (채택)** | ESP32 → PC 서버 → 유튜브 페이지 | 판정 안정화·로그·측정을 PC에서 빠르게 고침. AirStroke 구조 재사용. 담당 3개로 자연스럽게 나뉨 | PC 서버가 하나 더 필요 |
| 2 | ESP32가 웹페이지를 직접 제공 | 가장 단순, IoT 느낌 강함 | 고칠 때마다 펌웨어 재업로드, 측정·로그 어려움, 역할 분리 어려움 |

방식 1은 사용자가 골랐다. 판정 주체 선택지(ESP32 안 vs PC)는 수업 요구로 ESP32 안에서 판정하기로 확정했다.

**ESP32 → 서버 구간: WebSocket 대신 MQTT** (강사 권장, 사용자 확정). IoT 표준이고, 장치가 갑자기 끊기면 브로커가 대신 알려 주는 LWT(마지막 유언) 기능으로 연결 끊김 처리가 쉬워진다. 대가는 브로커 프로세스 하나(Mosquitto)를 더 실행하는 것. 서버 → 브라우저 구간은 그대로 WebSocket이다.

## 5. 구조

```
ESP32-S3 (카메라 + FOMO 추론)
   │  MQTT publish  ztmc/cam-1/detect · status · hello
   ▼
Mosquitto 브로커 (PC, :1883)
   │  MQTT subscribe  ztmc/+/#
   ▼
PC server (FastAPI + paho-mqtt)  ── 판정 안정화(디바운스) · 로그 · trace · 연결 감시
   │  (상태는 MQTT ztmc/state 로도 발행 — 다른 장치가 받아 쓸 수 있게)
   │  ws://localhost:8000/ws/player   state 메시지 (present / absent / no_device)
   ▼
브라우저 web/ (유튜브 IFrame API)  ── playVideo() / pauseVideo(), 상태 표시
```

- AirStroke의 Redis 자리를 MQTT 브로커가 대신한다. Docker는 쓰지 않는다.
- **재생/정지 판단은 서버 한 곳에서만 한다.** ESP32는 프레임마다 판정만 보내고, 브라우저는 서버가 보낸 상태를 따르기만 한다.

### 디렉터리와 담당

| 담당 | 폴더 | 할 일 |
|---|---|---|
| 팀장(박민성) | `server/`, `tools/`, `docs/`, 루트 파일 | 계약(프로토콜), 서버, 가짜 ESP32, 통합, 문서, 측정 |
| 펌웨어 담당 | `firmware/` | Edge Impulse 모델, 카메라 + 추론, Wi-Fi + MQTT 발행 |
| 웹 담당 | `web/` | 유튜브 페이지, 상태 표시, 수동 모드, 연결 끊김 표시 |

```
zero-touch-media/
├─ CLAUDE.md          # 항상 지킬 규칙, 문서 지도, 담당 표 (100줄 이하)
├─ HANDOFF.md         # 현재 상태, ## 남은 일, 교훈
├─ README.md          # 처음 실행하는 법
├─ .env.example       # 서버 설정 (설명 포함)
├─ environment.yml    # conda 환경 ztmc (python 3.11)
├─ broker/
│  └─ mosquitto.conf   # listener 1883 0.0.0.0, allow_anonymous true (LAN 전용)
├─ docs/
│  ├─ 01-overview.md  02-architecture.md  03-protocol.md
│  ├─ 04-firmware.md  05-web.md  06-roadmap.md  07-team.md
│  ├─ decisions.md    HISTORY.md
│  └─ superpowers/specs/   # 이 문서
├─ server/
│  ├─ ztmc_server/   main.py(FastAPI) · protocol.py(pydantic 모델) · presence.py(판정 안정화) · mqtt_in.py(구독) · hub.py(브라우저 연결 관리) · config.py
│  └─ tests/          # pytest: presence 상태기계, 메시지 검증, MQTT→WebSocket 통합
├─ tools/
│  └─ fake_esp32.py   # 키보드(f=얼굴 있음 / n=없음 / q=끊김) 또는 시나리오로 MQTT 발행
├─ web/
│  ├─ index.html  app.js  style.css   # 서버가 / 로 정적 제공
└─ firmware/
   ├─ zero_touch_cam/zero_touch_cam.ino
   ├─ zero_touch_cam/config.example.h   # Wi-Fi, 서버 주소, 기준값 (config.h는 git 제외)
   └─ README.md       # Edge Impulse 라이브러리 받는 법, 보드 설정, 업로드 방법
```

## 6. 계약 (docs/03-protocol.md의 초안)

공통 규칙(AirStroke와 같음): JSON 텍스트, `type` 필드로 구분, 모르는 필드와 모르는 `type`은 무시, 필드 추가는 자유, 삭제·이름 변경은 팀장 확인. 시각은 **서버 시계 기준 epoch ms**. ESP32 시계는 맞추지 않으므로 ESP32는 시각이 아니라 **걸린 시간(ms)** 만 보낸다.

**ESP32 → 브로커 (MQTT 토픽)** — 토픽 앞부분 `ztmc`는 `.env`의 `MQTT_TOPIC_PREFIX`

| 토픽 | 내용 | QoS | retain |
|---|---|---|---|
| `ztmc/{device_id}/status` | `online` / `offline` (문자열). 접속 직후 `online` 발행, **LWT로 `offline` 등록** | 1 | 예 |
| `ztmc/{device_id}/hello` | 장치 정보 JSON (아래) | 1 | 예 |
| `ztmc/{device_id}/detect` | 추론 결과 JSON (아래), 추론할 때마다 | 0 | 아니오 |

```jsonc
// hello
{"device_id": "cam-1", "fw": "0.1.0", "model": "face-fomo-96", "threshold": 0.6}
// detect
{"device_id": "cam-1", "seq": 12, "face": true, "score": 0.83, "count": 1, "dsp_ms": 8, "infer_ms": 45}
```
- `face`: 펌웨어 기준값(`threshold`) 이상인 얼굴이 하나라도 있으면 true. `score`는 가장 높은 값, 얼굴이 없으면 0.
- MQTT keepalive는 **5초**로 둔다(PubSubClient 기본 15초면 LWT가 20초 넘게 늦게 온다). 브로커는 keepalive×1.5(약 7.5초) 뒤 `offline`을 대신 발행한다.
- 그보다 빨리 알아채도록, 서버는 `DEVICE_TIMEOUT_MS`(3초) 동안 detect가 없어도 장치 없음으로 본다. 둘 중 먼저 오는 쪽을 따른다.
- PubSubClient 기본 버퍼가 256바이트라 `setBufferSize(512)`로 늘린다.

**서버 → 브로커**
- `ztmc/state` (QoS 1, retain): 아래 `state` 메시지와 같은 JSON. 다른 장치(예: LED 표시 보드)가 구독해서 쓸 수 있게 한다.

**서버 → 브라우저 (`/ws/player`)**
```jsonc
{"type": "state", "state": "present", "since": 1761800000000, "device": {"id": "cam-1", "connected": true}}
{"type": "detect", "seq": 12, "face": true, "score": 0.83, "infer_ms": 45,
 "trace": {"gw_recv": 1761800000123, "gw_sent": 1761800000124}}
```
- `state`: `present`(재생) | `absent`(정지) | `no_device`(정지 + 연결 끊김 표시). 바뀔 때와 접속 직후에 보낸다.
- `detect`: 상태 표시와 측정용 원본 판정. `trace.gw_recv`는 서버가 MQTT 메시지를 받은 시각. 화면 표시용이라 서버가 초당 `PLAYER_DETECT_HZ`(기본 10)로 줄여 보낸다.

**브라우저 → 서버**
```jsonc
{"type": "player", "event": "playing" | "paused" | "ended" | "manual_on" | "manual_off", "ts": <브라우저 ms>}
{"type": "pong", "t0": ..., "t1": ...}    // 시계 맞추기 (AirStroke와 같은 ping/pong)
```
- 서버는 `player` 이벤트를 로그와 측정(state 발송 → 실제 재생/정지까지 걸린 시간)에 쓴다.

**판정 안정화 (server/presence.py)** — `.env`로 조정
- `FACE_ON_MS`(기본 300): 얼굴이 이만큼 계속 보여야 present.
- `FACE_OFF_MS`(기본 1500): 얼굴이 이만큼 계속 안 보여야 absent. 잠깐 고개를 돌려도 멈추지 않게 길게 둔다.
- `MIN_SCORE`(기본 0.6): 서버 쪽 추가 기준값. 펌웨어 기준값보다 낮으면 효과 없다.
- `DEVICE_TIMEOUT_MS`(기본 3000): 이 시간 동안 메시지가 없으면 no_device.

**웹 페이지 동작**
- 영상 주소는 페이지의 입력칸에서 바꿀 수 있고, 기본값은 `.env`의 `DEFAULT_VIDEO_ID`를 `/api/config`로 받는다.
- 브라우저 자동재생 정책 때문에 첫 재생 전에는 사용자가 한 번 클릭해야 할 수 있다. 첫 화면에 "시작" 버튼을 둔다.
- 수동 모드 스위치: 켜면 서버 상태를 무시한다(시연·디버깅용).

## 7. 뼈대 범위 (오늘 팀장 + Claude가 만드는 것)

1. 저장소 `physical-ai-team/zero-touch-media` 생성(공개, AirStroke와 같음), `main` 기본 브랜치.
2. 문서 전부(5절 목록). `CLAUDE.md`에 문서 역할 표와 읽기 규칙(HANDOFF는 "남은 일" 절만, HISTORY는 grep)을 넣는다.
3. 서버: 위 계약 그대로 동작, pytest 통과.
4. `tools/fake_esp32.py`.
5. web/: **동작하는 최소 페이지**(시작 버튼, 유튜브 재생/정지, 현재 상태 한 줄). 꾸미기와 나머지는 웹 담당.
6. firmware/: 컴파일되는 **빈 스케치**(Wi-Fi 연결 + MQTT 연결(LWT 포함) + hello + 가짜 detect 발행), `config.example.h`, Edge Impulse 연결 방법 안내. 모델 붙이기는 펌웨어 담당.
7. Mosquitto 설치(winget `EclipseFoundation.Mosquitto`) — 이 PC에는 아직 없음. 팀원용 설치 방법은 README에.
8. 끝까지 확인: 브로커 + 서버 실행 → 가짜 ESP32 → 브라우저에서 재생/정지 확인. 실제 보드에 빈 스케치를 올려 서버에 hello가 오는지, 보드 USB를 뽑으면 정지하는지도 확인한다.

## 8. 위험과 첫 확인

- **Edge Impulse 라이브러리 + 코어 3.3.12 호환**: 펌웨어 담당의 첫 작업. 안 되면 보드 매니저에서 코어 2.0.17로 내리는 것을 기본 대안으로 한다(decisions.md에 기록).
- 카메라 핀 설정: 보드명이 확정되어야 정해진다. XIAO ESP32S3 Sense라면 `CAMERA_MODEL_XIAO_ESP32S3`.
- 학교·강의실 Wi-Fi가 기기 간 통신을 막으면 ESP32가 PC 브로커에 접속하지 못한다. 그때는 폰 핫스팟을 쓴다.
- Windows 방화벽이 1883을 막으면 같은 증상이 난다. 방화벽 규칙 추가는 관리자 권한이 필요하므로 사용자가 직접 한다(README에 명령 한 줄).
- 브로커는 PC IP를 주소로 쓰므로, 네트워크가 바뀌면 펌웨어 `config.h`의 브로커 주소를 고쳐 다시 올려야 한다.

## 9. Claude가 정한 것 (팀장이 확인할 것)

- 저장소 이름 `zero-touch-media`, 공개 저장소.
- 서버 스택: Python 3.11 + FastAPI + uvicorn + pydantic + **paho-mqtt 2.x**(별도 스레드에서 받고 asyncio로 넘김. aiomqtt는 Windows 이벤트 루프 제약이 있어 뺌), conda 환경 `ztmc`. Redis와 Docker는 쓰지 않음.
- 브로커: Mosquitto(winget). 토픽 이름 `ztmc/{device_id}/{status|hello|detect}`, `ztmc/state`.
- 판정 안정화 기본값(300ms / 1500ms / 0.6 / 3000ms).
- 펌웨어 MQTT 라이브러리: `PubSubClient`(knolleary), JSON은 `ArduinoJson` 7.
- 장치 1대만 지원(`device_id`는 나중 확장용으로만 둠).
- 팀원 이름은 아직 모르므로 문서에는 "펌웨어 담당", "웹 담당"으로 쓴다.

## 10. 구현자에게 맡기는 것

- 서버 내부 모듈 나누기, 로그 형식, 테스트 구성.
- 웹 페이지 디자인 전부(웹 담당).
- 펌웨어의 카메라 해상도, 추론 주기(펌웨어 담당, 계약만 지키면 됨).
