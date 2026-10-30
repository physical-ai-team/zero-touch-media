# 모델 비교 실험 기록 (담당: 팀원1)

목표: **ESP32-S3에서 더 빠르고 더 정확한** 얼굴 검출. 라벨 `face`, FOMO 계열.
시간 순서대로 짧게 적는다. 최종 선택은 `README.md` 기록 표에 옮긴다.

## 기준
- 정확도: Edge Impulse Model testing의 **F1 (test set)**. Validation 수치는 참고만.
- 속도·메모리: Edge Impulse 추정치(대상 장치 기준, int8). 보드 실측(`infer_ms`)은 팀원2가 붙인 뒤 채운다.
- 대상 장치: Espressif ESP-EYE (ESP32 240MHz) — 실제 보드는 ESP32-S3라 실측이 이보다 빠를 수 있다.

## 프로젝트
| 이름 | 링크 | 비고 |
|---|---|---|
| 공개 원본 | https://studio.edgeimpulse.com/public/96468/latest | Louis Moreau, FFHQ 일부 406장, 96×96 흑백, BSD-3-Clause-Clear |
| 우리 복제본 | https://studio.edgeimpulse.com/studio/1152773 | `ztmc-face-fomo` (비공개, 계정 minff) |

## 실험 표
F1·P·R은 test set(float32, 88장 137개 얼굴) 값. Model testing에서 int8은 무료 계정이라 선택 불가. ms·RAM·Flash는 int8 + EON, ESP-EYE 추정.

| # | impulse | 바꾼 것 | 입력 | 백본 | 에폭/LR/증강 | F1 test | P / R | val F1 (int8) | ESP 추정 ms | RAM | Flash | 메모 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | **공개 원본** (배포본, v17 zip) | 96 흑백 | FOMO MNv2 0.1 | 70 / 0.00015 / 끔 | 0.69 | 0.87 / 0.57 | 76.5% | 728 | 240K | 63.6K | 얼굴을 자주 놓침(재현율 낮음) |
| 1 | 2 | 원본 프로젝트의 다른 실험 | 96 흑백 | FOMO MNv2 0.35 | 30 / 0.0001 / 끔 | 0.71 | 0.60 / 0.87 | 80.4% | 1075 | 244K | 77.5K | 잘 잡지만 오탐 많음, 1.5배 느림 |

| 2 | 4 | #0 + LR 0.001 + 증강 | 96 흑백 | FOMO MNv2 0.1 | 70 / 0.001 / 켬 | (학습 중) | | | | | | 정확도(재현율) 개선 시도 |
| 3 | 5 | #2 + 입력 64×64 | 64 흑백 | FOMO MNv2 0.1 | 70 / 0.001 / 켬 | (학습 중) | | | | | | 속도 개선 시도(픽셀 44%) |

## 메모
- 10-30 11:30 Edge Impulse ESP-EYE 추정 ms는 ESP32(구형, SIMD 없음) 기준이라 매우 크게 나온다. ESP32-S3는 ESP-NN 가속으로 훨씬 빠를 것 — **상대 비교용**으로만 쓰고, 실제 값은 보드 `infer_ms`로 확인.
- 원본 0.1 모델은 LR 0.00015로 낮다. FOMO 기본값 0.001로 올리면 재현율이 오를지 확인할 것.
