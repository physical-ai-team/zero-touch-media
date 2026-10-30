# 모델 → 펌웨어 인수인계 (담당: 팀원1 → 팀원2)

`firmware/`는 팀원2 담당이라 여기서는 고치지 않고, 보드에서 **실제로 돌려 확인한 것**과 참고 스케치만 넘긴다.

## 쓸 모델: v19 (L3, 로컬 학습)
| 항목 | 값 |
|---|---|
| zip | `ei-ztmc-face-fomo-arduino-v19-L3-local.zip` (5,207,020 B), `C:\dev\ei-zips\` — git에 올리지 않음 |
| SHA256 | `65f2618b1a6c9dbe322439bd22b087a078b355efa617b8516198755e9a49171e` |
| 라이브러리 / 헤더 | `ztmc-face-fomo_inferencing` / `<ztmc-face-fomo_inferencing.h>` |
| 입력 | **64×64 흑백**, 라벨 `face` 1개, 출력 8×8 |
| 판정 임계값 | 0.6 |
| 실행 방식 | **TFLite Micro** (`EI_CLASSIFIER_COMPILED 0`, EON 아님), ESP-NN 켜짐 |
| arena | 128KB (`ei_malloc`). 64KB는 `AllocateTensors()` 실패 |

설치할 때 기존 `libraries\ztmc-face-fomo_inferencing` 폴더를 **먼저 지운다**. 같은 이름이 둘이면 충돌한다.

## 보드 실측 (XIAO ESP32S3 Sense, ESP32 코어 3.3.12, PSRAM=opi)
- 빌드: Flash 694KB(20%), 전역 RAM 40.7KB(12%)
- 추론: `dsp 2ms`, `infer 50ms` 고정. 카메라 포함 루프는 초당 약 6프레임.
- 힙: 추론 전·후 `heap_caps_check_integrity_all` 정상, 재부팅 없음.
- 검출: 카메라에서 50~80cm, 정면일 때 `face` value 0.64~0.79, 박스 1~2개(FOMO 셀 단위).
- 약점: 얼굴이 화면을 거의 채울 만큼 가까우면 못 잡는다(143프레임 연속 0). 시연 거리를 50cm 이상으로 안내.
- 아직 안 잼: 얼굴 없음 구간의 오탐률, 옆모습, 1~2m 거리.

## 피해야 할 것 (실제로 겪음)
- **v17(EON 라이브러리)은 보드에서 크래시**한다. 카메라 초기화·`run_classifier` 직전까지 힙은 정상인데 `run_classifier` 안에서 힙이 깨져 `StoreProhibited`로 재부팅을 반복한다(EON 모델 코드의 `reset`에서 `ei_free`). v18(EON, E3)은 보드에서 **아직 안 돌려 봤다**. 같은 EON 라이브러리는 PC에서 5,105번 문제없이 돌았다. 원인은 확정 못 했다(ESP-NN 끄기 시험은 플래그가 안 먹어서 무효). **TFLite Micro 방식인 v19는 문제없다.** 결론: EON이 아닌 TFLite Micro 방식 zip을 쓴다.
- 입력 크기는 `EI_CLASSIFIER_INPUT_WIDTH/HEIGHT` 매크로만 쓴다. 96을 하드코딩하지 않는다.
- Windows 한글 사용자 경로 때문에 빌드가 실패하면 `docs/HISTORY.md`의 subst(W:, V:) 방법을 쓴다.

## 참고 스케치
`model/samples/ei_cam_test/ei_cam_test.ino` — 이 스케치로 위 실측을 냈다.
- OV2640(XIAO ESP32S3 Sense 핀) 흑백 QVGA → 중앙 정사각 크롭 → 모델 입력 크기로 줄여 `run_classifier`.
- 이식할 때 바꿀 부분: Serial 출력을 MQTT `detect` 메시지로(`face`, `score`, `infer_ms`, `dsp_ms`, `docs/03-protocol.md` 규격).
- 주황 LED(GPIO21, LOW=켜짐): 부팅 때 3번 깜빡이고, 얼굴이 검출되면 켜짐.
- `-DCAPTURE_MODE`로 빌드하면 추론 대신 `FRAME W H <hex>` 한 줄(한 프레임)을 시리얼로 덤프한다. `model/testing/capture.py`가 이걸 읽어 PNG로 저장한다. 첫 프레임은 카메라 워밍업으로 어두우니 앞 1~2장은 버린다.

## 모델 교체
새 zip을 받으면 같은 방식으로 라이브러리 폴더만 바꾼다. 입력 크기·라벨·출력 형식이 같으면 스케치는 그대로다. 교체할 때마다 위 실측 표(infer_ms·dsp_ms·크기)를 갱신해 `README.md` 기록 표에 반영한다.
