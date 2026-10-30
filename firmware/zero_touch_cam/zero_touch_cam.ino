// Zero-Touch Media Control — ESP32-S3 카메라 펌웨어 (뼈대)
// 규격: docs/03-protocol.md, 펌웨어 안내: docs/04-firmware.md
//
// 지금 상태: Wi-Fi + MQTT(LWT 포함) + hello + 가짜 detect 발행까지.
// 펌웨어 담당이 할 일: run_inference() 안을 Edge Impulse 카메라 추론으로 바꾸기 (USE_FAKE_DETECT 0).

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#if __has_include("config.h")
#include "config.h"
#else
#error "config.example.h 를 config.h 로 복사하고 Wi-Fi·브로커 주소를 채우세요."
#endif

#define FW_VERSION "0.1.0"
#define MQTT_KEEPALIVE_SEC 5   // 끊기면 브로커가 약 7.5초 뒤 LWT(offline) 발행
#define DETECT_INTERVAL_MS 200 // 가짜 모드 발행 주기. 실제 모드는 추론이 끝날 때마다 보낸다.

WiFiClient net;
PubSubClient mqtt(net);
String topicStatus, topicHello, topicDetect;
uint32_t seq = 0;

struct Detection {
  bool face;
  float score;   // 가장 높은 얼굴 신뢰도, 없으면 0
  int count;     // FACE_THRESHOLD 이상인 얼굴 수
  int dsp_ms;
  int infer_ms;
};

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
  // TODO(펌웨어 담당): Edge Impulse 라이브러리 연결
  //  1) #include <프로젝트이름_inferencing.h> 와 esp_camera 초기화(setup 에서)
  //  2) 프레임 캡처 → run_classifier(&signal, &result)
  //  3) result.bounding_boxes 중 value >= FACE_THRESHOLD 인 것을 세고, 최대값을 score 로
  //  4) d.dsp_ms = result.timing.dsp; d.infer_ms = result.timing.classification;
  return false;
#endif
}

// ---------- 연결 ----------

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("[wifi] connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
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
  delay(500);
  Serial.printf("\nZero-Touch cam fw %s, device %s\n", FW_VERSION, DEVICE_ID);

  String base = String(MQTT_PREFIX) + "/" + DEVICE_ID;
  topicStatus = base + "/status";
  topicHello = base + "/hello";
  topicDetect = base + "/detect";

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setKeepAlive(MQTT_KEEPALIVE_SEC);
  mqtt.setBufferSize(512);  // 기본 256바이트는 hello/detect JSON에 빠듯함
  connectMqtt();
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  Detection d;
  if (run_inference(d)) {
    publishDetect(d);
    Serial.printf("#%lu face=%d score=%.2f infer=%dms\n", (unsigned long)seq, d.face, d.score, d.infer_ms);
  }
}
