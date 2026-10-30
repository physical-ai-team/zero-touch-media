# Zero-Touch Media Control

화면을 보는 순간 재생되고, 시선을 떼는 순간 멈추는 유튜브. ESP32-S3 카메라가 보드 안에서 얼굴을 인식하고(Edge Impulse), MQTT로 PC에 알리면 브라우저 유튜브가 자동 재생/정지된다.

```
ESP32-S3 ──MQTT──▶ Mosquitto ──▶ 서버(판정 안정화) ──WebSocket──▶ 유튜브 페이지
```

## 처음 실행 (Windows)
1. 설치: [Miniforge](https://github.com/conda-forge/miniforge), Mosquitto(`winget install EclipseFoundation.Mosquitto`)
2. 환경: `conda env create -f environment.yml` → `conda activate ztmc` → `copy .env.example .env`
3. 터미널 3개:
   ```powershell
   & "C:\Program Files\mosquitto\mosquitto.exe" -c broker\mosquitto.conf -v
   cd server; python -m ztmc_server
   python tools\fake_esp32.py
   ```
4. 브라우저 <http://localhost:8000> → "시작" → 가짜 ESP32 창에서 `f`(얼굴) / `n`(없음) / `x`(끊김)
5. 실제 보드: [docs/04-firmware.md](docs/04-firmware.md). ESP32가 접속하려면 PC 방화벽에서 TCP 1883 허용.

문서: [CLAUDE.md](CLAUDE.md)(규칙·문서 지도), [docs/](docs/), [HANDOFF.md](HANDOFF.md)(현재 상태·남은 일)
