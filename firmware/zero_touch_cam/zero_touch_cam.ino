// Zero-Touch Media Control — ESP32-S3 카메라 펌웨어 (뼈대)
// 규격: docs/03-protocol.md, 펌웨어 안내: docs/04-firmware.md
//
// Wi-Fi + MQTT(LWT 포함) + hello + detect 발행.
// USE_FAKE_DETECT 1: 카메라 없이 가짜 detect, 0: XIAO ESP32S3 Sense 카메라 + Edge Impulse FOMO 추론.

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#if __has_include("config.h")
#include "config.h"
#else
#error "config.example.h 를 config.h 로 복사하고 Wi-Fi·브로커 주소를 채우세요."
#endif

#if !USE_FAKE_DETECT
// Edge Impulse 에서 받은 Arduino library 의 헤더. 모델 zip 을 바꾸면 이 이름도 바꾼다.
#include <ztmc-face-fomo_inferencing.h>
#include "edge-impulse-sdk/dsp/image/image.hpp"
#include "esp_camera.h"
#endif

#define FW_VERSION "0.2.0"
#define MQTT_KEEPALIVE_SEC 5   // 끊기면 브로커가 약 7.5초 뒤 LWT(offline) 발행
#define DETECT_INTERVAL_MS 200 // 가짜 모드 발행 주기. 실제 모드는 추론이 끝날 때마다 보낸다.
#define EI_MIN_SCORE 0.1f      // 모델이 상자로 돌려줄 최소 점수(기본 0.5). 낮춰서 score 에 기준 미만 값도 보이게 한다.

WiFiClient net;
PubSubClient mqtt(net);
String topicStatus, topicHello, topicDetect, topicFrame;

#ifndef FRAME_INTERVAL_MS
#define FRAME_INTERVAL_MS 500  // config.h 에 없으면 기본값. 0 이면 frame 을 안 보낸다.
#endif
uint32_t seq = 0;

struct Detection {
  bool face;
  float score;   // 가장 높은 얼굴 신뢰도, 없으면 0
  int count;     // FACE_THRESHOLD 이상인 얼굴 수
  int dsp_ms;
  int infer_ms;
};

// ---------- 카메라 (XIAO ESP32S3 Sense, OV2640) ----------

#if !USE_FAKE_DETECT
// 핀: arduino-esp32 CameraWebServer/camera_pins.h 의 CAMERA_MODEL_XIAO_ESP32S3
#define CAM_PIN_XCLK  10
#define CAM_PIN_SIOD  40
#define CAM_PIN_SIOC  39
#define CAM_PIN_Y9    48
#define CAM_PIN_Y8    11
#define CAM_PIN_Y7    12
#define CAM_PIN_Y6    14
#define CAM_PIN_Y5    16
#define CAM_PIN_Y4    18
#define CAM_PIN_Y3    17
#define CAM_PIN_Y2    15
#define CAM_PIN_VSYNC 38
#define CAM_PIN_HREF  47
#define CAM_PIN_PCLK  13

// QVGA JPEG 로 찍어 RGB888 로 풀고, 가운데를 정사각형으로 잘라 모델 입력 크기(EI_CLASSIFIER_INPUT_WIDTH/HEIGHT)로 줄인다.
#define CAM_COLS 320
#define CAM_ROWS 240

static uint8_t *snapshot_buf = nullptr;  // CAM_COLS*CAM_ROWS*3, PSRAM
static bool camera_ok = false;

bool camera_init() {
  camera_config_t c = {};
  c.pin_pwdn = -1;
  c.pin_reset = -1;
  c.pin_xclk = CAM_PIN_XCLK;
  c.pin_sccb_sda = CAM_PIN_SIOD;
  c.pin_sccb_scl = CAM_PIN_SIOC;
  c.pin_d7 = CAM_PIN_Y9;
  c.pin_d6 = CAM_PIN_Y8;
  c.pin_d5 = CAM_PIN_Y7;
  c.pin_d4 = CAM_PIN_Y6;
  c.pin_d3 = CAM_PIN_Y5;
  c.pin_d2 = CAM_PIN_Y4;
  c.pin_d1 = CAM_PIN_Y3;
  c.pin_d0 = CAM_PIN_Y2;
  c.pin_vsync = CAM_PIN_VSYNC;
  c.pin_href = CAM_PIN_HREF;
  c.pin_pclk = CAM_PIN_PCLK;
  c.xclk_freq_hz = 20000000;
  c.ledc_timer = LEDC_TIMER_0;
  c.ledc_channel = LEDC_CHANNEL_0;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_QVGA;
  c.jpeg_quality = 12;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;  // 늘 가장 최근 프레임

  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("[cam] init failed 0x%x\n", err);
    return false;
  }
  snapshot_buf = (uint8_t *)ps_malloc(CAM_COLS * CAM_ROWS * 3);
  if (!snapshot_buf) {
    Serial.println("[cam] snapshot buffer alloc failed");
    return false;
  }
  // 센서 설정은 기본값 그대로. XIAO Sense 의 OV3660 은 vflip 이 필요 없고(켜면 거꾸로 나와 얼굴을 못 찾음),
  // 밝기를 올리면 영상이 더 뿌예진다.
  sensor_t *s = esp_camera_sensor_get();
  Serial.printf("[cam] ok, sensor PID=0x%x\n", s->id.PID);
  return true;
}

// 카메라 화면 JPEG 를 ztmc/{id}/frame 으로 보낸다(웹 PiP 표시용, 판정에는 안 씀. docs/03-protocol.md).
// 카메라가 이미 JPEG 로 찍으므로 변환 없이 그대로 보낸다. PubSubClient 버퍼(512)보다 커서 나눠 쓴다.
static void publish_frame(const uint8_t *jpg, size_t len) {
#if FRAME_INTERVAL_MS > 0
  static uint32_t last = 0;
  if (!mqtt.connected() || millis() - last < FRAME_INTERVAL_MS) return;
  last = millis();
  if (!mqtt.beginPublish(topicFrame.c_str(), len, false)) return;
  mqtt.write(jpg, len);
  mqtt.endPublish();
#endif
}

// 촬영 → RGB888 → 모델 입력 크기 (snapshot_buf 앞부분에 덮어씀).
// 대비 보정은 넣지 않는다: v17(공개 원본)에는 도움이 됐지만 v19 는 오히려 떨어졌다(앉은 상태 평균 0.92 → 0.53).
bool camera_capture() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[cam] capture failed");
    return false;
  }
  if (fb->width != CAM_COLS || fb->height != CAM_ROWS) {
    // 버퍼보다 큰 프레임을 풀면 힙이 깨진다
    Serial.printf("[cam] unexpected frame %ux%u\n", fb->width, fb->height);
    esp_camera_fb_return(fb);
    return false;
  }
  publish_frame(fb->buf, fb->len);
  bool converted = fmt2rgb888(fb->buf, fb->len, PIXFORMAT_JPEG, snapshot_buf);
  esp_camera_fb_return(fb);
  if (!converted) {
    Serial.println("[cam] jpeg decode failed");
    return false;
  }
  ei::image::processing::crop_and_interpolate_rgb888(
      snapshot_buf, CAM_COLS, CAM_ROWS,
      snapshot_buf, EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
  return true;
}

// Edge Impulse SDK 의 ei_calloc 은 코어 3.x(IDF 5)에서 16바이트 정렬을 안 해서,
// ESP32-S3 ESP-NN 커널이 그 버퍼 끝을 넘어 써 힙이 깨진다(CORRUPT HEAP). 정렬된 버전으로 덮어쓴다.
void *ei_calloc(size_t nitems, size_t size) {
  return heap_caps_aligned_calloc(16, nitems, size, MALLOC_CAP_DEFAULT);
}

// Edge Impulse 가 특징값을 읽어 가는 콜백. 픽셀 하나를 0xRRGGBB 로 묶어 준다.
// 코어 3.3.x 의 fmt2rgb888 결과는 이미 RGB 순서다. Edge Impulse 예제처럼 BGR 로 뒤집으면
// 빨강·파랑이 바뀐 이미지가 모델에 들어가 얼굴을 못 찾는다(스냅샷으로 확인).
static int camera_get_data(size_t offset, size_t length, float *out) {
  size_t p = offset * 3;
  for (size_t i = 0; i < length; i++, p += 3) {
    out[i] = (snapshot_buf[p] << 16) + (snapshot_buf[p + 1] << 8) + snapshot_buf[p + 2];
  }
  return 0;
}
#endif

// ---------- 추론 ----------

bool run_inference(Detection &d) {
#if USE_FAKE_DETECT
  bool on = (millis() / 5000) % 2 == 0;
  d.face = on;
  d.score = on ? 0.85f : 0.0f;
  d.count = on ? 1 : 0;
  d.dsp_ms = 0;
  d.infer_ms = 0;
  delay(DETECT_INTERVAL_MS);
  return true;
#else
  if (!camera_ok) {
    camera_ok = camera_init();
    if (!camera_ok) {
      delay(2000);
      return false;
    }
  }
  if (!camera_capture()) return false;

#ifdef CAPTURE_MODE
  // 캡처 모드(팀원4 model/testing/capture.py): 추론·발행 없이 모델 입력을 흑백 'FRAME W H <hex>' 한 줄로 내보낸다.
  {
    const size_t px = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
    Serial.printf("FRAME %d %d ", EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
    for (size_t i = 0; i < px; i++) {
      const uint8_t *p = snapshot_buf + i * 3;
      Serial.printf("%02x", (p[0] * 77 + p[1] * 150 + p[2] * 29) >> 8);  // RGB → 밝기(ITU-R BT.601)
    }
    Serial.println();
    return false;
  }
#endif

  // 디버그: 시리얼로 's' 를 보내면 모델 입력(RGB)을 16진수로 한 번 내보낸다.
  // 픽셀은 R,G,B 순서.
  if (Serial.available() && Serial.read() == 's') {
    const size_t n = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT * 3;
    Serial.printf("[snap] begin %dx%d rgb\n", EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
    for (size_t i = 0; i < n; i++) {
      Serial.printf("%02x", snapshot_buf[i]);
      if (i % 96 == 95) Serial.println();
    }
    Serial.println("[snap] end");
  }

  ei::signal_t signal;
  signal.total_length = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
  signal.get_data = &camera_get_data;

  ei_impulse_result_t result = {};
  EI_IMPULSE_ERROR err = run_classifier(&signal, &result, false);
  if (err != EI_IMPULSE_OK) {
    Serial.printf("[ei] run_classifier error %d\n", err);
    return false;
  }

  // FOMO 는 EI_MIN_SCORE 이상인 칸만 상자로 준다. 얼굴 판정 기준은 FACE_THRESHOLD.
  d.score = 0.0f;
  d.count = 0;
  for (uint32_t i = 0; i < result.bounding_boxes_count; i++) {
    const ei_impulse_result_bounding_box_t &bb = result.bounding_boxes[i];
    if (bb.value == 0 || strcmp(bb.label, "face") != 0) continue;
    if (bb.value > d.score) d.score = bb.value;
    if (bb.value >= FACE_THRESHOLD) d.count++;
  }
  d.face = d.count > 0;
  d.dsp_ms = result.timing.dsp;
  d.infer_ms = result.timing.classification;
  return true;
#endif
}

// ---------- 연결 ----------

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("[wifi] connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // 기본 절전(modem sleep)은 전송을 수백 ms씩 밀어, 약한 신호에서 detect 가 3초 넘게 끊긴다
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\n[wifi] ok, ip=%s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    connectWifi();
    Serial.printf("[mqtt] connecting to %s:%d ... ", MQTT_HOST, MQTT_PORT);
    String clientId = String("ztmc-") + DEVICE_ID;
    // LWT: 갑자기 끊기면 브로커가 status=offline(retain)을 대신 발행
    if (mqtt.connect(clientId.c_str(), nullptr, nullptr, topicStatus.c_str(), 1, true, "offline")) {
      Serial.println("ok");
      mqtt.publish(topicStatus.c_str(), "online", true);
      JsonDocument hello;
      hello["device_id"] = DEVICE_ID;
      hello["fw"] = FW_VERSION;
      hello["model"] = USE_FAKE_DETECT ? "fake" : "edge-impulse";
      hello["threshold"] = FACE_THRESHOLD;
      char buf[256];
      size_t n = serializeJson(hello, buf);
      mqtt.publish(topicHello.c_str(), (const uint8_t *)buf, n, true);
    } else {
      Serial.printf("failed rc=%d, retry in 2s\n", mqtt.state());
      delay(2000);
    }
  }
}

void publishDetect(const Detection &d) {
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["seq"] = ++seq;
  doc["face"] = d.face;
  doc["score"] = d.score;
  doc["count"] = d.count;
  doc["dsp_ms"] = d.dsp_ms;
  doc["infer_ms"] = d.infer_ms;
  char buf[256];
  size_t n = serializeJson(doc, buf);
  mqtt.publish(topicDetect.c_str(), (const uint8_t *)buf, n, false);
}

// ---------- 메인 ----------

void setup() {
  Serial.begin(115200);
#if ARDUINO_USB_MODE && ARDUINO_USB_CDC_ON_BOOT
  // USB-Serial/JTAG 는 PC 가 안 읽으면 출력마다 막혀 detect 가 초당 4회 → 0.4회로 떨어진다. 막히면 버린다.
  Serial.setTxTimeoutMs(0);
#endif
  delay(500);
  Serial.printf("\nZero-Touch cam fw %s, device %s\n", FW_VERSION, DEVICE_ID);

  String base = String(MQTT_PREFIX) + "/" + DEVICE_ID;
  topicStatus = base + "/status";
  topicHello = base + "/hello";
  topicDetect = base + "/detect";
  topicFrame = base + "/frame";

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setKeepAlive(MQTT_KEEPALIVE_SEC);
  mqtt.setBufferSize(512);  // 기본 256바이트는 hello/detect JSON에 빠듯함
#if !USE_FAKE_DETECT
  camera_ok = camera_init();
  // face/count 판정은 FACE_THRESHOLD 로 따로 한다
  EI_IMPULSE_ERROR th = set_threshold_postprocessing(&ei_default_impulse.impulse->postprocessing_blocks[0],
                                                     "min_score", EI_MIN_SCORE);
  Serial.printf("[ei] min_score=%.2f %s\n", EI_MIN_SCORE, th == EI_IMPULSE_OK ? "ok" : "FAILED");
#endif
  connectMqtt();
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  Detection d;
  if (run_inference(d)) {
    publishDetect(d);
    Serial.printf("#%lu face=%d score=%.2f count=%d dsp=%dms infer=%dms\n", (unsigned long)seq, d.face,
                  d.score, d.count, d.dsp_ms, d.infer_ms);
  }
}
