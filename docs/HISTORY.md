# HISTORY

## 2026-10-30 뼈대
- 기획: `Zero_Touch_Media_Control.pdf`(얼굴 인식 → 유튜브 재생/정지). AirStroke 구조(문서 지도, 담당 폴더, 계약 우선, .env, trace)를 축소해서 적용.
- 보드 확인(esptool): ESP32-S3 (QFN56) rev0.2, PSRAM 8MB 내장, 플래시 8MB, COM10, USB-Serial/JTAG (VID 303A PID 1001). XIAO ESP32S3 Sense와 같은 구성.
- 결정: 인식은 ESP32 안(수업 요구), 전달은 MQTT(강사 권장), 서버 판정 300/1500/0.6/3000ms.
- 시험: pytest 14 통과. Mosquitto 2.1.2 + 서버 + fake_esp32 --scenario: 0.9s absent → 1.4s present → 5초 뒤 얼굴 없음 → 1.5초 후 absent → 강제 종료 시 즉시 offline(LWT) → no_device.
- 펌웨어 컴파일 실패: 한글 사용자 경로 때문에 ld가 출력 파일·코어 라이브러리를 못 찾음. `--build-path` 영문 경로만으로는 부족(코어 라이브러리 경로도 한글). junction은 arduino-cli가 따라가지 못함. subst 가상 드라이브(W:=Arduino15, V:=Documents\Arduino) + `ARDUINO_DIRECTORIES_DATA/USER` + 영문 `--build-path`로 **컴파일 성공**: 862,852 B(25%), 전역 46,120 B(14%).
- 설계 문서: `docs/superpowers/specs/2026-10-30-skeleton-design.md`

## 2026-10-30 실제 보드 첫 연결 (팀원2)
- 환경: 영문 사용자 경로 PC라 subst 불필요. arduino-cli 1.5.1, esp32 코어 3.3.12, PubSubClient 2.8.0, ArduinoJson 7.4.3. FQBN `esp32:esp32:XIAO_ESP32S3:PSRAM=opi`, 이 PC에서 COM5. 컴파일 868,166 B(25%), 전역 46,596 B(14%).
- 보드(esptool): ESP32-S3 (QFN56) rev0.2, PSRAM 8MB, USB-Serial/JTAG.
- 집 공유기 접속 실패: 보드 스캔 RSSI -92~-94 dBm(같은 자리 PC는 100%), 주변 AP 1개만 보임, 끊김 사유 2/4(auth/assoc expire). 비밀번호는 PC 저장값과 일치. 공유기 앞에서 -65 dBm로 접속됨 → 안테나 문제로 판단.
- 폰 핫스팟(2.4GHz)으로 자리에서 접속 2초. MQTT: status online·hello·detect 28초 131개 유실 없음. 서버 `/health` mqtt·device 정상, bad 0, `ztmc/state` present/absent 교대. 브라우저 유튜브 재생/정지 사용자 확인.
- 주의: `config.h` 비밀번호에 한/영 전환 안 된 한글(`ㅁ`)이 섞여 실패할 뻔함. 핫스팟은 PC IP가 바뀔 수 있음 → `MQTT_HOST` 재확인.
