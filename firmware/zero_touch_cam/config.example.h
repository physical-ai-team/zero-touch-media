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
// 이 값 이상인 얼굴이 하나라도 있으면 face=true. 서버의 MIN_SCORE 와 맞춘다.
#define FACE_THRESHOLD 0.6f

// 1 이면 카메라·모델 없이 5초마다 얼굴 있음/없음을 번갈아 보낸다(연결 시험용).
// Edge Impulse 모델을 붙이면 0 으로 바꾼다.
#define USE_FAKE_DETECT 1
