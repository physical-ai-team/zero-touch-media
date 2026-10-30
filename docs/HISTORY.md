# HISTORY

## 2026-10-30 뼈대
- 기획: `Zero_Touch_Media_Control.pdf`(얼굴 인식 → 유튜브 재생/정지). AirStroke 구조(문서 지도, 담당 폴더, 계약 우선, .env, trace)를 축소해서 적용.
- 보드 확인(esptool): ESP32-S3 (QFN56) rev0.2, PSRAM 8MB 내장, 플래시 8MB, COM10, USB-Serial/JTAG (VID 303A PID 1001). XIAO ESP32S3 Sense와 같은 구성.
- 결정: 인식은 ESP32 안(수업 요구), 전달은 MQTT(강사 권장), 서버 판정 300/1500/0.6/3000ms.
- 시험: pytest 14 통과. Mosquitto 2.1.2 + 서버 + fake_esp32 --scenario: 0.9s absent → 1.4s present → 5초 뒤 얼굴 없음 → 1.5초 후 absent → 강제 종료 시 즉시 offline(LWT) → no_device.
- 펌웨어 컴파일 실패: 한글 사용자 경로 때문에 ld가 출력 파일·코어 라이브러리를 못 찾음. `--build-path` 영문 경로만으로는 부족(코어 라이브러리 경로도 한글). junction은 arduino-cli가 따라가지 못함. subst 가상 드라이브(W:=Arduino15, V:=Documents\Arduino) + `ARDUINO_DIRECTORIES_DATA/USER` + 영문 `--build-path`로 **컴파일 성공**: 862,852 B(25%), 전역 46,120 B(14%).
- 설계 문서: `docs/superpowers/specs/2026-10-30-skeleton-design.md`

## 2026-10-30 얼굴 감지 신호 모니터 (팀원3)
- `tools/monitor.py`: 브로커 `ztmc/#` 직접 구독 → 상태 한 줄(얼굴 여부·score·Hz·infer ms·받음/유실) + 바뀔 때만 기록(status, hello, face 전환, 서버 판정, seq 감소). 기본값은 루트 `.env`.
- `web/monitor.html`·`monitor.js`: `/ws/player` detect·state 대시보드. 서버 코드는 안 바꿈.
- 시험: 브로커 + 서버 + `fake_esp32 --scenario` + monitor: Face Detected → 0.32s 뒤 present, Face Not Detected → 1.51s 뒤 absent, 가짜 강제 종료 → offline(LWT) → no_device. `/monitor.html` 200. pytest 14 통과.
