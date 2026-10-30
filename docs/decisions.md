# 설계 결정

| ID | 결정 | 이유 |
|---|---|---|
| D-001 | 얼굴 인식은 ESP32 안(Edge Impulse FOMO) | 수업 요구사항 |
| D-002 | ESP32 → 서버는 MQTT(Mosquitto), 서버 → 브라우저는 WebSocket | 강사 권장. LWT로 장치 끊김을 브로커가 알려 줌. WebSocket 직결·ESP32 웹서버 방식보다 IoT 표준에 맞음 |
| D-003 | 재생/정지 판단은 서버 presence.py 한 곳 | 펌웨어 재업로드 없이 값 조정, 깜빡임 방지 규칙을 한 곳에서 시험 |
| D-004 | 서버 MQTT는 paho-mqtt(스레드) | aiomqtt는 Windows 기본 이벤트 루프(Proactor)에서 동작하지 않음 |
| D-005 | Redis·Docker 없음 | 서비스 1개, 장치 1대. 브로커가 메시지 통로 역할 |
| D-006 | 판정 기본값 300/1500ms, 0.6, 3000ms | 짧은 시선 이탈로 멈추지 않게 OFF를 길게. 측정 후 조정 |
| D-007 | 펌웨어 keepalive 5초 | PubSubClient 기본 15초면 LWT가 20초 넘게 늦음 |
