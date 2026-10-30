# 5. 웹 페이지 (담당: 팀원3)

코드: [web/](../web/) — 서버가 `http://localhost:8000/`으로 제공. 규격: [03-protocol.md](03-protocol.md)의 WebSocket 절.

## 뼈대에 있는 것
- 유튜브 IFrame API 플레이어, "시작" 버튼(브라우저 자동재생 정책 때문에 첫 클릭 필요)
- `state`에 따라 `playVideo()` / `pauseVideo()`. 서버 연결이 끊기면 정지
- 판정·장치·최근 인식·플레이어 상태 표시, 영상 바꾸기(유튜브 주소 붙여넣기 또는 영상 ID, `t=` 시작 시각 반영, 마지막 영상은 브라우저에 기억), 수동 모드
- `ping`에 `pong` 응답, 플레이어 이벤트를 서버로 보고

## 모니터 페이지 `monitor.html`
- <http://localhost:8000/monitor.html> (플레이어 페이지 위 "모니터" 링크). 같은 `/ws/player`를 받아 **보여 주기만** 한다.
- Face Detected / Face Not Detected / 신호 없음(`DEVICE_TIMEOUT_MS` 동안 detect 없음) 큰 표시, 신뢰도 막대(`MIN_SCORE` 표시), 서버 판정, 장치, 수신 Hz, 추론/DSP ms, 최근 30초 타임라인, 바뀔 때만 남는 기록.
- **보드 카메라 + PiP** (플레이어·모니터 두 페이지 모두, 코드는 `web/campip.js` 공용): 보드가 보내는 JPEG(`frame`)를 "보드 카메라" 칸에 보여 주고, "PiP 창으로"를 누르면 영상 + 감지 배지(테두리 색)를 항상 위 창에 띄운다(Chrome·Edge의 Document PiP, 마우스로 옮기기·크기 조절). 3초 동안 영상이 없으면 "영상 끊김". 보드 펌웨어가 `frame`을 보내야 보인다(보드 없이는 `fake_esp32.py`가 가짜 영상을 보냄).
- detect는 서버가 `PLAYER_DETECT_HZ`로 줄여 보내므로 웹의 빈도는 "받은 것" 기준. 원본 전부를 보려면 터미널 모니터:
  `python tools\monitor.py` (브로커 직접 구독, 서버 없이도 동작, seq 유실 수 표시, `--all`로 detect 전부 출력)

## 할 일 (예시)
- 디자인, 상태를 크게 보여 주는 표시(재생 중/정지/장치 없음), 신뢰도 막대
- 영상 목록·재생목록, 전체 화면
- 판정 → 실제 재생까지 걸린 시간 표시(`trace` + ping/pong 시계 차이)

## 기다리지 않고 작업하기
보드 없이: 브로커 + 서버 + `python tools\fake_esp32.py` 를 켜고 `f`/`n`/`x`로 상태를 바꿔 가며 개발한다.

## 지킬 것
- 재생/정지를 페이지에서 따로 판단하지 않는다(디바운스는 서버). 바꾸고 싶으면 `.env` 값을 조정(판정값은 세 명이 측정 보고 합의).
