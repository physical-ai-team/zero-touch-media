# CLAUDE.md — Zero-Touch Media Control

ESP32-S3 카메라 보드가 **보드 안에서** Edge Impulse 얼굴 인식 모델을 돌리고, 결과를 MQTT로 보낸다.
PC 서버가 판정을 안정화해 브라우저 유튜브를 자동 재생/정지한다. **팀원 3명이 각자 Claude Code로 작업**하므로 이 규칙을 지킨다.

## 0. 문서 역할과 읽는 법
| 파일 | 역할 | 읽는 법 |
|---|---|---|
| `CLAUDE.md` | 항상 지킬 규칙 (100줄 이하) | 자동으로 읽힘 |
| `HANDOFF.md` | 현재 상태, **남은 일**, 교훈 | 세션 시작 때 `grep -n "^## " HANDOFF.md` → "남은 일" 절만 읽기 |
| `docs/HISTORY.md` | 날짜별 작업 기록·원인·측정 | 통째로 읽지 말고 grep으로 필요한 부분만 |

## 1. 작업별로 먼저 읽을 문서
| 작업 | 문서 |
|---|---|
| 처음 / 전체 파악 | [docs/01-overview.md](docs/01-overview.md), [docs/02-architecture.md](docs/02-architecture.md) |
| MQTT 토픽·메시지·WebSocket | [docs/03-protocol.md](docs/03-protocol.md) + [server/ztmc_server/protocol.py](server/ztmc_server/protocol.py) |
| 펌웨어·모델 | [docs/04-firmware.md](docs/04-firmware.md), [model/README.md](model/README.md) |
| 웹 페이지 | [docs/05-web.md](docs/05-web.md) |
| 일정·동시 작업 방법 | [docs/06-roadmap.md](docs/06-roadmap.md) |
| 담당·브랜치 규칙 | [docs/07-team.md](docs/07-team.md) |
| 왜 이렇게 정했나 | [docs/decisions.md](docs/decisions.md) |

## 2. 담당 영역 (가장 중요한 규칙)
| 담당 | 폴더 |
|---|---|
| 팀원1 박민성 — 모델(Edge Impulse) | `model/` |
| 팀원2 — 펌웨어(보드·카메라·모델 이식·MQTT 발행) | `firmware/` |
| 팀원3 — 브로커·서버·웹·통합 | `broker/`, `server/`, `web/`, `tools/`, 루트 설정 파일 |
| 팀원4 — 시연 데이터·실제 정확도 측정 | `model/testing/` |
| 공동 | `docs/`, `HANDOFF.md` — 자기 담당 문서·절만 고친다 |

- **자기 담당 폴더 밖은 수정하지 않는다.** 고쳐야 할 것 같으면 수정하지 말고 사용자에게 알리고 멈춘다(어느 파일을 왜).
- 메시지 규격(`docs/03-protocol.md`) 변경은 세 명 합의. 필드 **추가**는 자유, 삭제·이름 변경은 금지.
- 큰 설계 결정은 임의로 정하지 말고 선택지를 제시한다. 확정되면 `docs/decisions.md`에 기록.
- `main`에 직접 push 하지 않는다. `feat/<담당>-<내용>` 브랜치 → PR.

## 3. 설계 제약 (요약)
- ESP32 → 서버는 **MQTT만**(브로커: PC의 Mosquitto, 1883). 서버 → 브라우저는 WebSocket `/ws/player`.
- 토픽: `ztmc/{device_id}/status|hello|detect`, 서버 결과 `ztmc/state`. status는 LWT로 `offline` 등록.
- **재생/정지 판단은 서버(`presence.py`) 한 곳에서만.** ESP32는 프레임별 판정만 보내고, 웹은 서버 상태를 따르기만 한다.
- 시각은 서버 시계 epoch ms. ESP32는 시각이 아니라 걸린 시간(ms)만 보낸다.
- 설정값은 `.env`(서버) / `firmware/.../config.h`(펌웨어)에만. 하드코딩 금지. 비밀값(Wi-Fi 비번)은 git에 올리지 않는다.

## 4. 개발 명령
```powershell
conda env create -f environment.yml      # 최초 (환경 이름 ztmc)
conda activate ztmc
copy .env.example .env
& "C:\Program Files\mosquitto\mosquitto.exe" -c broker\mosquitto.conf -v   # 터미널 1: 브로커
cd server; python -m ztmc_server                                         # 터미널 2: 서버 → http://localhost:8000
python tools\fake_esp32.py                                               # 터미널 3: 가짜 ESP32 (f/n/l/x/q)
python -m pytest -q                                                      # 시험 (루트에서)
```

## 5. 작업 후 순서
1. `python -m pytest -q` 통과 확인 (서버를 고쳤다면 필수)
2. `HANDOFF.md`의 "남은 일"과 상태 한두 줄 갱신, 상세는 `docs/HISTORY.md` 맨 아래에 날짜와 함께
3. 커밋 → 자기 브랜치 push → PR
