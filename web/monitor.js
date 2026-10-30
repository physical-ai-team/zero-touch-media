// 얼굴 감지 신호 실시간 대시보드. 서버(/ws/player)의 detect·state를 받아 보여 주기만 한다. 규격: docs/03-protocol.md
// detect는 서버가 PLAYER_DETECT_HZ로 줄여 보내므로, 빈도·유실은 "브라우저가 받은 것" 기준이다.

const $ = (id) => document.getElementById(id);
const STATE_LABEL = { present: "present (재생)", absent: "absent (정지)", no_device: "no_device (장치 없음)" };
const WINDOW_MS = 30000;
const LOG_MAX = 50;

let cfg = { min_score: 0.6, device_timeout_ms: 3000 };
let ws = null;
let lastFace = null;      // 마지막 detect의 face (기록은 바뀔 때만)
let lastSeq = null;
let lastAt = 0;           // 마지막 detect 받은 시각(브라우저 ms)
let count = 0;
const samples = [];       // {t, face, score} 최근 WINDOW_MS

fetch("/api/config").then((r) => r.json()).then((c) => {
  cfg = { ...cfg, ...c };
  $("bar-th").style.left = `${cfg.min_score * 100}%`;
}).catch(() => {});

function log(text, cls = "") {
  const li = document.createElement("li");
  li.className = cls;
  li.textContent = `${new Date().toLocaleTimeString("ko-KR", { hour12: false })}.${String(Date.now() % 1000).padStart(3, "0")}  ${text}`;
  $("log").prepend(li);
  while ($("log").children.length > LOG_MAX) $("log").lastChild.remove();
}

function onDetect(m) {
  const now = Date.now();
  // 서버가 빈도를 줄여 보내면 seq 건너뜀이 정상이므로, 장치 재시작(seq 감소)만 기록한다.
  if (lastSeq !== null && m.seq <= lastSeq) {
    log(`${m.device_id}: seq ${lastSeq} → ${m.seq} (보드 재시작?)`, "warn");
  }
  lastSeq = m.seq;
  lastAt = now;
  count += 1;
  samples.push({ t: now, face: m.face, score: m.score });

  const label = m.face ? "Face Detected" : "Face Not Detected";
  if (m.face !== lastFace) {
    log(`${m.device_id}: ${label} (score ${m.score.toFixed(2)}, #${m.seq})`, m.face ? "on" : "off");
    lastFace = m.face;
  }
  setFace(m.face ? "yes" : "no", label, `${m.device_id} · 얼굴 ${m.count}개 · #${m.seq}`, `${label} · ${m.score.toFixed(2)}`);
  $("score-val").textContent = m.score.toFixed(2);
  $("bar-fill").style.width = `${Math.min(1, m.score) * 100}%`;
  $("bar-fill").className = m.score >= cfg.min_score ? "ok" : "low";
  $("infer").textContent = `${m.infer_ms ?? "?"} / ${m.dsp_ms ?? "?"} ms`;
  $("count").textContent = count;
}

function onState(m) {
  $("state").textContent = STATE_LABEL[m.state] || m.state;
  document.body.dataset.state = m.state;
  const d = m.device || {};
  $("device").textContent = d.connected ? `${d.id} (fw ${d.fw || "?"}, ${d.model || "?"})` : "연결 안 됨";
  log(`서버 판정 → ${m.state}`, "state");
}

// 0.2초마다: 신호 끊김 표시, 빈도, 타임라인
setInterval(() => {
  const now = Date.now();
  while (samples.length && now - samples[0].t > WINDOW_MS) samples.shift();
  const recent = samples.filter((s) => now - s.t <= 2000).length;
  $("hz").textContent = lastAt ? `${(recent / 2).toFixed(1)} Hz` : "-";
  if (lastAt && now - lastAt > cfg.device_timeout_ms) {
    if ($("face").dataset.face !== "stale") log("detect 신호 끊김", "warn");
    setFace("stale", "신호 없음", `마지막 수신 ${((now - lastAt) / 1000).toFixed(1)}초 전`, "보드 신호 없음");
    lastFace = null;
  }
  drawTimeline(now);
}, 200);

function drawTimeline(now) {
  const cv = $("timeline");
  const w = (cv.width = cv.clientWidth * devicePixelRatio);
  const h = (cv.height = 80 * devicePixelRatio);
  const ctx = cv.getContext("2d");
  const css = getComputedStyle(document.body);
  const x = (t) => w - ((now - t) / WINDOW_MS) * w;
  ctx.clearRect(0, 0, w, h);
  // 얼굴 있음/없음 띠
  for (let i = 0; i < samples.length; i++) {
    const s = samples[i];
    const next = samples[i + 1] ? samples[i + 1].t : Math.min(now, s.t + cfg.device_timeout_ms);
    ctx.fillStyle = css.getPropertyValue(s.face ? "--ok" : "--warn");
    ctx.globalAlpha = 0.25;
    ctx.fillRect(x(s.t), 0, Math.max(1, x(next) - x(s.t)), h);
  }
  ctx.globalAlpha = 1;
  // 기준선
  ctx.strokeStyle = css.getPropertyValue("--muted");
  ctx.setLineDash([4 * devicePixelRatio, 4 * devicePixelRatio]);
  ctx.beginPath();
  ctx.moveTo(0, h * (1 - cfg.min_score));
  ctx.lineTo(w, h * (1 - cfg.min_score));
  ctx.stroke();
  ctx.setLineDash([]);
  // 신뢰도 선
  ctx.strokeStyle = css.getPropertyValue("--fg");
  ctx.lineWidth = 2 * devicePixelRatio;
  ctx.beginPath();
  samples.forEach((s, i) => (i ? ctx.lineTo : ctx.moveTo).call(ctx, x(s.t), h * (1 - Math.min(1, s.score))));
  ctx.stroke();
}

// 큰 표시와 웹캠 배지를 함께 바꾼다. 웹캠 박스는 PiP 창으로 옮겨질 수 있어 id 대신 변수로 잡아 둔다.
function setFace(kind, label, sub, badge) {
  $("face").dataset.face = kind;
  $("face-label").textContent = label;
  $("face-sub").textContent = sub;
  cam.dataset.face = kind;
  camBadge.textContent = badge;
}

// ---------- PC 웹캠 + PiP ----------
// Chrome·Edge: Document PiP로 웹캠+감지 배지를 항상 위 창에 띄운다. 그 밖의 브라우저: 영상만 PiP.
// getUserMedia는 localhost 또는 https에서만 된다(다른 PC에서 http://IP 로 열면 웹캠 못 씀).

const cam = $("cam");
const camVideo = $("cam-video");
const camBadge = $("cam-badge");
let camStream = null;
let pipWin = null;

$("cam-on").onclick = async () => {
  if (camStream) {
    if (pipWin) pipWin.close();
    camStream.getTracks().forEach((t) => t.stop());
    camStream = null;
    cam.hidden = true;
    $("cam-on").textContent = "웹캠 켜기";
    $("cam-pip").disabled = true;
    return;
  }
  if (!navigator.mediaDevices) {
    log("웹캠은 localhost(또는 https)에서만 열 수 있습니다", "warn");
    return;
  }
  try {
    camStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
  } catch (e) {
    log(`웹캠을 열지 못했습니다: ${e.name}`, "warn");
    return;
  }
  camVideo.srcObject = camStream;
  cam.hidden = false;
  $("cam-on").textContent = "웹캠 끄기";
  $("cam-pip").disabled = false;
};

$("cam-pip").onclick = async () => {
  if (pipWin) { pipWin.close(); return; }
  if (!("documentPictureInPicture" in window)) {
    await camVideo.requestPictureInPicture().catch((e) => log(`PiP 실패: ${e.name}`, "warn"));
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
  camVideo.play();
  $("cam-pip").textContent = "PiP 닫기";
  pipWin.addEventListener("pagehide", () => {
    $("cam-card").append(cam);
    camVideo.play();
    pipWin = null;
    $("cam-pip").textContent = "PiP 창으로";
  });
};

// ---------- 서버 WebSocket ----------

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/player`);
  ws.onopen = () => setConn(true);
  ws.onclose = () => { setConn(false); setTimeout(connect, 1000); };
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type === "detect") onDetect(m);
    else if (m.type === "state") onState(m);
    else if (m.type === "ping") ws.send(JSON.stringify({ type: "pong", t0: m.t0, t1: Date.now() }));
  };
}

function setConn(ok) {
  $("conn").textContent = ok ? "서버 연결됨" : "서버 연결 끊김";
  $("conn").className = "badge " + (ok ? "on" : "off");
}

connect();
