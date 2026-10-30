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

## 0단계: 사이트 후보 고르기 (10-30 오전)
Edge Impulse 공개 프로젝트 검색 "Face detection"(object detection) 결과 8개. 기준: **ESP32-S3에서 돌 만큼 작고(FOMO), 흑백 입력, 라벨이 `face` 하나, 바로 복제·배포 가능**.
상세 페이지까지 연 것은 2개, 나머지는 검색 결과 이름으로만 판단했다(그 자리에서 기록하지 않아 10-30 오후에 세션 로그에서 복원).

| 후보 | 구조·입력 | 데이터 | 판단 |
|---|---|---|---|
| **Louis Moreau / Face detection - FOMO - Embedded Online Conference (public/96468)** | FOMO MNv2 0.1, **96×96 흑백** | FFHQ 일부 406장 | **선택** — 가장 작은 FOMO, 흑백, 라벨 `face` 하나. 공개 페이지 정확도 val 77.6%, test 53.4% |
| Developer Relations / Face detection - FOMO - bigger dataset (public/116394) | FOMO MNv2 0.35, 96×96 **RGB** | FFHQ(수동 라벨, 더 많음) | 탈락 — RGB·0.35라 더 무겁다. 데이터가 많은 장점은 우리 재학습(증강·WIDER)으로 대신 |
| Demo Team / FOMO: Face Detection 96x96 RGB | FOMO, RGB | – | 이름만 봄. RGB라 흑백 96468보다 무거움 |
| Dmitry / Face detection - FOMO, Charity / Face detection - FOMO | FOMO | – | 이름만 봄. 같은 계열이라 원본 격인 96468로 대표 |
| Edge Impulse Experts / Face Detection (YOLOpro) | YOLO 계열 | – | 이름만 봄. ESP32-S3에는 무겁다 |
| Alif Semiconductor / Face detection with FOMO and YOLOv5 | FOMO + YOLOv5 | – | 이름만 봄. Alif 보드용·YOLOv5 무거움 |
| Edge Impulse Experts / Face detection for AI Bell | – | – | 이름만 봄. 특정 장치용 |

한계: 후보끼리 같은 테스트셋으로 정확도를 재지는 않았다. 대신 고른 96468을 출발점으로 학습 설정·입력 크기·데이터를 바꿔 개선했다(아래 실험).

## 실험 표
F1·P·R은 test set(float32, 88장 137개 얼굴) 값. Model testing에서 int8은 무료 계정이라 선택 불가. ms·RAM·Flash는 int8 + EON, ESP-EYE 추정.

| # | impulse | 바꾼 것 | 입력 | 백본 | 에폭/LR/증강 | F1 test | P / R | val F1 (int8) | ESP 추정 ms | RAM | Flash | 메모 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | **공개 원본** (배포본, v17 zip) | 96 흑백 | FOMO MNv2 0.1 | 70 / 0.00015 / 끔 | 0.69 | 0.87 / 0.57 | 76.5% | 728 | 240K | 63.6K | 얼굴을 자주 놓침(재현율 낮음) |
| 1 | 2 | 원본 프로젝트의 다른 실험 | 96 흑백 | FOMO MNv2 0.35 | 30 / 0.0001 / 끔 | 0.71 | 0.60 / 0.87 | 80.4% | 1075 | 244K | 77.5K | 잘 잡지만 오탐 많음, 1.5배 느림 |

| 2 | 4 | #0 + LR 0.001 + 증강 | 96 흑백 | FOMO MNv2 0.1 | 70 / 0.001 / 켬 | 0.80 | 0.81 / 0.79 | 78.8% | 797 | 119K | 68.8K | 재현율 0.57→0.79, 속도 그대로 |
| 3 | 5 | #2 + 입력 64×64 | 64 흑백 | FOMO MNv2 0.1 | 70 / 0.001 / 켬 | **0.82** | 0.81 / 0.83 | 82.4% | **280** | **69K** | 68.8K | **현재 1위** — 원본 대비 2.6배 빠르고 RAM 1/3.5, 정확도도 높음 |
| 4 | 6 | #1 + LR 0.001 + 증강 | 96 흑백 | FOMO MNv2 0.35 | 70 / 0.001 / 켬 | 0.80 | 0.93 / 0.69 | 88.4% | 990 | 115K | 81.0K | val은 최고지만 test에선 E3보다 낮고 3.5배 느림 → 탈락 |
| 5 | 7 | #3 + 입력 48×48 | 48 흑백 | FOMO MNv2 0.1 | 70 / 0.001 / 켬 | 0.77 | 0.80 / 0.74 | 82.8% | 269 | 52K | 68.9K | E3 대비 4%만 빠르고 정확도 하락 → 64가 적정점 |

**결론(10-30 12:15): E3(64×64 흑백, MNv2 0.1, LR 0.001, 증강)을 "우리 학습 v1"로 채택.**
원본 대비 test F1 0.69→0.82, 추정 지연 728→280ms(2.6배), RAM 240K→69K.

## 메모
- 10-30 11:30 Edge Impulse ESP-EYE 추정 ms는 ESP32(구형, SIMD 없음) 기준이라 매우 크게 나온다. ESP32-S3는 ESP-NN 가속으로 훨씬 빠를 것 — **상대 비교용**으로만 쓰고, 실제 값은 보드 `infer_ms`로 확인.
- 원본 0.1 모델은 LR 0.00015로 낮다. FOMO 기본값 0.001로 올리면 재현율이 오를지 확인할 것.
  → 확인(E2): LR 0.001 + 증강으로 test F1 0.69→0.80. 원본은 학습 부족이었다.
- E3: 64×64로 줄여도 정확도가 떨어지지 않았다. 우리 시연은 카메라 앞 한 사람이라 얼굴이 화면에서 크게 잡혀 저해상도로 충분하다. FOMO 출력 격자는 64 입력에서 8×8.
- 공개 원본 zip(v17): `C:\dev\ei-zips\ei-ztmc-face-fomo-arduino-v17-public-original.zip` (git에 안 올림, 컴파일 담당에 전달함). 펌웨어는 `EI_CLASSIFIER_INPUT_WIDTH/HEIGHT`를 쓰고 96을 하드코딩하지 말 것.

## 로컬 학습 (10-30 오후, EI 무료 학습 시간 소진 후)
같은 기준: WIDER FACE val에서 만든 64×64 흑백 5,105장(얼굴 4,132개), **EI Arduino 라이브러리를 PC에서 통째로 실행**(`model/train/pc_harness/`, DSP·FOMO 후처리 포함). 학습은 WIDER train 41,067장(`build_dataset.py`).

| # | 바꾼 것 | 결과 (WIDER val) | 메모 |
|---|---|---|---|
| E3 (v18) | 기준선, EON | F1 **0.642** (P 0.66 R 0.62), PC 9.9ms | 정면 사진(FFHQ) 위주 학습이라 다양한 사진에서 떨어짐 |
| L1 | MNv2 0.35 ImageNet, 얼굴 가중치 100 | float F1 0.51 (P 0.34 R 0.98) | 오탐 과다, 저장 실패(한글 Temp) |
| L2 | MNv2 0.1 처음부터, 가중치 100 | float F1 0.53 (P 0.36 R 0.98) | 오탐 과다 |
| **L3 (v19)** | MNv2 0.1 처음부터, **가중치 10**, 가려진 얼굴 무시, 30에폭 | int8 F1 **0.748** (P 0.74 R 0.76) @임계값 0.6, PC **4.4ms** | **채택 후보** — 보드 실측 대기 |

- 얼굴 가중치 100(EI 기본)은 우리 데이터에선 오탐이 너무 많았다. 10으로 낮추자 정밀도 0.34→0.74.
- L3는 파라미터 10.6K, TFLite 41KB. EON 대신 TFLite Micro(`swap_model.py`)로 v18 라이브러리에 끼움 — arena 64KB는 할당 실패, 128KB 정상.
- 임계값 0.6이 F1 최고(0.5: 0.725, 0.7: 0.744, 0.8: 0.708). 오탐을 더 줄이려면 0.7~0.8(정밀도 0.82~0.89).
- 남은 확인: 보드 `infer_ms`, 시연 카메라에서의 감지율·오탐률(팀원4 `model/testing/measure.py`).

#### 데이터·모델 출처 (v19)
- **데이터:** WIDER FACE (Yang et al., CVPR 2016, <http://shuoyang1213.me/WIDERFACE/>). 실제로 받은 곳은 Hugging Face 미러 [`CUHK-CSE/wider_face`](https://huggingface.co/datasets/CUHK-CSE/wider_face)이다. 파일은 `data/WIDER_train.zip`, `data/WIDER_val.zip`, `data/wider_face_split.zip`이고 2026-10-30 12:03~12:06에 받았다. 이 PC의 위치는 `C:\dev\ztm-data\wider\`(git 제외).
- **분할:** 공식 분할을 그대로 쓴다. train 12,880장에서 학습용 정사각형 41,067장을 잘랐다(seed 2·3 두 벌). val 3,226장에서 검증용 5,105장을 잘랐다(seed 1). 공식 test는 정답이 공개되지 않아 쓰지 않았다.
- **라이선스:** CC BY-NC-ND 4.0(비상업·출처 표시·변경물 배포 금지). 수업 프로젝트(비상업)에서 학습과 발표에 쓰는 것은 조건 안이라고 본다.
  - 잘라낸 데이터(npz)와 원본 이미지는 git이나 공개 저장소에 올리지 않는다.
  - 발표 자료에 출처(논문 인용)를 적는다.
  - 학습한 모델을 외부에 공개 배포하는 것이 "변경물 배포"에 해당하는지는 해석이 갈린다. 그래서 v19 zip은 팀 안에서만 쓴다. (법률 판단이 아니라 라이선스 문구를 읽은 정리다.)
- **모델 구조:** Keras로 직접 구성했다(`model/train/train_fomo.py`). Edge Impulse FOMO와 같은 형태로, MobileNetV2 α=0.1의 `block_6_expand_relu`까지 쓰고 그 뒤에 1×1 Conv 32(relu)와 1×1 Conv 2(softmax)를 붙였다. 입력은 64×64×1, 출력은 8×8×2이다.
  - **사전학습 가중치는 쓰지 않았다**(`--no-pretrained`, 무작위 초기화). Keras에는 α=0.1의 ImageNet 가중치가 없다. ImageNet 가중치를 쓴 L1(α=0.35)은 탈락했다.

## 보드 실측 (10-30 14시, XIAO ESP32S3 + OV2640, 코어 3.3.12, 창2/팀원2)
| 모델 | 엔진 | 빌드 | 크래시 | dsp / 추론 | 정면 50~80cm | 아주 가까운 얼굴 | 얼굴 없음 오탐 |
|---|---|---|---|---|---|---|---|
| v17 공개 원본 | EON | 성공 | **추론 중 힙 손상 → 재부팅 반복** | – | – | – | – |
| **v19 (L3)** | TFLite Micro | Flash 694KB(20%), RAM 40.7KB(12%) | **없음** | **2 / 50 ms** (카메라 포함 약 6fps) | 잡음, value 0.64~0.79 | **못 잡음**(143프레임 연속 0) | 미측정 |

- 크래시: v17(EON, ESP-NN 켬)은 크래시, v19(TFLite Micro, ESP-NN 켬)는 정상 → ESP-NN보다 EON 경로 문제로 좁혀짐. v18도 EON이라 같은 위험 → **v19 유지**.
- 가까운 얼굴 실패 원인: 학습 데이터를 얼굴이 화면 15~55%인 장면만으로 만듦(`build_dataset.py`). 화면을 채우는 얼굴은 학습에 없음 → 범위를 넓혀 재학습(v20) 예정.
- 캡처 모드 첫 1~2프레임은 카메라 워밍업으로 어두움(평균 밝기 54, 이후 약 140) → 버린다.

