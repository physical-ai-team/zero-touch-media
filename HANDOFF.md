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
3. 역할별 첫 문서: 팀원1 `model/README.md` · 팀원2 `docs/04-firmware.md` · 팀원3 `docs/05-web.md` + `docs/02-architecture.md`. 공통으로 `docs/03-protocol.md`.
4. 환경(서버·웹·가짜 ESP32를 돌릴 사람): Miniforge + `conda env create -f environment.yml`(환경 `ztmc`) + Mosquitto(`winget install EclipseFoundation.Mosquitto`) + `copy .env.example .env`. 실행 명령은 `CLAUDE.md` 4절.
5. 보드 없이 전체 확인: 브로커 → 서버 → `python tools\fake_esp32.py` → <http://localhost:8000> "시작" → `f`/`n`/`x`.

## 현재 상태 (2026-10-30)
- 뼈대 완료: 판정 서버(MQTT 구독 → presence 상태기계 → WebSocket·`ztmc/state`), 가짜 ESP32, 최소 유튜브 페이지, 펌웨어 빈 스케치(Wi-Fi + MQTT + 가짜 detect), 문서 전부.
- 확인함: pytest 14개 통과. Mosquitto 2.1.2 + 서버 + 가짜 ESP32로 absent → present → (얼굴 없음 1.5초) absent → (강제 종료) no_device(LWT) 확인. 펌웨어 컴파일 통과(XIAO_ESP32S3, 플래시 25%).
- 확인 못 함: 브라우저에서 유튜브 실제 재생/정지, 실제 보드 업로드·MQTT 접속, Edge Impulse 모델.
- 역할: 팀원1 박민성(모델), 팀원2(펌웨어), 팀원3(브로커·서버·웹) — 팀원2·3 이름은 정해지면 `CLAUDE.md`·`docs/07-team.md`에 적는다.
- 보드: ESP32-S3, PSRAM 8MB, 플래시 8MB(esptool 확인). XIAO ESP32S3 Sense로 추정, 정확한 보드명 미확인.
- 설계 근거: `docs/superpowers/specs/2026-10-30-skeleton-design.md`, `docs/decisions.md`.

## 남은 일
**팀원1 박민성 (모델)**
- [ ] Edge Impulse 공개 Face detection 프로젝트 고르기 → Clone → 공개 원본 그대로 Arduino library zip 받아 **팀원2에게 먼저 전달**
- [ ] 학습·최적화(96×96 그레이스케일 FOMO 권장, 라벨 `face`) → 우리 모델 zip 전달
- [ ] `model/README.md` 기록 표 채우기(정확도·RAM·Flash·보드 추론 ms, 공개 원본 vs 우리 모델)

**팀원2 (펌웨어)**
- [ ] 보드명 확인 후 `docs/04-firmware.md` 보드 줄 고치기
- [ ] `config.h` 만들고 `USE_FAKE_DETECT 1`로 업로드 → `mosquitto_sub -t "ztmc/#" -v`로 hello/detect 확인
- [ ] Edge Impulse 라이브러리가 ESP32 코어 3.3.12에서 빌드되는지 확인(안 되면 2.0.17, `decisions.md` 기록)
- [ ] `run_inference()` TODO 채우기 → `USE_FAKE_DETECT 0`, `infer_ms`·`dsp_ms` 실제 값

**팀원3 (브로커·서버·웹)**
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
