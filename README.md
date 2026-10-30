# Zero-Touch Media Control

**화면을 보는 순간 재생되고, 시선을 떼는 순간 멈추는 유튜브.**

ESP32-S3 카메라 보드가 **보드 안에서** 얼굴 인식 모델(Edge Impulse FOMO)을 돌리고, 결과를 MQTT로 PC에 보냅니다. PC 서버가 판정을 안정화해 브라우저의 유튜브를 자동으로 재생하거나 멈춥니다. 영상은 클라우드로 나가지 않고, 판정에 쓰는 것은 "얼굴이 있다/없다"뿐입니다.

| 상황 | 결과 |
|---|---|
| 얼굴이 0.3초 이상 보임 | 영상 자동 재생 |
| 얼굴이 1.5초 이상 안 보임 | 영상 자동 일시정지 (보던 위치 유지) |
| 보드가 3초 이상 신호 없음 / 끊김 | 정지 + "장치 없음" 표시 |

판정 시간은 서버 `.env`의 `FACE_ON_MS` / `FACE_OFF_MS`로 바꿉니다(기본 300 / 1500ms). 빈자리에서 잘못 재생되는 일이 잦으면 `FACE_ON_MS`를 500 정도로 늘립니다.

---

## 시스템 구조

```
 ┌──────────── ESP32-S3 (XIAO Sense) ────────────┐
 │ 카메라 OV3660 → 64×64 흑백 → FOMO 추론(51ms)  │
 └───────┬───────────────────────────────────────┘
         │ MQTT  ztmc/cam-1/detect  (초당 약 7회, 얼굴 여부·점수)
         │       ztmc/cam-1/frame   (초당 2장, JPEG — 화면 확인용)
         │       ztmc/cam-1/status  (online / offline = LWT)
         ▼
 ┌─ Mosquitto (PC, 1883) ─┐
 └───────┬────────────────┘
         ▼
 ┌─ 판정 서버 (FastAPI, presence.py) ─┐   재생/정지 판단은 여기 한 곳에서만
 │ 얼굴 0.3초 연속 → present           │
 │ 얼굴 1.5초 없음 → absent            │
 │ 신호 3초 없음  → no_device          │
 └───────┬─────────────────────────────┘
         │ WebSocket /ws/player
         ▼
 ┌─ 브라우저 ─────────────────────────────┐
 │ 유튜브 플레이어 (서버 판정을 따르기만) │
 │ 보드 카메라 PiP · 감지 모니터          │
 └────────────────────────────────────────┘
```

- ESP32 → 서버는 **MQTT만** 씁니다. 서버 → 브라우저는 WebSocket입니다. 규격: [docs/03-protocol.md](docs/03-protocol.md)
- ESP32는 프레임마다 판정만 보내고, 깜빡임을 막는 시간 조건(디바운스)은 서버가 적용합니다. 웹은 서버 상태를 따르기만 합니다.

---

## 팀과 역할

| 역할 | 이름 (GitHub) | 담당 폴더 | 한 일 |
|---|---|---|---|
| **팀장 · 팀원2 펌웨어** | **김세광** (`kimsegwang`) | `firmware/` | 실제 보드 연결, 카메라 + 모델 이식, 보드 크래시·인식 실패 원인 규명, MQTT `detect`·`frame` 발행, 캡처 모드 |
| 팀원1 모델 | 박민성 (`msungaffa`) | `model/` | 프로젝트 뼈대·문서, 공개 모델 선정, Edge Impulse 비교 실험 6개, WIDER FACE 로컬 학습(v19), PC 하네스, 팀원4 측정 도구 |
| 팀원3 브로커·서버·웹 | (`yunnyKim-610`) | `broker/` `server/` `web/` `tools/` | 감지 모니터(터미널·웹), 유튜브 주소 불러오기, 오류 안내, 보드 카메라 PiP(`frame` → WebSocket) |
| 팀원4 시연 데이터·정확도 측정 | – | `model/testing/` | 상황 11개 감지율·오탐률 측정(`measure.py`), 시연 장소 사진 수집(`capture.py`) |
| 문서 기여 | (`maraoj1004`) | `docs/` | 보드 사양 실측값 정리(PR #6) |

담당 폴더 밖은 고치지 않습니다. 브랜치는 `feat/<담당>-<내용>`이고 `main`은 PR + 다른 한 명의 승인으로만 병합합니다. 자세한 규칙은 [docs/07-team.md](docs/07-team.md)에 있습니다.

### 팀원별 작업 상세 (10-30 기준)

**김세광 (팀장, 펌웨어)**
- 환경 구축: conda `ztmc`, Mosquitto, arduino-cli, ESP32 코어 3.3.12
- 실제 보드 첫 연결: 가짜 detect → MQTT → 서버 → 웹 재생/정지 확인(PR #2). 보드 Wi-Fi 수신 약함(-92 dBm)을 찾아 핫스팟으로 해결
- **실제 추론 펌웨어**: XIAO Sense 카메라 → 크롭·축소 → Edge Impulse 추론 → MQTT
- **보드 크래시 원인 규명**: Edge Impulse SDK의 `ei_calloc`이 코어 3.x에서 16바이트 정렬을 하지 않아 ESP32-S3 가속(ESP-NN)이 버퍼 밖에 쓰던 문제. 펌웨어에서 해결했고, 팀원1이 겪은 "EON 모델 크래시"와 같은 원인
- **인식 실패 원인 규명**: Studio 테스트 데이터를 보드에 그대로 넣는 시험으로 모델이 정상임을 확인한 뒤, 카메라 입력의 색 순서(RGB/BGR)와 상하 뒤집힘을 찾아 수정
- USB 시리얼 막힘(detect 초당 4 → 0.4회) 해결, 카메라 JPEG `frame` 발행, 팀원4용 캡처 모드
- 두 모델을 보드에서 비교 측정(아래 표)

**박민성 (팀원1, 모델)**
- 프로젝트 뼈대(서버·가짜 ESP32·웹·펌웨어 스케치)와 문서 체계(CLAUDE.md, HANDOFF, HISTORY)
- 공개 후보 8개 중 public/96468 선정 → Edge Impulse 실험 6개 → E3(64×64) 채택(v18)
- Edge Impulse 무료 학습 시간이 바닥난 뒤 WIDER FACE로 **로컬 학습** → v19 채택. EI 라이브러리를 PC에서 그대로 돌리는 하네스로 F1 측정
- 팀원4용 측정·캡처 도구

**팀원3 (`yunnyKim-610`, 브로커·서버·웹)**
- 감지 신호 모니터: 터미널 `tools/monitor.py`, 웹 `monitor.html`
- 플레이어: 유튜브 주소(watch, youtu.be, shorts, `t=`) 붙여넣기, 마지막 영상 기억, 재생 불가 이유 안내
- 보드 카메라 PiP: MQTT `frame` → 서버 → WebSocket 바이너리 → 웹(항상 위 창 + 감지 배지)

---

## 모델 선택과 비교

> 정확도 수치는 기준(테스트셋)이 서로 달라 **같은 줄 안에서만** 비교하세요. 보드 실측은 모두 XIAO ESP32S3 Sense, 코어 3.3.12, PSRAM=opi입니다.

### 1) Edge Impulse 실험 (팀원1) — FFHQ 테스트셋 88장, float32 F1

| # | 바꾼 것 | 입력 | 백본 | F1 | 정밀도 / 재현율 | ESP-EYE 추정 | RAM |
|---|---|---|---|---|---|---|---|
| E0 | 공개 원본 (public/96468, v17) | 96 흑백 | MNv2 0.1 | 0.69 | 0.87 / 0.57 | 728 ms | 240K |
| E1 | 원본의 다른 실험 | 96 흑백 | MNv2 0.35 | 0.71 | 0.60 / 0.87 | 1075 ms | 244K |
| E2 | E0 + 학습률 0.001 + 증강 | 96 흑백 | MNv2 0.1 | 0.80 | 0.81 / 0.79 | 797 ms | 119K |
| **E3** | E2 + 입력 64×64 **(v18)** | 64 흑백 | MNv2 0.1 | **0.82** | 0.81 / 0.83 | **280 ms** | **69K** |
| E4 | E1 + 학습률 0.001 + 증강 | 96 흑백 | MNv2 0.35 | 0.80 | 0.93 / 0.69 | 990 ms | 115K |
| E5 | E3 + 입력 48×48 | 48 흑백 | MNv2 0.1 | 0.77 | 0.80 / 0.74 | 269 ms | 52K |

공개 원본은 학습이 덜 돼서(학습률 0.00015) 얼굴의 43%를 놓쳤습니다. 학습률과 증강만 고쳐도 F1이 0.69에서 0.80으로 올랐고, 입력을 64×64로 줄여도 정확도는 떨어지지 않으면서 2.6배 빨라졌습니다. ESP-EYE 추정 ms는 구형 ESP32 기준이라 **상대 비교용**입니다.

### 2) 로컬 학습 (팀원1) — WIDER FACE 검증 5,105장, EI 라이브러리를 PC에서 그대로 실행

| 모델 | 바꾼 것 | F1 | 정밀도 / 재현율 | PC 추론 |
|---|---|---|---|---|
| E3 (v18) | 기준선 (EON) | 0.642 | 0.66 / 0.62 | 9.9 ms |
| L1 | MNv2 0.35 ImageNet, 얼굴 가중치 100 | 0.51 | 0.34 / 0.98 | – |
| L2 | MNv2 0.1, 가중치 100 | 0.53 | 0.36 / 0.98 | – |
| **L3 (v19)** | MNv2 0.1, **가중치 10**, 30에폭, TFLite Micro | **0.748** | 0.74 / 0.76 | **4.4 ms** |

FFHQ(정면 인물 사진)로 학습한 E3는 다양한 실제 사진에서 F1이 0.64로 떨어졌습니다. WIDER FACE로 다시 학습한 v19가 같은 기준에서 0.748로 가장 좋았습니다.

### 3) 실제 보드 비교 (김세광) — 우리 카메라, 실제 사용 자세

| 모델 | 입력 | 엔진 | 보드 추론 | 초당 판정 | 앉은 정면 감지 | 빈자리 오탐 | 비고 |
|---|---|---|---|---|---|---|---|
| v17 공개 원본 (팀원1 측정) | 96 흑백 | EON | – | – | – | – | 정렬 버그로 **크래시** (원인 규명 후 해결 가능) |
| 공개 RGB 모델 (김세광 복제, EI val F1 0.886) | 96 RGB | EON | 143 ms | 약 4 | 64% (대비 보정 시), 화면 보는 자세 평균 0.11 | 2.5% | 크래시는 `ei_calloc` 수정으로 해결. 우리 카메라의 뿌연 영상에 약함 |
| **v19 (채택)** | 64 흑백 | TFLite Micro | **51 ms** (dsp 2) | **약 7** | **93%** (점수 0.7 이상 95/102, 평균 0.92) | 측정 예정 | 대비 보정은 오히려 역효과(93% → 36%)라 빼고 원본 영상 사용 |

**결론: v19를 씁니다.** 보드에서 3배 빠르고, 실제 사용 자세에서 훨씬 안정적으로 잡습니다.

알려진 약점: 얼굴이 화면을 가득 채울 만큼 가까우면 못 잡습니다(학습 데이터의 얼굴 크기가 15~55%). 시연 거리는 **50cm 이상**으로 둡니다. 팀원1이 v20(15~90%)으로 재학습을 준비 중입니다.

상세: [model/experiments.md](model/experiments.md) · [model/model-selection.md](model/model-selection.md) · [docs/04-firmware.md](docs/04-firmware.md) · [docs/HISTORY.md](docs/HISTORY.md)

---

## 처음 실행하기 (Windows)

### 보드 없이 (가짜 ESP32)
1. 설치: [Miniforge](https://github.com/conda-forge/miniforge), Mosquitto(`winget install EclipseFoundation.Mosquitto`)
   - Mosquitto 설치 프로그램이 Windows 서비스를 자동 시작해 1883 포트를 잡습니다. 관리자 PowerShell에서 `Stop-Service mosquitto; Set-Service mosquitto -StartupType Manual`
2. 환경: `conda env create -f environment.yml` → `conda activate ztmc` → `copy .env.example .env`
3. 터미널 3개:
   ```powershell
   & "C:\Program Files\mosquitto\mosquitto.exe" -c broker\mosquitto.conf -v   # 1: 브로커
   cd server; python -m ztmc_server                                         # 2: 서버
   python tools\fake_esp32.py                                               # 3: 가짜 ESP32 (f/n/l/x/q)
   ```
4. 브라우저 <http://localhost:8000> → "시작" → 가짜 ESP32 창에서 `f`(얼굴) / `n`(없음) / `x`(끊김)
5. 시험: 루트에서 `python -m pytest -q`

### 실제 보드
[docs/04-firmware.md](docs/04-firmware.md)를 따릅니다. 요약:
1. `firmware/zero_touch_cam/config.example.h` → `config.h`로 복사하고 Wi-Fi와 `MQTT_HOST`(PC IP) 입력
2. v19 모델 zip(팀원1에게 받음, git에 없음)을 `Documents\Arduino\libraries\`에 설치
3. `USE_FAKE_DETECT 0`으로 업로드 (FQBN `esp32:esp32:XIAO_ESP32S3:PSRAM=opi`)
4. PC 방화벽에서 TCP 1883 인바운드 허용
5. **카메라는 모니터 위 가운데**, 앉는 자리에서 50cm 이상

### 확인 도구
| 도구 | 용도 |
|---|---|
| <http://localhost:8000/monitor.html> | 얼굴 점수·판정 실시간 대시보드 |
| `python tools\monitor.py` | 터미널 모니터 (서버 없이 브로커 직접) |
| `python model\testing\measure.py` | 상황별 감지율·오탐률 표 (팀원4) |
| `python model\testing\capture.py COM5 --label face` | 보드 카메라 사진 수집 (`CAPTURE_MODE` 펌웨어) |

---

## 폴더 구조

```
broker/     Mosquitto 설정 (LAN 전용, 0.0.0.0:1883)
server/     판정 서버 (FastAPI, MQTT 구독 → presence 판정 → WebSocket)
web/        유튜브 플레이어, 감지 모니터, 보드 카메라 PiP
firmware/   ESP32-S3 펌웨어 (카메라 → 추론 → MQTT)
model/      모델 실험 기록, 로컬 학습 도구, 측정 도구(testing/)
tools/      가짜 ESP32, 터미널 모니터
docs/       설계·규격·담당별 안내·기록
```

## 문서
| 문서 | 내용 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 항상 지킬 규칙, 문서 지도 |
| [HANDOFF.md](HANDOFF.md) | 현재 상태와 담당별 남은 일 |
| [docs/01-overview.md](docs/01-overview.md) · [02-architecture.md](docs/02-architecture.md) | 개요, 구조 |
| [docs/03-protocol.md](docs/03-protocol.md) | MQTT 토픽과 메시지, WebSocket 규격 |
| [docs/04-firmware.md](docs/04-firmware.md) | 펌웨어 설치·설정·겪은 문제 |
| [docs/05-web.md](docs/05-web.md) | 웹 페이지 |
| [docs/decisions.md](docs/decisions.md) | 주요 결정과 이유 |
| [docs/HISTORY.md](docs/HISTORY.md) | 날짜별 작업 기록과 측정 |

## 알려진 문제
- 보드 Wi-Fi 수신이 약합니다(공유기 앞에서도 -65 dBm). 안테나를 점검하기 전까지는 폰 핫스팟을 보드 가까이 둡니다.
- 웹: 유튜브 API가 캐시로 빨리 준비되면 "플레이어가 준비되지 않았습니다"에 멈출 수 있습니다(스크립트 로딩 순서). 팀원3에게 전달했습니다. 당장은 Ctrl+Shift+R로 피할 수 있습니다.
- 빈자리 오탐률, 옆얼굴, 1~2m 거리는 아직 측정 전입니다(팀원4).

## 데이터 출처와 라이선스
- v19 학습 데이터: **WIDER FACE** (Yang et al., CVPR 2016), Hugging Face 미러 `CUHK-CSE/wider_face`. CC BY-NC-ND 4.0이라 비상업 수업 프로젝트에서만 쓰고, 데이터와 v19 zip은 공개 저장소에 올리지 않습니다.
- 공개 원본 모델: Edge Impulse public/96468 (Louis Moreau, FFHQ 일부), BSD-3-Clause-Clear
