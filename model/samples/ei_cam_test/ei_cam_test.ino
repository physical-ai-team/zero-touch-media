#include <ztmc-face-fomo_inferencing.h>
#include "esp_camera.h"

// XIAO ESP32S3 Sense (OV2640) pins
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  10
#define SIOD_GPIO_NUM  40
#define SIOC_GPIO_NUM  39
#define Y9_GPIO_NUM    48
#define Y8_GPIO_NUM    11
#define Y7_GPIO_NUM    12
#define Y6_GPIO_NUM    14
#define Y5_GPIO_NUM    16
#define Y4_GPIO_NUM    18
#define Y3_GPIO_NUM    17
#define Y2_GPIO_NUM    15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM  47
#define PCLK_GPIO_NUM  13

static const int W = EI_CLASSIFIER_INPUT_WIDTH;
static const int H = EI_CLASSIFIER_INPUT_HEIGHT;
static float *features;
#define USE_CAM 1
#define LED_PIN 21   // XIAO ESP32S3 주황 사용자 LED, LOW일 때 켜짐

static int get_data(size_t offset, size_t length, float *out) {
  memcpy(out, features + offset, length * sizeof(float));
  return 0;
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  for (int i = 0; i < 3; i++) { digitalWrite(LED_PIN, LOW); delay(150); digitalWrite(LED_PIN, HIGH); delay(150); }
  Serial.begin(115200);
  delay(1500);
  features = (float *)ps_malloc(W * H * sizeof(float));
  memset(features,0,W*H*sizeof(float));

  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0; c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_GRAYSCALE;
  c.frame_size = FRAMESIZE_QVGA;   // 320x240
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t err = esp_camera_init(&c);
  Serial.printf("camera init: 0x%x, model input %dx%d, labels %d\n", err, W, H, EI_CLASSIFIER_LABEL_COUNT);
}

void loop() {
#if USE_CAM
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { Serial.println("fb fail"); delay(200); return; }

  // center square crop, nearest-neighbor downsample, packed gray -> float
  int side = fb->height < fb->width ? fb->height : fb->width;
  int x0 = (fb->width - side) / 2, y0 = (fb->height - side) / 2;
  for (int y = 0; y < H; y++) {
    for (int x = 0; x < W; x++) {
      uint8_t g = fb->buf[(y0 + y * side / H) * fb->width + (x0 + x * side / W)];
      features[y * W + x] = (float)((g << 16) | (g << 8) | g);
    }
  }
  esp_camera_fb_return(fb);
#endif
#ifdef CAPTURE_MODE
  // 모델 입력 직전의 흑백 버퍼를 hex로 덤프 (학습 데이터 수집용). 추론은 건너뜀.
  Serial.printf("FRAME %d %d ", W, H);
  for (int i = 0; i < W * H; i++) Serial.printf("%02x", (uint8_t)((uint32_t)features[i] & 0xff));
  Serial.println();
  delay(1500);
  return;
#endif

  signal_t signal;
  signal.total_length = W * H;
  signal.get_data = &get_data;
  ei_impulse_result_t result = {0};
  EI_IMPULSE_ERROR e = run_classifier(&signal, &result, false);
  if (e != EI_IMPULSE_OK) { Serial.printf("classifier err %d\n", e); return; }

  bool face = false;
  for (uint32_t i = 0; i < result.bounding_boxes_count; i++) if (result.bounding_boxes[i].value > 0) face = true;
  digitalWrite(LED_PIN, face ? LOW : HIGH);
  Serial.printf("dsp %d ms, infer %d ms, faces %d", result.timing.dsp, result.timing.classification, (int)result.bounding_boxes_count);
  for (uint32_t i = 0; i < result.bounding_boxes_count; i++) {
    auto b = result.bounding_boxes[i];
    if (b.value == 0) continue;
    Serial.printf(" | %s %.2f @(%d,%d %dx%d)", b.label, b.value, b.x, b.y, b.width, b.height);
  }
  Serial.println();
}
