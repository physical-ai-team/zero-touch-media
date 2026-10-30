# 4. 펌웨어 (담당: 팀원2)

코드: [firmware/zero_touch_cam/](../firmware/zero_touch_cam/). 규격: [03-protocol.md](03-protocol.md).

## 보드
- ESP32-S3 (QFN56) rev0.2, PSRAM 8MB, 플래시 8MB (esptool 및 FQBN esp32:esp32:XIAO_ESP32S3:PSRAM=opi 실측 완료)
- Arduino IDE: 도구 → PSRAM **OPI PSRAM** 켜기(모델·카메라 버퍼에 필요).
- 라이브러리: `PubSubClient` 2.8, `ArduinoJson` 7.x (라이브러리 매니저).

## 처음 할 일 (순서)
1. `config.example.h` → `config.h` 복사, Wi-Fi와 `MQTT_HOST`(브로커 PC의 IP, `ipconfig`) 입력. `config.h`는 git에 안 올라간다.
2. `USE_FAKE_DETECT 1` 그대로 업로드 → 시리얼 모니터(115200)에 `[mqtt] ... ok` 확인.
3. PC에서 `"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 127.0.0.1 -t "ztmc/#" -v` 로 hello/detect가 오는지 확인(서버 없이 가능).
4. Edge Impulse 라이브러리 zip 설치(`model/README.md`) → `run_inference()`의 TODO 채우기 → `USE_FAKE_DETECT 0`.
5. `detect`의 `infer_ms`, `dsp_ms`를 실제 값으로 채운다(측정표에 쓴다).

## 기다리지 않고 작업하기
- 팀원1의 모델을 기다리지 말고 **Edge Impulse 공개 Face detection 프로젝트를 그대로 배포한 zip**으로 먼저 붙인다. 나중에 zip만 교체.
- 서버가 없어도 3번의 `mosquitto_sub`로 확인할 수 있다.

## 지킬 것
- keepalive 5초, LWT `offline`(retain), 접속 직후 `online`·`hello`(retain) — 뼈대에 이미 들어 있다. 바꾸지 않는다.
- 얼굴 판정 기준값은 `FACE_THRESHOLD`. 재생/정지 디바운스는 서버가 하므로 펌웨어에 넣지 않는다.

## 위험
- Edge Impulse의 ESP32 카메라 예제는 예전에 코어 2.0.x 기준이었다. 3.3.12에서 빌드가 안 되면 보드 매니저에서 esp32 코어 2.0.17로 내리고 `decisions.md`에 기록.
- 강의실 Wi-Fi가 기기 간 통신을 막으면 폰 핫스팟 사용.

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
