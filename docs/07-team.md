# 7. 팀 규칙

| 담당 | 폴더 | 할 일 |
|---|---|---|
| 팀장 박민성 | `broker/`, `server/`, `tools/`, `docs/`, 루트 | 브로커 설정, 서버, 통합, 측정, 문서, PR 병합 |
| 팀원1 | `model/`, `web/` | Edge Impulse 학습·최적화, 유튜브 페이지 |
| 팀원2 | `firmware/` | 보드·카메라, 모델 이식, MQTT 발행 |

- 자기 폴더만 고친다. 다른 폴더를 고쳐야 하면 담당자에게 말하거나 이슈를 연다.
- 브랜치: `feat/<담당>-<내용>` (예: `feat/firmware-ei-model`). `main` 직접 push 금지, PR로 병합.
- 규격 변경은 `docs/03-protocol.md`와 `protocol.py`를 같이 고치는 PR로, 팀장 확인.
- 비밀값(Wi-Fi 비번, Edge Impulse API 키)은 커밋하지 않는다.
