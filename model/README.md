# 모델 (담당: 팀원1 박민성)

## 순서
1. Edge Impulse 공개 프로젝트 검색: <https://www.edgeimpulse.com/projects/all?project=Face%20detection&projectTypes=object-detection>
2. 마음에 드는 프로젝트 **Clone** → 내 계정에서 데이터·임펄스 확인.
3. 대상 장치 **Espressif ESP-EYE (ESP32 240MHz)** 또는 ESP32-S3 계열로 설정, 입력 96×96 그레이스케일 FOMO 권장(작고 빠름).
4. 학습 → Model testing으로 정확도 확인 → **Deployment → Arduino library** → zip 다운로드.
5. zip은 git에 올리지 않는다. 팀원2에게 전달(메신저/드라이브)하고 아래 표를 채운다.
6. 공개 원본 모델 zip도 먼저 받아 팀원2에게 넘긴다 — 팀원2가 학습을 기다리지 않고 바로 이식을 시작할 수 있다.

## 기록 (발표 자료용)
선택 과정 전체(후보 고르기 → Edge Impulse 개선 → 로컬 학습 → 보드 실측)는 [model-selection.md](model-selection.md).
실험 전체와 이유는 [experiments.md](experiments.md). F1은 test set(float32), RAM·Flash·추정 ms는 int8 + EON의 ESP-EYE 추정치.
보드 추론 ms는 팀원2가 붙인 뒤 채운다.

| 버전 | Edge Impulse 프로젝트 링크 | 입력 | 모델 | 정확도(F1) | RAM | Flash | 추정 ms | 보드 추론 ms | 날짜 |
|---|---|---|---|---|---|---|---|---|---|
| 공개 원본 (zip v17) | [public/96468](https://studio.edgeimpulse.com/public/96468/latest) → 복제 [1152773](https://studio.edgeimpulse.com/studio/1152773) impulse 1 | 96×96 흑백 | FOMO MNv2 0.1 | 0.69 | 240K | 63.6K | 728 | | 10-30 |
| 우리 학습 v1 (zip v18, E3) | [1152773](https://studio.edgeimpulse.com/studio/1152773) impulse 5 | **64×64** 흑백 | FOMO MNv2 0.1, LR 0.001, 증강 | **0.82** | **69K** | 68.8K | **280** | | 10-30 |
| 우리 학습 v2 (zip v19, L3, **로컬**) | `model/train/` (WIDER FACE, EI 학습 시간 소진으로 로컬) | 64×64 흑백 | FOMO MNv2 0.1(처음부터), 얼굴 가중치 10, 임계값 0.6, TFLite Micro | WIDER 검증 **0.748** (같은 기준 v18 0.642) | arena 128K | 모델 41K | PC 4.4ms (v18 9.9ms) | **50** (dsp 2) | 10-30 |

zip 위치(이 PC): `C:\dev\ei-zips\` — git에 올리지 않는다.

v1(E3)과 v2(L3)의 F1은 기준이 다르다: v1 0.82는 EI 테스트셋(FFHQ 88장), v2 0.748은 WIDER 검증 5,105장(같은 기준에서 v1은 0.642). 둘 다 PC 하네스로 EI 라이브러리를 통째로 돌린 값은 WIDER 쪽.

## 지킬 것
- 라벨 이름은 `face` 로 통일(펌웨어가 이 라벨로 센다). 바꾸면 팀원2와 맞춘다.
- 입력 크기는 모델마다 다르다(v17 96, v18 64). 펌웨어는 `EI_CLASSIFIER_INPUT_WIDTH/HEIGHT`만 쓴다.
- 라이브러리 이름이 같아서(`ztmc-face-fomo_inferencing`) 교체할 때는 Arduino `libraries`에 있는 옛 폴더를 지우고 설치한다.
