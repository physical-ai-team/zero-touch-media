// PC 웹캠 + PiP 창. 플레이어(index.html)·모니터(monitor.html) 공용. 페이지에 #cam-card 마크업이 있어야 한다.
// Chrome·Edge: Document PiP로 웹캠+감지 배지를 항상 위 창에 띄운다(창은 마우스로 옮기고 크기 조절 가능).
// 그 밖의 브라우저: 영상만 PiP. getUserMedia는 localhost 또는 https에서만 된다.
// 배지는 보드의 감지 결과다. 페이지 스크립트가 camPip.setFace()로 알려 준다.

const camPip = (() => {
  const $ = (id) => document.getElementById(id);
  // 웹캠 박스는 PiP 창으로 옮겨질 수 있어 id 대신 변수로 잡아 둔다.
  const card = $("cam-card");
  const cam = $("cam");
  const video = $("cam-video");
  const badge = $("cam-badge");
  const msg = $("cam-msg");
  const btnOn = $("cam-on");
  const btnPip = $("cam-pip");
  let stream = null;
  let pipWin = null;

  btnOn.onclick = async () => {
    msg.textContent = "";
    if (stream) {
      if (pipWin) pipWin.close();
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
      cam.hidden = true;
      btnOn.textContent = "웹캠 켜기";
      btnPip.disabled = true;
      return;
    }
    if (!navigator.mediaDevices) {
      msg.textContent = "웹캠은 localhost(또는 https)에서만 열 수 있습니다";
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
    } catch (e) {
      msg.textContent = `웹캠을 열지 못했습니다: ${e.name}`;
      return;
    }
    video.srcObject = stream;
    cam.hidden = false;
    btnOn.textContent = "웹캠 끄기";
    btnPip.disabled = false;
  };

  btnPip.onclick = async () => {
    msg.textContent = "";
    if (pipWin) { pipWin.close(); return; }
    if (!("documentPictureInPicture" in window)) {
      await video.requestPictureInPicture().catch((e) => { msg.textContent = `PiP 실패: ${e.name}`; });
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
    pipWin.document.title = "ZTMC 웹캠";
    pipWin.document.body.className = "pip";
    pipWin.document.body.append(cam);
    video.play();
    btnPip.textContent = "PiP 닫기";
    pipWin.addEventListener("pagehide", () => {
      card.append(cam);
      video.play();
      pipWin = null;
      btnPip.textContent = "PiP 창으로";
    });
  };

  return {
    // kind: yes | no | stale | none
    setFace(kind, text) {
      cam.dataset.face = kind;
      badge.textContent = text;
    },
  };
})();
