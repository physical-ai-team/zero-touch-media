# 4. 펌웨어 (담당: 팀원2)

코드: [firmware/zero_touch_cam/](../firmware/zero_touch_cam/). 규격: [03-protocol.md](03-protocol.md).

## 보드
- ESP32-S3 (QFN56) rev0.2, PSRAM 8MB, 플래시 8MB (esptool 및 FQBN esp32:esp32:XIAO_ESP32S3:PSRAM=opi 실측 완료)
- Arduino IDE: 도구 → PSRAM **OPI PSRAM** 켜기(모델·카메라 버퍼에 필요).
- 라이브러리: `PubSubClient` 2.8, `ArduinoJson` 7.x (라이브러리 매니저).
- 모델: 팀원1의 **v19** zip(`ei-ztmc-face-fomo-arduino-v19-L3-local.zip`, 64×64 흑백, TFLite Micro). zip을 풀어 `ztmc-face-fomo_inferencing` 폴더를 `Documents\Arduino\libraries\`에 넣는다(git에 안 올림). 다른 `*_inferencing` 라이브러리는 빼 둔다 — 둘 다 `edge-impulse-sdk`를 갖고 있어 엉뚱한 쪽을 집을 수 있다. 첫 빌드는 라이브러리 전체 컴파일로 약 10분, 이후 스케치만 바뀌면 1분 안쪽.
- 카메라: 이 보드는 **OV3660**(PID 0x3660). vflip 필요 없음.

## 처음 할 일 (순서)
1. `config.example.h` → `config.h` 복사, Wi-Fi와 `MQTT_HOST`(브로커 PC의 IP, `ipconfig`) 입력. `config.h`는 git에 안 올라간다.
2. `USE_FAKE_DETECT 1` 그대로 업로드 → 시리얼 모니터(115200)에 `[mqtt] ... ok` 확인.
3. PC에서 `"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 127.0.0.1 -t "ztmc/#" -v` 로 hello/detect가 오는지 확인(서버 없이 가능).
4. 위 모델 라이브러리 설치 → `USE_FAKE_DETECT 0` → 시리얼에 `#n face=.. score=.. dsp=..ms infer=..ms`가 나오면 끝(v19: dsp 2ms, infer 51ms, 초당 약 7회).

## config.h 값
| 값 | 기본 | 뜻 |
|---|---|---|
| `FACE_THRESHOLD` | 0.6 | 이 점수 이상인 얼굴이 있으면 `face=true` |
| `USE_FAKE_DETECT` | 1 | 1이면 카메라·모델 없이 가짜 detect |
| `FRAME_INTERVAL_MS` | 500 | 카메라 JPEG를 `ztmc/{id}/frame`으로 보내는 간격(웹 PiP용, 판정에 안 씀). 0이면 끔 |
| `CAPTURE_MODE` | 꺼짐 | 켜면 추론 대신 흑백 `FRAME W H <hex>`를 시리얼로(팀원4 `model/testing/capture.py`) |

## 디버깅
- 모델이 실제로 보는 그림: 시리얼로 `s` 한 글자를 보내면 `[snap] begin W H rgb` ~ `[snap] end` 사이에 모델 입력을 16진수로 한 번 내보낸다.
- `score`는 모델 기준(`EI_MIN_SCORE` 0.1) 이상이면 그대로 실린다 → 0.6 미만 점수도 보이므로 "아깝게 못 넘는지, 아예 반응이 없는지"를 가를 수 있다.
- 스케치가 아닌 Edge Impulse 쪽을 의심할 때: Studio의 Live classification → Raw features를 그대로 넣는 static buffer 시험. 보드 결과가 Studio와 같으면 모델·라이브러리는 정상.

## 지킬 것
- keepalive 5초, LWT `offline`(retain), 접속 직후 `online`·`hello`(retain) — 뼈대에 이미 들어 있다. 바꾸지 않는다.
- 얼굴 판정 기준값은 `FACE_THRESHOLD`. 재생/정지 디바운스는 서버가 하므로 펌웨어에 넣지 않는다.

## 위험·겪은 문제
- **EON 라이브러리 + 코어 3.x = 힙 깨짐(CORRUPT HEAP / StoreProhibited)**: Edge Impulse SDK의 `ei_calloc`이 IDF 5에서 16바이트 정렬을 안 해 ESP32-S3 ESP-NN이 버퍼 끝을 넘어 쓴다. 펌웨어에 정렬된 `ei_calloc`을 넣어 해결(라이브러리는 안 고침). v17(공개 원본, EON)도 이걸로 정상 동작 확인.
- **색 순서**: 코어 3.3.x의 `fmt2rgb888`은 RGB 순서다. Edge Impulse 예제처럼 BGR로 뒤집으면 모델이 얼굴을 못 찾는다.
- **USB 시리얼 막힘**: PC가 시리얼을 안 읽으면 출력마다 막혀 detect가 초당 4회 → 0.4회로 떨어진다. `Serial.setTxTimeoutMs(0)`으로 해결.
- 카메라는 **보는 화면 쪽(모니터 위)**에 둔다. 옆에 두면 화면을 볼 때 옆얼굴이 되어 못 잡는다.
- 보드 Wi-Fi 수신이 약하다(안테나 점검 전). 폰 핫스팟을 보드 가까이.

## 한글 사용자 이름 PC
사용자 폴더가 `C:\Users\홍길동`처럼 한글이면 링크 단계에서 `cannot find -lxtensa` / `cannot open output file ... .elf`로 실패한다(코어가 AppData 아래에 있어서). PowerShell에서:
```powershell
subst W: "$env:LOCALAPPDATA\Arduino15"; subst V: "$env:USERPROFILE\Documents\Arduino"
$env:ARDUINO_DIRECTORIES_DATA='W:\'; $env:ARDUINO_DIRECTORIES_USER='V:\'
$cli = "C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
& $cli compile --fqbn esp32:esp32:XIAO_ESP32S3 --build-path C:\ztmc_build firmware\zero_touch_cam
& $cli upload  --fqbn esp32:esp32:XIAO_ESP32S3 --build-path C:\ztmc_build -p COM10 firmware\zero_touch_cam
subst W: /D; subst V: /D
```
저장소도 영문 경로(예: `C:\dev\zero-touch-media`)에 둔다.
