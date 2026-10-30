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

## 2026-10-30 실제 보드 첫 연결 (팀원2)
- 환경: 영문 사용자 경로 PC라 subst 불필요. arduino-cli 1.5.1, esp32 코어 3.3.12, PubSubClient 2.8.0, ArduinoJson 7.4.3. FQBN `esp32:esp32:XIAO_ESP32S3:PSRAM=opi`, 이 PC에서 COM5. 컴파일 868,166 B(25%), 전역 46,596 B(14%).
- 보드(esptool): ESP32-S3 (QFN56) rev0.2, PSRAM 8MB, USB-Serial/JTAG.
- 집 공유기 접속 실패: 보드 스캔 RSSI -92~-94 dBm(같은 자리 PC는 100%), 주변 AP 1개만 보임, 끊김 사유 2/4(auth/assoc expire). 비밀번호는 PC 저장값과 일치. 공유기 앞에서 -65 dBm로 접속됨 → 안테나 문제로 판단.
- 폰 핫스팟(2.4GHz)으로 자리에서 접속 2초. MQTT: status online·hello·detect 28초 131개 유실 없음. 서버 `/health` mqtt·device 정상, bad 0, `ztmc/state` present/absent 교대. 브라우저 유튜브 재생/정지 사용자 확인.
- 주의: `config.h` 비밀번호에 한/영 전환 안 된 한글(`ㅁ`)이 섞여 실패할 뻔함. 핫스팟은 PC IP가 바뀔 수 있음 → `MQTT_HOST` 재확인.

## 2026-10-30 오후 로컬 학습 준비·팀원4 도구 (팀원1)
- Edge Impulse 무료 학습 시간 소진(이번 달 남은 시간 0, 11-29 초기화) → 클라우드 재학습 불가. 브라우저에서 학습 데이터를 PC로 옮기는 것도 Studio CSP에 막힘.
- 대신 WIDER FACE(HF `CUHK-CSE/wider_face`)에서 시연 상황처럼 얼굴이 화면 10~60%인 정사각형을 잘라 64×64 흑백 FOMO 데이터 생성(`model/train/build_dataset.py`, 학습 41,067장·검증 5,105장).
- `model/train/train_fomo.py`: EI FOMO와 같은 구조(MNv2 앞부분 block_6_expand_relu + 1×1 머리, 출력 8×8×2)로 학습 → int8 TFLite. `swap_model.py`: v18 라이브러리의 EON 모델을 TFLite Micro(`EI_CLASSIFIER_COMPILED 0`, AllOpsResolver)로 바꿔 끼움 — DSP·후처리·라벨 그대로라 펌웨어 수정 불필요.
- `model/train/pc_harness/`: EI 라이브러리를 PC(MinGW g++ 16)에서 그대로 돌려 검증셋 F1 측정. E3(v18 EON)은 5,105장 연속 실행에 크래시 없음(평균 9.9ms, PC) — 보드 추론 크래시는 모델 코드보다 ESP-NN/코어 쪽 의심. **E3 WIDER 검증 F1 0.642**(P 0.66 R 0.62)를 기준선으로.
- 실패 교훈: 한글 사용자 폴더 Temp 때문에 TF 저장·TFLite 변환·MinGW 링크가 실패 → `TMP/TEMP`를 `C:\dev\ztm-data\tmp`로, g++는 `C:\dev\mingw64`로 복사. 학습 2개를 동시에 돌려 RAM 4.6GB를 써서 보드 세션 빌드가 메모리 부족으로 중단됨 → 학습은 한 번에 하나.
- 첫 학습(얼굴 가중치 100): 재현율 0.98·정밀도 0.34로 오탐 과다. 가중치 10 + 가려진 얼굴 무시로 다시 학습 중(L3, 20에폭 float F1 0.735).
- 팀원4 합류 → `model/testing/`: `measure.py`(MQTT detect를 상황 11개별로 모아 감지율·오탐률 표), `capture.py`(캡처 모드 시리얼 FRAME → PNG). 가짜 ESP32·가상 시리얼로 동작 확인.

## 2026-10-30 L3(v19) 로컬 모델 (팀원1)
- L3: MNv2 0.1 처음부터, 얼굴 가중치 10, 30에폭(CPU 약 25분). int8 WIDER val F1 0.745(임계값 0.6). `swap_model.py`로 v18 라이브러리에 끼워 v19 zip, PC 하네스에서 F1 **0.748**(v18 0.642), 4.4ms(v18 9.9ms).
- 시행착오: arena 64KB는 AllocateTensors 실패 → 128KB. 하네스 빌드 캐시가 헤더 변경을 못 잡아 옛 arena로 돈 적 있음 → obj 폴더 이름에 모델 설정 해시.
- PR #3(팀원4 도구·로컬 학습 도구)은 사용자 요청으로 확인자 없이 병합.

## 2026-10-30 모니터 페이지 웹캠 PiP (팀원3)
- 결정: 영상은 **PC 웹캠**(보드는 이미지를 안 보냄. 보드 영상은 프로토콜·펌웨어 변경이 필요해 보류), 창은 Document Picture-in-Picture(항상 위, 감지 배지 포함). 미지원 브라우저는 video PiP(영상만).
- `web/monitor.*`만 변경. 서버가 새 파일을 내주는 것까지 확인, 브라우저 웹캠·PiP 동작은 수동 확인 필요.
