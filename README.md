# Zero-Touch Media Control

**화면을 보는 순간 재생되고, 시선을 떼는 순간 멈추는 유튜브.**

ESP32-S3 카메라 보드가 **보드 안에서** 얼굴 인식 모델(Edge Impulse FOMO)을 돌리고, 결과를 MQTT로 PC에 보냅니다. PC 서버가 판정을 안정화해 브라우저의 유튜브를 자동으로 재생하거나 멈춥니다. 영상은 클라우드로 나가지 않고, 판정에 쓰는 것은 "얼굴이 있다/없다"뿐입니다.

| 상황 | 결과 |
|---|---|
| 얼굴이 0.3초 이상 보임 | 영상 자동 재생 |
| 얼굴이 1.5초 이상 안 보임 | 영상 자동 일시정지 (보던 위치 유지) |
| 보드가 6초 이상 신호 없음 / 끊김 | 정지 + "장치 없음" 표시 |

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
 │ 신호 6초 없음  → no_device          │
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

| 이름 (GitHub) | 맡은 일 | 담당 폴더 |
|---|---|---|
| **김세광** (`kimsegwang`) · 팀장 | 펌웨어: 보드·카메라, 모델 이식, MQTT 발행 | `firmware/` |
| **박민성** (`msungaffa`) | 모델: 선정·학습·최적화, 프로젝트 뼈대 | `model/` |
| **김정윤** (`yunnyKim-610`) | 브로커·서버·웹, 모니터링, 통합 | `broker/` `server/` `web/` `tools/` |
| **조아람** (`maraoj1004`) | 보드 사양 검증, 시연 데이터·정확도 측정 | `model/testing/` |

담당 폴더 밖은 고치지 않습니다. 브랜치는 `feat/<담당>-<내용>`이고, `main`은 PR을 올린 뒤 다른 한 명이 승인해야 병합됩니다. 자세한 규칙은 [docs/07-team.md](docs/07-team.md)에 있습니다.

### 각자 한 일 (10-30 기준)

**박민성 — 모델 · 프로젝트 뼈대**
- **프로젝트 뼈대**를 처음 세움
  - 판정 서버의 상태기계(present / absent / no_device)
  - 키보드나 시나리오로 조작하는 가짜 ESP32
  - 최소 유튜브 페이지, 펌웨어 스케치(Wi-Fi + MQTT + LWT)
  - pytest 14개
- 문서 체계: `CLAUDE.md`(규칙), `HANDOFF.md`(남은 일), `docs/HISTORY.md`(기록), 담당별 안내 문서
- **모델 선정**: Edge Impulse 공개 얼굴 검출 후보 8개를 비교해 가장 가벼운 public/96468 선택
- **Edge Impulse 비교 실험 6개**
  - 공개 원본이 학습 부족(재현율 0.57)임을 찾음
  - 학습률·증강 조정과 입력 64×64 축소로 F1 0.69 → 0.82, 추정 속도 2.6배, RAM 1/3.5 (v18)
- **로컬 학습 파이프라인**: Edge Impulse 무료 학습 시간이 바닥나자 직접 구축
  - WIDER FACE에서 시연 상황과 비슷한 64×64 학습 데이터 41,067장 생성(`build_dataset.py`)
  - Edge Impulse FOMO와 같은 구조로 학습(`train_fomo.py`)
  - Edge Impulse 라이브러리에 새 모델을 끼우는 도구(`swap_model.py`)
  - 라이브러리를 PC에서 통째로 돌려 F1을 재는 하네스(`pc_harness/`)
- 얼굴 가중치 조정(100 → 10)으로 오탐을 줄여 **v19 완성**
  - F1 0.748로 v18(0.642)보다 높고, PC 추론은 절반
  - 보드 실측 50 ms로 채택
- 펌웨어 인수인계 문서, 정확도 측정 도구(`measure.py` 11개 상황, `capture.py`), 데이터 출처·라이선스 정리, 가까운 얼굴 대응 v20 준비

**김정윤 — 브로커 · 서버 · 웹**
- **감지 모니터 두 가지**
  - 터미널 `tools/monitor.py`: 얼굴 여부·점수·초당 횟수·추론 시간·유실을 한 줄로 보여 주고, 바뀔 때만 기록
  - 웹 대시보드 `monitor.html`: 최근 30초 타임라인
  - 가짜 ESP32로 반응 시간 확인(재생 0.32초, 정지 1.51초)
- **유튜브 플레이어 개선**
  - 주소 붙여넣기 지원(watch, youtu.be, shorts, embed, live, `t=` 시작 시각, 9가지 형식 시험), 마지막 영상 기억
  - 재생할 수 없는 이유 안내: 임베드 막힘(101/150), 비공개, "시작" 안 누름, 얼굴 대기
- **보드 카메라 PiP**
  - 화면 위에 항상 떠 있는 창에 감지 배지를 겹쳐 표시. 처음엔 PC 웹캠이었다가 보드 카메라로 전환
  - 전송 방식 설계: MQTT `frame` → 서버 → WebSocket 바이너리
- **서버의 `frame` 처리**
  - 판정과 분리하고, 브라우저로는 초당 횟수를 제한해 전달(`PLAYER_FRAME_HZ`)
  - JPEG가 아니거나 너무 큰 데이터는 버림(`FRAME_MAX_BYTES`)
  - 시험 추가(15개)
- 가짜 ESP32가 가짜 카메라 화면을 보내게 해서, 보드 없이 PiP 시험 가능
- 웹 스크립트를 브라우저 화면 없이 Edge/Chrome에서 실행해 확인

**조아람 — 보드 검증 · 측정**
- 보드 사양 실측과 문서화
  - esptool로 칩 정보 확인: ESP32-S3 QFN56 rev0.2, PSRAM 8MB, 플래시 8MB
  - 빌드 설정(FQBN) `XIAO_ESP32S3:PSRAM=opi` 확정 → `docs/04-firmware.md` 갱신(PR #6)
- 시연 장소 데이터 수집과 실제 정확도 측정을 맡음
  - 준비된 도구: `measure.py`(감지율·오탐률), `capture.py`(사진 수집)
  - 펌웨어에 캡처 모드가 들어가 바로 시작 가능

**김세광 — 팀장 · 펌웨어**
- **실제 보드 첫 연결**: 가짜 detect로 보드 → MQTT → 서버 → 웹 재생/정지까지 처음 확인(PR #2). 보드 Wi-Fi 수신이 약한 문제(-92 dBm)를 찾아 핫스팟으로 해결
- **실제 추론 펌웨어**
  - XIAO Sense 카메라 → 크롭·축소 → Edge Impulse 추론 → MQTT `detect`
  - 초당 약 7회, 추론 51 ms
- **보드 크래시 원인 규명**
  - Edge Impulse SDK의 `ei_calloc`이 코어 3.x에서 메모리를 16바이트 정렬하지 않아, ESP32-S3 가속 코드가 버퍼 밖에 쓰던 버그
  - 라이브러리는 그대로 두고 펌웨어에서 해결. EON 모델이 보드에서 죽던 원인과 같음
- **인식 실패 원인 규명**
  - Studio 테스트 데이터를 보드에 그대로 넣어 모델이 정상임을 먼저 확인
  - 시리얼로 모델 입력 이미지를 뽑아 보고, 카메라 색 순서(RGB/BGR)와 상하 뒤집힘을 찾아 수정
- **모델 비교와 채택**: 공개 RGB 모델과 v19를 실제 카메라·실제 자세로 측정해 v19 채택(아래 표 3). v19에는 대비 보정이 역효과임도 확인
- 그 밖에
  - USB 시리얼 막힘 해결: PC가 안 읽으면 detect가 초당 4회 → 0.4회로 떨어지던 문제
  - 웹 PiP용 카메라 JPEG `frame` 발행, 사진 수집용 캡처 모드
  - 웹 플레이어의 스크립트 로딩 순서 버그를 찾아 김정윤에게 전달

---

## 모델 선택과 비교

> 정확도 수치는 기준(테스트셋)이 서로 달라 **같은 줄 안에서만** 비교하세요. 보드 실측은 모두 XIAO ESP32S3 Sense, 코어 3.3.12, PSRAM=opi입니다.

### 1) Edge Impulse 실험 (박민성) — FFHQ 테스트셋 88장, float32 F1

| # | 바꾼 것 | 입력 | 백본 | F1 | 정밀도 / 재현율 | ESP-EYE 추정 | RAM |
|---|---|---|---|---|---|---|---|
| E0 | 공개 원본 (public/96468, v17) | 96 흑백 | MNv2 0.1 | 0.69 | 0.87 / 0.57 | 728 ms | 240K |
| E1 | 원본의 다른 실험 | 96 흑백 | MNv2 0.35 | 0.71 | 0.60 / 0.87 | 1075 ms | 244K |
| E2 | E0 + 학습률 0.001 + 증강 | 96 흑백 | MNv2 0.1 | 0.80 | 0.81 / 0.79 | 797 ms | 119K |
| **E3** | E2 + 입력 64×64 **(v18)** | 64 흑백 | MNv2 0.1 | **0.82** | 0.81 / 0.83 | **280 ms** | **69K** |
| E4 | E1 + 학습률 0.001 + 증강 | 96 흑백 | MNv2 0.35 | 0.80 | 0.93 / 0.69 | 990 ms | 115K |
| E5 | E3 + 입력 48×48 | 48 흑백 | MNv2 0.1 | 0.77 | 0.80 / 0.74 | 269 ms | 52K |

공개 원본은 학습이 덜 돼서(학습률 0.00015) 얼굴의 43%를 놓쳤습니다. 학습률과 증강만 고쳐도 F1이 0.69에서 0.80으로 올랐고, 입력을 64×64로 줄여도 정확도는 떨어지지 않으면서 2.6배 빨라졌습니다. ESP-EYE 추정 ms는 구형 ESP32 기준이라 **상대 비교용**입니다.

### 2) 로컬 학습 (박민성) — WIDER FACE 검증 5,105장, EI 라이브러리를 PC에서 그대로 실행

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
| v17 공개 원본 (박민성 측정) | 96 흑백 | EON | – | – | – | – | 정렬 버그로 **크래시** (원인 규명 후 해결 가능) |
| 공개 RGB 모델 (김세광 복제, EI val F1 0.886) | 96 RGB | EON | 143 ms | 약 4 | 64% (대비 보정 시), 화면 보는 자세 평균 0.11 | 2.5% | 크래시는 `ei_calloc` 수정으로 해결. 우리 카메라의 뿌연 영상에 약함 |
| **v19 (채택)** | 64 흑백 | TFLite Micro | **51 ms** (dsp 2) | **약 7** | **93%** (점수 0.7 이상 95/102, 평균 0.92) | 측정 예정 | 대비 보정은 오히려 역효과(93% → 36%)라 빼고 원본 영상 사용 |

**결론: v19를 씁니다.** 보드에서 3배 빠르고, 실제 사용 자세에서 훨씬 안정적으로 잡습니다.

알려진 약점: 얼굴이 화면을 가득 채울 만큼 가까우면 못 잡습니다(학습 데이터의 얼굴 크기가 15~55%). 시연 거리는 **50cm 이상**으로 둡니다. 박민성이 v20(15~90%)으로 재학습을 준비 중입니다.

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
2. v19 모델 zip(박민성에게 받음, git에 없음)을 `Documents\Arduino\libraries\`에 설치
3. `USE_FAKE_DETECT 0`으로 업로드 (FQBN `esp32:esp32:XIAO_ESP32S3:PSRAM=opi`)
4. PC 방화벽에서 TCP 1883 인바운드 허용
5. **카메라는 모니터 위 가운데**, 앉는 자리에서 50cm 이상

### 확인 도구
| 도구 | 용도 |
|---|---|
| <http://localhost:8000/monitor.html> | 얼굴 점수·판정 실시간 대시보드 |
| `python tools\monitor.py` | 터미널 모니터 (서버 없이 브로커 직접) |
| `python model\testing\measure.py` | 상황별 감지율·오탐률 표 |
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
- **해결됨: 보드 연결 끊김.** 원인은 두 가지였습니다. 보드 **안테나가 빠져 있었고**(수신 -92 → 끼운 뒤 -52 dBm), ESP32의 **Wi-Fi 절전 모드**가 전송을 밀었습니다. 안테나를 끼우고 절전을 끈 뒤, 영상(`frame`)까지 켜고 2분에 1번 정도로 줄었습니다. 보드를 쓸 때는 안테나부터 확인하세요.
- 웹: 유튜브 API가 캐시로 빨리 준비되면 "플레이어가 준비되지 않았습니다"에 멈출 수 있습니다(스크립트 로딩 순서). 김정윤에게 전달했습니다. 당장은 Ctrl+Shift+R로 피할 수 있습니다.
- 빈자리 오탐률, 옆얼굴, 1~2m 거리는 아직 측정 전입니다(조아람 담당).

## 데이터 출처와 라이선스
- v19 학습 데이터: **WIDER FACE** (Yang et al., CVPR 2016), Hugging Face 미러 `CUHK-CSE/wider_face`. CC BY-NC-ND 4.0이라 비상업 수업 프로젝트에서만 쓰고, 데이터와 v19 zip은 공개 저장소에 올리지 않습니다.
- 공개 원본 모델: Edge Impulse public/96468 (Louis Moreau, FFHQ 일부), BSD-3-Clause-Clear
