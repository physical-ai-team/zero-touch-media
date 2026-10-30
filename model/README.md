# 모델 (담당: 팀원1)

## 순서
1. Edge Impulse 공개 프로젝트 검색: <https://www.edgeimpulse.com/projects/all?project=Face%20detection&projectTypes=object-detection>
2. 마음에 드는 프로젝트 **Clone** → 내 계정에서 데이터·임펄스 확인.
3. 대상 장치 **Espressif ESP-EYE (ESP32 240MHz)** 또는 ESP32-S3 계열로 설정, 입력 96×96 그레이스케일 FOMO 권장(작고 빠름).
4. 학습 → Model testing으로 정확도 확인 → **Deployment → Arduino library** → zip 다운로드.
5. zip은 git에 올리지 않는다. 팀원2에게 전달(메신저/드라이브)하고 아래 표를 채운다.

## 기록 (발표 자료용)
| 버전 | Edge Impulse 프로젝트 링크 | 입력 | 모델 | 정확도(F1) | RAM | Flash | 보드 추론 ms | 날짜 |
|---|---|---|---|---|---|---|---|---|
| 공개 원본 | | | | | | | | |
| 우리 학습 v1 | | | | | | | | |

## 지킬 것
- 라벨 이름은 `face` 로 통일(펌웨어가 이 라벨로 센다). 바꾸면 팀원2와 맞춘다.
