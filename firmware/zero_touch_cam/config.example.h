// 이 파일을 같은 폴더에 config.h 로 복사해서 값을 채운다. config.h 는 git에 올라가지 않는다(.gitignore).
#pragma once

// --- Wi-Fi (PC와 같은 네트워크) ---
#define WIFI_SSID     "your-ssid"
#define WIFI_PASSWORD "your-password"

// --- MQTT 브로커 = Mosquitto 를 실행한 PC의 LAN IP (ipconfig 로 확인) ---
#define MQTT_HOST     "192.168.0.10"
#define MQTT_PORT     1883
#define MQTT_PREFIX   "ztmc"
#define DEVICE_ID     "cam-1"

// --- 판정 ---
// 이 값 이상인 얼굴이 하나라도 있으면 face=true. 서버 MIN_SCORE(0.6)보다 높아서 이 값이 실제 기준이 된다.
// 0.7: v19 실측에서 앉은 정면은 대부분 0.9 근처라 여유가 있고, 빈자리 오탐(점수가 가끔 튀는 것)을 줄인다.
#define FACE_THRESHOLD 0.7f

// 1 이면 카메라·모델 없이 5초마다 얼굴 있음/없음을 번갈아 보낸다(연결 시험용).
// Edge Impulse 모델을 붙이면 0 으로 바꾼다.
#define USE_FAKE_DETECT 1

// 카메라 화면(JPEG)을 ztmc/{id}/frame 으로 보내는 간격(ms). 웹 PiP 창 표시용, 판정에는 안 쓴다.
// Wi-Fi 가 약해 detect 가 밀리면 늘리거나 0(끔)으로.
#define FRAME_INTERVAL_MS 500

// 주석을 풀면(또는 빌드 옵션 -DCAPTURE_MODE) 추론 대신 모델 입력을 흑백 'FRAME W H <hex>'로 시리얼에 내보낸다.
// 팀원4 model/testing/capture.py 로 사진을 모을 때만 쓴다. USE_FAKE_DETECT 0 일 때만 동작.
// #define CAPTURE_MODE
