// 보드(ESP32) 카메라 영상 + PiP 창. 플레이어(index.html)·모니터(monitor.html) 공용. 페이지에 #cam-card 마크업이 있어야 한다.
// 영상: 서버 /ws/player의 바이너리 메시지(JPEG, docs/03-protocol.md) → 페이지 스크립트가 camPip.setFrame(blob)으로 넘긴다.
// PiP: Chrome·Edge의 Document PiP로 항상 위 창(마우스로 옮기기·크기 조절 가능). 그 밖의 브라우저는 페이지 안에서만 보인다.
// 배지는 보드의 감지 결과다. 페이지 스크립트가 camPip.setFace()로 알려 준다.

const camPip = (() => {
  const FRAME_STALE_MS = 3000;  // 이 시간 동안 영상이 없으면 '영상 없음' 표시
  const $ = (id) => document.getElementById(id);
  // 영상 박스는 PiP 창으로 옮겨질 수 있어 id 대신 변수로 잡아 둔다.
  const card = $("cam-card");
  const cam = $("cam");
  const img = $("cam-img");
  const empty = $("cam-empty");
  const badge = $("cam-badge");
  const msg = $("cam-msg");
  const btnPip = $("cam-pip");
  let pipWin = null;
  let url = null;
  let lastFrameAt = 0;

  setInterval(() => {
    const on = lastFrameAt && Date.now() - lastFrameAt <= FRAME_STALE_MS;
    cam.dataset.video = on ? "on" : "off";
    if (!on) empty.textContent = lastFrameAt ? "보드 영상 끊김" : "보드 영상 기다리는 중";
  }, 500);

  btnPip.onclick = async () => {
    msg.textContent = "";
    if (pipWin) { pipWin.close(); return; }
    if (!("documentPictureInPicture" in window)) {
      msg.textContent = "PiP 창은 Chrome·Edge에서만 됩니다";
      return;
    }
    pipWin = await documentPictureInPicture.requestWindow({ width: 360, height: 290 });
    // PiP 창은 빈 문서라 스타일을 절대 주소로 다시 건다.
    document.querySelectorAll('link[rel="stylesheet"]').forEach((l) => {
      const link = pipWin.document.createElement("link");
      link.rel = "stylesheet";
      link.href = l.href;
      pipWin.document.head.append(link);
    });
    pipWin.document.title = "ZTMC 보드 카메라";
    pipWin.document.body.className = "pip";
    pipWin.document.body.append(cam);
    btnPip.textContent = "PiP 닫기";
    pipWin.addEventListener("pagehide", () => {
      card.append(cam);
      pipWin = null;
      btnPip.textContent = "PiP 창으로";
    });
  };

  return {
    // blob: JPEG 한 장
    setFrame(blob) {
      const prev = url;
      url = URL.createObjectURL(blob);
      img.src = url;
      if (prev) URL.revokeObjectURL(prev);
      lastFrameAt = Date.now();
    },
    // kind: yes | no | stale | none
    setFace(kind, text) {
      cam.dataset.face = kind;
      badge.textContent = text;
    },
  };
})();
