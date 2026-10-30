// PC(Windows/MinGW)용 Edge Impulse 포팅 함수. Arduino 포팅 파일 대신 링크한다.
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <thread>
#include "edge-impulse-sdk/porting/ei_classifier_porting.h"

static auto t_start = std::chrono::steady_clock::now();

EI_IMPULSE_ERROR ei_run_impulse_check_canceled() { return EI_IMPULSE_OK; }
void ei_serial_set_baudrate(int) {}
EI_IMPULSE_ERROR ei_sleep(int32_t ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); return EI_IMPULSE_OK; }
uint64_t ei_read_timer_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t_start).count();
}
uint64_t ei_read_timer_us() {
    return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - t_start).count();
}
void ei_putchar(char c) { fputc(c, stderr); }
char ei_getchar(void) { return 0; }
__attribute__((weak)) void ei_printf(const char *format, ...) {
    va_list a; va_start(a, format); vfprintf(stderr, format, a); va_end(a);
}
__attribute__((weak)) void ei_printf_float(float f) { fprintf(stderr, "%f", f); }
__attribute__((weak)) void *ei_malloc(size_t size) { return malloc(size); }
__attribute__((weak)) void *ei_calloc(size_t n, size_t size) { return calloc(n, size); }
__attribute__((weak)) void ei_free(void *p) { free(p); }

extern "C" void DebugLog(const char *s) { fputs(s, stderr); }
