// Edge Impulse 라이브러리를 PC에서 그대로 돌려 정확도를 잰다 (보드와 같은 DSP·후처리).
// 입력: 64x64(또는 모델 입력 크기) 흑백 uint8 이미지가 이어 붙은 파일.
// 출력(표준 출력): 이미지마다 한 줄 "i n x y w h v ..." (모델 입력 좌표), 끝에 평균 ms.
#include <chrono>
#include <cstdio>
#include <cstring>
#include <vector>
#include "edge-impulse-sdk/classifier/ei_run_classifier.h"

static std::vector<float> g_buf;

static int get_data(size_t off, size_t len, float *out) {
    memcpy(out, g_buf.data() + off, len * sizeof(float));
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: harness images.u8\n"); return 1; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { fprintf(stderr, "open fail\n"); return 1; }
    const size_t N = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
    std::vector<uint8_t> img(N);
    g_buf.resize(N);
    double total_ms = 0; int count = 0;
    while (fread(img.data(), 1, N, f) == N) {
        for (size_t i = 0; i < N; i++) {
            uint32_t v = img[i];
            g_buf[i] = (float)((v << 16) | (v << 8) | v);   // 카메라 RGB888 묶음 형식
        }
        signal_t s; s.total_length = N; s.get_data = &get_data;
        ei_impulse_result_t r = {0};
        auto t0 = std::chrono::high_resolution_clock::now();
        EI_IMPULSE_ERROR e = run_classifier(&s, &r, false);
        auto t1 = std::chrono::high_resolution_clock::now();
        if (e != EI_IMPULSE_OK) { fprintf(stderr, "err %d\n", e); return 2; }
        total_ms += std::chrono::duration<double, std::milli>(t1 - t0).count();
        int n = 0;
        for (uint32_t k = 0; k < r.bounding_boxes_count; k++) if (r.bounding_boxes[k].value > 0) n++;
        printf("%d %d", count, n);
        for (uint32_t k = 0; k < r.bounding_boxes_count; k++) {
            auto &b = r.bounding_boxes[k];
            if (b.value <= 0) continue;
            printf(" %u %u %u %u %.3f", b.x, b.y, b.width, b.height, b.value);
        }
        printf("\n");
        count++;
    }
    fprintf(stderr, "images %d  avg %.3f ms\n", count, total_ms / (count ? count : 1));
    return 0;
}
