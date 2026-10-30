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

## 2026-10-30 v19 보드 실측·인수인계 (팀원1, 컴파일 세션)
- 도구: Arduino IDE 내장 `arduino-cli`, 보드 XIAO ESP32S3 Sense(COM10), 코어 3.3.12, `PSRAM=opi`, 한글 경로 때문에 subst W:/V: 사용. 빌드는 `--jobs 2`(동시 4.6GB 학습과 겹치면 메모리 부족으로 시스템이 빌드를 중단함).
- v17(공개 원본, EON): 코어 3.3.12·XIAO_ESP32S3에서 컴파일 통과(최소 스케치 Flash 346KB, RAM 63.7KB). 카메라 스케치로 업로드하면 `run_classifier` 안에서 `StoreProhibited` 반복 재부팅. 추론 직전까지 `heap_caps_check_integrity_all` 정상 → 카메라·스케치 버퍼는 원인 아님. 백트레이스: `tflite_learn_*_reset` → `ei_free` → `tlsf_free`(이미 깨진 힙). 같은 EON 라이브러리는 PC 하네스에서 5,105번 정상.
- ESP-NN 끄기 시험은 **무효**: PowerShell이 `-D…` 인자를 매개변수 이름으로 해석해 `build.extra_flags`가 비어 있었음(`compile_commands.json`에 `ESP_NN=0` 없음). 환경변수 `EXTRA_FLAGS`로 고쳤으나 이후 v19가 돌아 재시험은 보류. 원인은 EON 경로일 가능성이 크다는 정도까지(v17·v19 모두 ESP-NN 켬, v19만 정상).
- v19(L3, TFLite Micro, ESP-NN 켬): 빌드 Flash 694KB(20%)·RAM 40.7KB(12%), **크래시 없음**, `dsp 2ms`, `infer 50ms`, 카메라 포함 초당 약 6프레임. 50~80cm 정면에서 value 0.64~0.79, 박스 1~2개. 얼굴이 화면을 가득 채울 만큼 가까우면 143프레임 연속 0(캡처 모드로 확인: 카메라는 정상, 학습에 없는 크기).
- 캡처 모드(`-DCAPTURE_MODE`): `FRAME 64 64 <hex>` 한 줄 = 한 프레임, hex 길이 8192. 첫 프레임은 워밍업으로 어두움(평균 54, 이후 약 140).
- 시행착오: 빌드 폴더를 버전마다 새로 만들면 라이브러리를 처음부터 다시 컴파일해 10분 이상 걸림(스케치만 바꿀 땐 1분 안쪽).
- 아직 안 한 것: v18 보드 실행, 얼굴 없음 오탐률, 옆모습·1~2m. 인수인계: `model/firmware-handoff.md`, 참고 스케치 `model/samples/ei_cam_test/`.

## 2026-10-30 모니터 페이지 웹캠 PiP (팀원3)
- 결정: 영상은 **PC 웹캠**(보드는 이미지를 안 보냄. 보드 영상은 프로토콜·펌웨어 변경이 필요해 보류), 창은 Document Picture-in-Picture(항상 위, 감지 배지 포함). 미지원 브라우저는 video PiP(영상만).
- `web/monitor.*`만 변경. 서버가 새 파일을 내주는 것까지 확인, 브라우저 웹캠·PiP 동작은 수동 확인 필요.
- 플레이어 페이지: 영상 ID 칸이 유튜브 주소(watch?v=, youtu.be, shorts, embed, live, `t=`)도 받음. Enter로 불러오기, 마지막 영상 localStorage 기억. 주소 해석 9가지 node로 확인.
- 웹캠 PiP를 `web/campip.js`로 떼어 플레이어 페이지에도 추가. 플레이어에서는 detect로 배지, no_device·서버 끊김이면 '신호 없음'. 헤드리스 Edge/Chrome으로 두 페이지 스크립트 실행 확인(웹캠·PiP 자체는 수동 확인 필요).
- 영상 불러오기 안내: 유튜브 onError(임베드 막힘 101/150, 비공개 100 등) 문구 표시, 불러온 뒤 바로 재생 안 되는 이유(시작 안 누름·수동 모드·얼굴 없음) 표시, 플레이어 준비 전 클릭 안내.

## 2026-10-30 PiP 영상을 보드 카메라로 (팀원3)
- 결정(사용자): PC 웹캠 대신 ESP32 카메라. 전송은 MQTT JPEG(보드 MJPEG HTTP 대신: 연결 하나, 터널·https에서도 보임), 겹쳐 표시는 배지만, 웹캠 기능은 뺌.
- 프로토콜 추가 제안: `ztmc/{id}/frame` JPEG 바이너리 QoS0 → WebSocket 바이너리 메시지. 세 명 합의 대기(문서에 표시). 펌웨어는 아직 안 보냄 → 팀원2 요청.
- 서버: `frame`은 판정에 안 쓰고 `PLAYER_FRAME_HZ`(5)로 줄여 전달, JPEG 아님·`FRAME_MAX_BYTES` 초과는 버림. `.env.example`에 두 키 추가. 시험 1개 추가(15 통과).
- 가짜 ESP32: Pillow로 320×240 흑백 가짜 화면(얼굴 있음이면 웃는 얼굴) 2fps, `--frame-hz 0`으로 끔. `requirements-dev.txt`에 pillow 추가. 터미널 모니터에 영상 fps·크기 표시.
- 시험: 따로 띄운 서버(8001, 접두어 ztmctest) + 가짜 ESP32: 서버 frame 9 / bad 0, 플레이어 페이지가 blob JPEG 받음, monitor.py "영상 2.0fps".

## 2026-10-30 실제 추론 펌웨어 (팀원2)
- `run_inference()` 구현: XIAO Sense 카메라(OV3660, PID 0x3660) QVGA JPEG → `fmt2rgb888` → 가운데 정사각 크롭·축소 → `run_classifier`. `score`는 모델 기준을 `EI_MIN_SCORE` 0.1로 낮춰 최고값 그대로, `face`/`count`는 `FACE_THRESHOLD`.
- v17(공개 원본, EON) 첫 추론에서 `CORRUPT HEAP` → `tflite_learn_*_reset` → `ei_free`. 원인: SDK `ei_calloc`이 IDF 5에서 `heap_caps_calloc`(정렬 없음) — 같은 파일 `ei_malloc`은 esp-nn issue #7 때문에 16바이트 정렬함. 펌웨어에 `heap_caps_aligned_calloc(16, …)` 버전으로 덮어써(weak) 해결. 팀원1이 겪은 v17 크래시와 같은 증상.
- ESP-NN 끄기 시험(`--build-property compiler.c(pp).extra_flags=-DEI_CLASSIFIER_TFLITE_ENABLE_ESP_NN=0`)은 적용됨(추론 143→3597ms) — 점수 0 문제는 ESP-NN 탓 아님.
- 점수 0 원인 찾기: Studio Raw features로 static buffer 시험 → 보드 face 0.996(Studio와 일치) → 모델·SDK 정상. 시리얼 스냅샷(`s`)으로 본 입력이 (1) 상하 뒤집힘(넣었던 vflip이 이 모듈엔 불필요) (2) 빨강·파랑 바뀜(코어 3.3.x `fmt2rgb888`은 RGB인데 EI 예제는 BGR로 뒤집음) → 둘 다 고침.
- v17은 그래도 우리 카메라 영상(뿌옇고 대비 낮음)에 약함: 같은 사진이 원본 0.1 미만, 채널별 1~99% 대비 늘리기 후 0.86. 대비 보정 넣고 앉은 상태 face 64%, 빈자리 오탐 2.5%. 다만 화면을 보는 자연스러운 자세에서는 평균 0.11로 떨어짐.
- v19(팀원1, SHA256 일치)로 교체: dsp 2ms·infer 51ms, 초당 약 7회. **대비 보정은 v19에서 역효과**(앉은 상태 0.7 이상 37/102 → 끄니 95/102, 평균 0.53 → 0.92) → 제거.
- USB 시리얼 막힘: PC가 시리얼을 안 읽으면 detect 초당 4 → 0.4. `Serial.setTxTimeoutMs(0)`로 해결(10초 4개 → 39개). 서버가 잠깐 `no_device`로 바뀌던 원인.
- `frame` 펌웨어 쪽: 카메라가 이미 JPEG라 변환 없이 `beginPublish/write/endPublish`, `FRAME_INTERVAL_MS` 500. 장당 약 8KB, 10초 detect 68·frame 17·bad 0(detect 속도 그대로).
- 캡처 모드 `CAPTURE_MODE`: 모델 입력을 흑백 `FRAME W H <hex>`로 → 팀원4 `capture.py`로 3장 저장 확인.
- 카메라 위치: 모니터 옆에 두면 화면을 볼 때 옆얼굴 → 거의 못 잡음. 모니터 위 가운데.
- 웹(팀원3에게 전달): `index.html`이 `iframe_api`를 `app.js`보다 먼저 불러, API가 캐시로 빨리 준비되면 `onYouTubeIframeAPIReady`가 정의 전에 지나가 "플레이어가 준비되지 않았습니다"에 멈춤(campip.js 추가 후 재현).
- 이 PC 로컬값(git 아님): `FACE_THRESHOLD` 0.7, 서버 `.env` `FACE_ON_MS` 500. 팀 기본값은 그대로(0.6 / 300).

## 2026-10-30 시연 후: 끊김 원인과 기본값 변경 (팀원2 김세광)
- 증상: 시험 중 몇십 초마다 `no_device`(영상 멈춤) → `offline`/`online` 재접속. 시리얼에 재부팅 흔적 없음(발열·전원 아님), MQTT만 재접속하고 출력이 2~8초씩 멈춤.
- 설정별 측정(서버 `/health`·로그):

| 설정 | 시간 | 끊김(no_device/offline) | detect/초 |
|---|---|---|---|
| 안테나 없음, 영상 0.5초 | 1분 | 몇십 초마다 | 들쭉날쭉 |
| 안테나 없음, 영상 끔 | 90초 | 2 | 6.8 |
| 안테나 없음, 영상 끔, **절전 끔** | 120초 ×2 | **0** | 7.0 |
| 안테나 없음, 절전 끔, 영상 1초 | 120초 | 2 | 5.3 |
| 안테나 없음, 절전 끔, 영상 1초, 타임아웃 6초 | 150초 | 3(연결 끊김 포함) | 4.2 |
| **안테나 연결**, 절전 끔, 영상 0.5초 | 2분(사용자 직접) | 약 1 | – |

- 원인 1 **Wi-Fi 절전(modem sleep)**: 전송이 수백 ms씩 밀려 약한 신호에서 3초 넘게 비었다. `WiFi.setSleep(false)` 한 줄로 해결.
- 원인 2 **안테나 빠짐**: 진단 스케치 스캔 — 끼우기 전 핫스팟 -87·공유기 -92 dBm·AP 2개, 끼운 뒤 -22·-52 dBm·AP 24개. 사진(8KB) 전송이 막히던 근본 원인.
- 팀 기본값 변경(D-008, 팀장 결정): `FACE_THRESHOLD` 0.6 → 0.7(`config.example.h`), `DEVICE_TIMEOUT_MS` 3000 → 6000(`.env.example`, `config.py` 기본값). 시험 코드는 값을 직접 넣어 영향 없음.
