# HISTORY

## 2026-10-30 뼈대
- 기획: `Zero_Touch_Media_Control.pdf`(얼굴 인식 → 유튜브 재생/정지). AirStroke 구조(문서 지도, 담당 폴더, 계약 우선, .env, trace)를 축소해서 적용.
- 보드 확인(esptool): ESP32-S3 (QFN56) rev0.2, PSRAM 8MB 내장, 플래시 8MB, COM10, USB-Serial/JTAG (VID 303A PID 1001). XIAO ESP32S3 Sense와 같은 구성.
- 결정: 인식은 ESP32 안(수업 요구), 전달은 MQTT(강사 권장), 서버 판정 300/1500/0.6/3000ms.
- 시험: pytest 14 통과. Mosquitto 2.1.2 + 서버 + fake_esp32 --scenario: 0.9s absent → 1.4s present → 5초 뒤 얼굴 없음 → 1.5초 후 absent → 강제 종료 시 즉시 offline(LWT) → no_device.
- 펌웨어 컴파일 실패: 한글 사용자 경로 때문에 ld가 출력 파일·코어 라이브러리를 못 찾음. `--build-path` 영문 경로만으로는 부족(코어 라이브러리 경로도 한글). junction은 arduino-cli가 따라가지 못함. subst 가상 드라이브(W:=Arduino15, V:=Documents\Arduino) + `ARDUINO_DIRECTORIES_DATA/USER` + 영문 `--build-path`로 **컴파일 성공**: 862,852 B(25%), 전역 46,120 B(14%).
- 설계 문서: `docs/superpowers/specs/2026-10-30-skeleton-design.md`

## 2026-10-30 모델 비교 (팀원1, 브랜치 feat/model-compare)
- 공개 원본: Edge Impulse public/96468(Louis Moreau, FFHQ 일부 406장, 96×96 흑백 FOMO MNv2 0.1, 라벨 face) → 복제 1152773 `ztmc-face-fomo`(비공개), 대상 장치 ESP-EYE로 변경.
- 실험 6개(E0~E5) 상세는 `model/experiments.md`. 요점: 원본은 LR 0.00015로 학습 부족(재현율 0.57). LR 0.001 + 증강만으로 F1 0.69→0.80. 입력 64×64로 줄이면 F1 0.82, 추정 280ms(원본 728), RAM 69K(원본 240K). 48×48과 MNv2 0.35는 이득 없음.
- 채택: E3(64×64) = 우리 학습 v1, Arduino library v18. 공개 원본은 v17. zip은 `C:\dev\ei-zips\`(git 제외), 컴파일 담당 세션에 전달.
- Chrome 다운로드가 `.tmp`로 멈춤(이름 변경 안 됨). 크기가 다 받아진 `.tmp`를 복사해 zip으로 열어 `model_metadata.h`로 버전·입력 크기를 확인함.
- Model testing에서 int8은 무료 계정이라 선택 불가 → test F1은 float32 기준. ESP-EYE 추정 ms는 구형 ESP32 기준이라 S3 실측보다 클 것.
