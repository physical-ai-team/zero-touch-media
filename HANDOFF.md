# HANDOFF — Zero-Touch Media Control

<!-- claude-setup-notify -->
> **(팀원1 박민성 개인 PC용 — 다른 팀원은 건너뜀) 새 PC면 세션 시작 전에 한 번 확인 — Claude 알림 훅**(1분 넘는 작업이 끝나거나 입력이 필요할 때, 그 VS Code 창이 **최소화돼 있으면** 윈도우 팝업, 누르면 그 창이 다시 뜸).
> 1. 확인: `powershell -ExecutionPolicy Bypass -File C:\dev\claude-setup\install.ps1 -Check` → `OK`면 끝.
> 2. 폴더가 없거나 `없음/구버전`이면: `git clone https://github.com/msungaffa/claude-setup C:\dev\claude-setup`(이미 있으면 `git -C C:\dev\claude-setup pull`) → `powershell -ExecutionPolicy Bypass -File C:\dev\claude-setup\install.ps1` → Claude Code·VS Code 다시 시작.

> 새 세션은 `grep -n "^## " HANDOFF.md` → **"이어서 시작하는 법"과 "남은 일"** 절만 읽고 시작한다. 상세 기록은 `docs/HISTORY.md`(grep으로만).
> 작업을 끝낼 때: 자기 담당의 "남은 일" 줄과 "현재 상태"를 한두 줄 고치고, 상세는 `docs/HISTORY.md` 맨 아래에 날짜와 함께.

## 이어서 시작하는 법
1. 저장소: `github.com/physical-ai-team/zero-touch-media` → `C:\dev\zero-touch-media` 처럼 **영문 경로**에 clone.
   이미 있으면 `git fetch --all --prune` → `git switch main` → `git pull --ff-only` → 자기 브랜치에 `git merge origin/main`.
2. 자기 역할 확인: `CLAUDE.md` 2절(담당 폴더). 작업 브랜치는 `feat/<담당>-<내용>`, `main` 직접 push 금지 → PR.
3. 역할별 첫 문서: 팀원1 `model/README.md` · 팀원2 `docs/04-firmware.md` · 팀원3 `docs/05-web.md` + `docs/02-architecture.md` · 팀원4 `model/testing/README.md`. 공통으로 `docs/03-protocol.md`.
4. 환경(서버·웹·가짜 ESP32를 돌릴 사람): Miniforge + `conda env create -f environment.yml`(환경 `ztmc`) + Mosquitto(`winget install EclipseFoundation.Mosquitto`) + `copy .env.example .env`. 실행 명령은 `CLAUDE.md` 4절.
5. 보드 없이 전체 확인: 브로커 → 서버 → `python tools\fake_esp32.py` → <http://localhost:8000> "시작" → `f`/`n`/`x`.

## 현재 상태 (2026-10-30)
- 뼈대 완료: 판정 서버(MQTT 구독 → presence 상태기계 → WebSocket·`ztmc/state`), 가짜 ESP32, 최소 유튜브 페이지, 펌웨어 빈 스케치(Wi-Fi + MQTT + 가짜 detect), 문서 전부.
- 확인함: pytest 14개 통과. Mosquitto 2.1.2 + 서버 + 가짜 ESP32로 absent → present → (얼굴 없음 1.5초) absent → (강제 종료) no_device(LWT) 확인. 펌웨어 컴파일 통과(XIAO_ESP32S3, 플래시 25%).
- 모니터 추가(팀원3): `tools/monitor.py`(터미널), `web/monitor.html`(대시보드). 가짜 ESP32로 확인함.
- 확인 못 함: 브라우저에서 유튜브 실제 재생/정지, 실제 보드 업로드·MQTT 접속, Edge Impulse 모델.
- 역할: 팀원1 박민성(모델), 팀원2(펌웨어), 팀원3(브로커·서버·웹), 팀원4(시연 데이터·실제 정확도 측정, 10-30 합류) — 팀원2·3·4 이름은 정해지면 `CLAUDE.md`·`docs/07-team.md`에 적는다.
- 보드: ESP32-S3, PSRAM 8MB, 플래시 8MB(esptool 확인). XIAO ESP32S3 Sense로 추정, 정확한 보드명 미확인.
- 실제 보드 확인(팀원2): `USE_FAKE_DETECT 1` 업로드 → 폰 핫스팟 Wi-Fi → MQTT → 서버 → 웹 유튜브 재생/정지까지 동작. 끊김 원인은 **안테나 빠짐**(-92 → 끼운 뒤 -52 dBm)과 **Wi-Fi 절전**이었고 둘 다 해결(10-30 시연 후).
- **실제 추론 펌웨어(팀원2)**: v19 모델로 카메라 → 추론 → MQTT detect(dsp 2ms, infer 51ms, 초당 약 7회) + 카메라 JPEG `frame`(초당 2장, 웹 PiP용). 앉은 정면 평균 score 0.92. EON 크래시 원인(`ei_calloc` 정렬)을 찾아 펌웨어에서 해결. 상세 `docs/04-firmware.md` "위험·겪은 문제".
- 설계 근거: `docs/superpowers/specs/2026-10-30-skeleton-design.md`, `docs/decisions.md`.

## 남은 일
**팀원1 박민성 (모델)**
- [x] 공개 원본(public/96468) 복제 → Arduino library v17 zip (10-30)
- [x] 비교 실험 6개 → **E3 64×64 흑백 채택**(test F1 0.69→0.82, 추정 728→280ms) → v18 zip. 기록 `model/experiments.md`, zip `C:\dev\ei-zips\`
- [ ] 팀원2에게 v17·v18 zip 전달(이 PC의 컴파일 세션에는 전달함), 보드 실측 `infer_ms`를 받아 `model/README.md` 표 채우기
- [ ] (시간 남으면) 시연 장소·카메라로 찍은 얼굴/배경 사진을 추가 학습 → 오탐 줄이기 (사진은 팀원4가 모아 줌)
- [x] 로컬 학습 L3 → **v19 zip**(WIDER 검증 F1 0.748 vs v18 0.642, PC 추론 절반, TFLite Micro). 기록 `model/experiments.md`, zip `C:\dev\ei-zips\` → 창2(펌웨어 세션)에 전달
- [x] v19 보드 실측: 크래시 없음(v17 EON은 크래시), 추론 50ms·dsp 2ms, 정면 50~80cm 감지. **v19 유지** (`model/experiments.md` 보드 실측 절). 펌웨어 인수인계 `model/firmware-handoff.md`
- [ ] 아주 가까운 얼굴(화면 가득) 못 잡음 → `build_dataset.py` 얼굴 크기 범위 15~55% → 15~90%로 넓혀 재학습(v20). 같은 arena·임계값이면 모델 배열 파일만 바뀌어 재컴파일이 짧다
- [ ] v18(EON)은 보드 미측정 — 필요하면 시험. 얼굴 없음 오탐·옆모습·1~2m는 팀원4 측정으로 확정
- [x] 사이트 후보 8개와 96468 선택 이유를 `experiments.md` 0단계에 추가(세션 로그에서 복원, 상세 확인은 2개뿐)

**팀원4 (시연 데이터·실제 정확도 측정)** — 시작 문서 `model/testing/README.md`
- [ ] 환경 준비(`conda` 환경 `ztmc` + `pip install -r model/testing/requirements.txt` + Mosquitto)
- [ ] 보드가 실제 추론으로 돌면 `python model/testing/measure.py --tag v18` → 상황 11개 감지율·오탐률 표 커밋(`model/testing/results/`)
- [ ] 캡처 모드 펌웨어로 `model/testing/capture.py` → 얼굴 200장+·배경 100장+ 모아 팀원1에게 전달(git 금지). 보드 전이면 휴대폰으로 시연 자리 사진(차선책)
- [ ] 새 모델이 오면 같은 조건으로 다시 측정해 버전 비교

**팀원2 (펌웨어)**
- [x] 보드 줄 고치기(조아람이 실측값으로, PR #6), 카메라 센서는 OV3660 확인
- [x] `config.h` 만들고 `USE_FAKE_DETECT 1`로 업로드 → `mosquitto_sub -t "ztmc/#" -v`로 hello/detect 확인
- [x] 안테나(U.FL) 연결 — 빠져 있었음. 끼우니 핫스팟 -87 → -22 dBm, 공유기 -92 → -52 dBm
- [x] Wi-Fi 절전 끔(`WiFi.setSleep(false)`) — 영상 끈 상태 2분×2번 끊김 0번
- [x] Edge Impulse 라이브러리 코어 3.3.12 빌드 확인(v17 EON·v19 둘 다, 코어 내릴 필요 없음)
- [x] `run_inference()` 구현 → `USE_FAKE_DETECT 0`, v19로 `infer_ms` 51·`dsp_ms` 2 실측
- [x] `frame` 토픽 펌웨어 쪽 구현(`FRAME_INTERVAL_MS`, 기본 500) — 서버가 받는 것 확인(10초 17장, bad 0). 웹 PiP 표시는 브라우저 확인 필요
- [x] 캡처 모드(`CAPTURE_MODE`) — 팀원4 `capture.py`로 3장 저장 확인
- [x] 판정값 팀 기본값 변경(D-008): `FACE_THRESHOLD` 0.7, `DEVICE_TIMEOUT_MS` 6000
- [ ] 얼굴 없음 오탐률을 v19로 측정해 0.7이 맞는지 확인 — 팀원4 `measure.py`와 같이
- [ ] 팀원1에게: EON 크래시 원인은 `ei_calloc` 정렬(펌웨어에서 해결) → `model/firmware-handoff.md` "피해야 할 것" 갱신 요청

**팀원3 (브로커·서버·웹)**
- [x] 얼굴 감지 신호 모니터: 터미널 `python tools\monitor.py`(브로커 직접 구독, 서버 없이도 됨), 웹 <http://localhost:8000/monitor.html>
- [x] 모니터 페이지에 PC 웹캠 PiP 창(감지 배지 겹쳐 표시) 추가
- [x] PiP를 PC 웹캠 → **보드 카메라 영상**으로 교체: MQTT `ztmc/{id}/frame`(JPEG) → 서버 → WebSocket 바이너리 → 웹. 가짜 ESP32로 확인
- [ ] `frame` 토픽 추가를 팀원1·2와 합의(`docs/03-protocol.md`), 팀원2에게 펌웨어 쪽 요청(같은 문서 frame 절에 방법)
- [ ] PiP 창을 Chrome/Edge에서 직접 확인(자동 시험 못 함)
- [ ] 실제 보드 신호를 `tools\monitor.py`로 확인(팀원2 `USE_FAKE_DETECT 1` 업로드 후)
- [ ] 시연 PC Windows 방화벽 1883 인바운드 허용 — 관리자 PowerShell:
      `New-NetFirewallRule -DisplayName "Mosquitto 1883" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow`
- [ ] 브라우저에서 유튜브 재생/정지 실제 확인, 웹 페이지 다듬기(`docs/05-web.md`)
- [ ] 실제 보드 → 서버 → 웹 통합, 지연·오판정 측정, 판정값(300/1500ms, 0.6) 조정

**공동**
- [ ] 저장소에 팀원 초대(만든 사람), `main` 보호 규칙
- [ ] 팀원2·3 이름 채우기

## 교훈
- 사용자 폴더 이름이 한글이면 ESP32 코어 링크가 실패한다(`cannot find -lxtensa`, `cannot open output file ... .elf`). `--build-path`만으로는 안 되고 junction은 arduino-cli가 못 따라감 → `docs/04-firmware.md` "한글 사용자 이름 PC" 절의 subst 방법으로 해결. 사용자 이름이 영문이면 해당 없음.
- Mosquitto 2.x는 설정 없이 켜면 localhost만 받는다 → 반드시 `-c broker\mosquitto.conf`.
- 조직에 공개 저장소를 만드는 `gh repo create`는 Claude 자동 권한 검사가 막는다 → 사용자가 직접 `!`로 실행.
