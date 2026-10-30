# HANDOFF — Zero-Touch Media Control

## 현재 상태 (2026-10-30)
- 뼈대 완료: 서버(판정 안정화 + MQTT 구독 + WebSocket), 가짜 ESP32, 최소 웹 페이지, 펌웨어 빈 스케치, 문서.
- 확인함: pytest 14개 통과. Mosquitto + 서버 + 가짜 ESP32로 present/absent/no_device(LWT) 전환 확인.
- 펌웨어 빈 스케치 컴파일 통과(XIAO_ESP32S3, 플래시 25%). 이 PC는 한글 경로 우회 필요(아래 교훈).
- 확인 못 함: 실제 보드 업로드, 브라우저 유튜브 실제 재생.

## 남은 일
- [ ] (팀장) 팀원 2명 저장소에 초대, `main` 보호 규칙 설정
- [ ] (팀장) Windows 방화벽 1883 인바운드 허용 — 관리자 PowerShell:
      `New-NetFirewallRule -DisplayName "Mosquitto 1883" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow`
- [ ] (팀원1) Edge Impulse 공개 Face detection 프로젝트 복제 → 학습 → Arduino library 배포 (`model/README.md`)
- [ ] (팀원1) 웹 페이지 다듬기 (`docs/05-web.md`)
- [ ] (팀원2) 보드명 확인, 펌웨어 컴파일·업로드, `USE_FAKE_DETECT 1`로 연결 시험 → 모델 이식 (`docs/04-firmware.md`)
- [ ] (팀원2) Edge Impulse 라이브러리가 ESP32 코어 3.3.12에서 빌드되는지 확인. 안 되면 2.0.17
- [ ] (팀장) 실제 보드 → 서버 → 웹 통합, 지연·오판정 측정

## 교훈
- 사용자 폴더 이름이 한글이면 ESP32 코어(AppData\Local\Arduino15) 링크 단계가 실패한다(`ld: cannot find -lxtensa`, `cannot open output file`).
  해결: `docs/04-firmware.md`의 "한글 사용자 이름 PC" 절(subst 가상 드라이브 + arduino-cli). 사용자 이름이 영문인 PC는 해당 없음.
- Mosquitto 2.x는 설정 없이 켜면 localhost만 받는다 → 반드시 `-c broker\mosquitto.conf`.
