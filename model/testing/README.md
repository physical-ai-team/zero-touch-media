# 시연 데이터 수집 · 실제 정확도 측정 (담당: 팀원4)

목표: **시연 장소·실제 보드 카메라**에서 모델이 얼마나 잘 잡는지 숫자로 남기고(발표용),
잘 못 잡는 장면의 사진을 모아 팀원1이 추가 학습에 쓰게 한다.

## 준비 (한 번)
1. 저장소 clone, `conda env create -f environment.yml` → `conda activate ztmc` (`HANDOFF.md` "이어서 시작하는 법" 4번)
2. `pip install -r model/testing/requirements.txt`
3. Mosquitto 설치(측정할 PC). 보드·PC는 같은 Wi-Fi(핫스팟). 자세한 건 `docs/04-firmware.md`, `CLAUDE.md` 4절.

## A. 정확도 측정 (보드가 실제 추론 펌웨어일 때)
1. 브로커 켜기: `"C:\Program Files\mosquitto\mosquitto.exe" -c broker\mosquitto.conf -v`
2. 보드 전원 → 보드가 브로커에 붙는지 `python tools/monitor.py`(있으면) 또는 `mosquitto_sub -t "ztmc/#" -v`로 확인
3. 측정: `python model/testing/measure.py --tag v18 --secs 20`
   - 상황 11개가 차례로 나온다(정면 50cm·1m·2m, 옆얼굴, 고개 숙임, 안경/마스크, 어둡게, 두 명, 빈 자리, 뒤로 지나감, 물건만).
   - 상황을 만들고 Enter → 20초 동안 보드가 보낸 판정을 센다. `s` 건너뛰기, `q` 끝.
   - 얼굴 있는 상황은 **감지율**(높을수록 좋음), 없는 상황은 **오탐률**(낮을수록 좋음).
4. 결과: `model/testing/results/<시각>-<tag>.md`(요약 표) · `.csv`(프레임별). **md는 커밋**한다.
5. 모델이 바뀌면(팀원1이 새 zip 전달 → 팀원2가 업로드) `--tag`만 바꿔 같은 순서로 다시 잰다 → 버전끼리 비교.

같은 조건으로 재야 비교가 된다: 같은 자리·조명·거리, 사람은 가능하면 같은 사람. 조건을 표 아래에 한 줄 적는다.

## B. 시연 데이터 수집 (추가 학습용)
1. 팀원2에게 **캡처 모드** 펌웨어(`-DCAPTURE_MODE`)를 올려 달라고 한다 → 시리얼로 모델 입력 그림이 1.5초마다 나온다.
2. `python model/testing/capture.py COM10 --label face` — 얼굴이 보이는 장면(거리·각도·조명·사람을 바꿔 가며, 200장 이상)
3. `python model/testing/capture.py COM10 --label none` — 얼굴 없는 장면(빈 자리, 지나가는 몸, 물건, 모니터 화면, 100장 이상)
4. **측정에서 틀린 상황**(오탐 높음 / 감지율 낮음)을 특히 많이 찍는다.
5. 저장 위치 `model/testing/captures/` 는 **git에 올리지 않는다**(사람 얼굴). 폴더째 압축해 팀원1에게 직접 전달.
   - 찍힌 사람에게 학습용으로 쓴다고 미리 말한다.

보드가 아직 안 될 때: 휴대폰으로 **시연 장소에서 카메라 위치·높이 그대로** 사진을 찍어 같은 폴더 구조(`face/`, `none/`)로 전달해도 된다(차선책).

## 결과를 어디에 적나
- 요약 표 md → `model/testing/results/` 커밋
- 모델 버전별 대표 숫자(정면 1m 감지율, 빈 자리 오탐률, 추론 ms) → `model/README.md` 기록 표의 "보드 추론 ms"·메모
- 상세 경위 → `docs/HISTORY.md` 맨 아래
