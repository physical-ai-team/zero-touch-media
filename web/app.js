// 서버(/ws/player)의 state 메시지대로 유튜브를 재생/정지한다. 규격: docs/03-protocol.md
// 재생·정지 판단은 서버가 한다. 이 페이지는 따르기만 한다.

const $ = (id) => document.getElementById(id);
const STATE_LABEL = { present: "얼굴 인식됨 → 재생", absent: "얼굴 없음 → 정지", no_device: "장치 없음 → 정지" };

let player = null;
let playerReady = false;
let started = false;   // 브라우저 자동재생 정책: 사용자가 한 번 눌러야 재생 가능
let serverState = "no_device";
let ws = null;

// ---------- 유튜브 ----------

window.onYouTubeIframeAPIReady = async () => {
  const cfg = await fetch("/api/config").then((r) => r.json()).catch(() => ({}));
  // 마지막으로 불러온 영상(이 브라우저에만 저장) → 없으면 .env의 DEFAULT_VIDEO_ID
  let saved = null;
  try { saved = localStorage.getItem("ztmc.video"); } catch {}
  const v = (saved && parseVideo(saved)) || { videoId: cfg.default_video_id || "jNQXAC9IVRw" };
  $("video-id").value = saved && parseVideo(saved) ? saved : v.videoId;
  player = new YT.Player("player", {
    videoId: v.videoId,
    playerVars: { playsinline: 1, rel: 0, start: v.startSeconds || 0 },
    events: {
      onReady: () => { playerReady = true; apply(); },
      onStateChange: onPlayerStateChange,
    },
  });
};

function onPlayerStateChange(e) {
  const names = { [YT.PlayerState.PLAYING]: "playing", [YT.PlayerState.PAUSED]: "paused", [YT.PlayerState.ENDED]: "ended" };
  const ev = names[e.data];
  $("player-state").textContent = ev || String(e.data);
  if (ev) send({ type: "player", event: ev, ts: Date.now() });
}

function apply() {
  if (!playerReady || !started || $("manual").checked) return;
  if (serverState === "present") player.playVideo();
  else player.pauseVideo();
}

$("start").onclick = () => {
  started = true;
  $("start").hidden = true;
  if (playerReady) { player.playVideo(); player.pauseVideo(); }  // 사용자 동작으로 재생 권한 얻기
  apply();
};

// 유튜브 주소(watch?v=, youtu.be/, shorts/, embed/, live/) 또는 11자 영상 ID → {videoId, startSeconds}
function parseVideo(text) {
  const s = text.trim();
  if (/^[\w-]{11}$/.test(s)) return { videoId: s };
  let u;
  try { u = new URL(s.includes("://") ? s : `https://${s}`); } catch { return null; }
  const path = u.pathname.match(/^\/(?:shorts|embed|live|v)\/([\w-]{11})/);
  const id = u.hostname.endsWith("youtu.be") ? u.pathname.slice(1, 12) : (u.searchParams.get("v") || (path && path[1]));
  if (!id || !/^[\w-]{11}$/.test(id)) return null;
  // t=90, t=90s, t=1m30s, t=1h2m3s
  const t = (u.searchParams.get("t") || u.searchParams.get("start") || "").match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/);
  const start = t ? (+t[1] || 0) * 3600 + (+t[2] || 0) * 60 + (+t[3] || 0) : 0;
  return start ? { videoId: id, startSeconds: start } : { videoId: id };
}

function loadVideo() {
  const v = parseVideo($("video-id").value);
  if (!v) { $("video-msg").textContent = "유튜브 주소나 영상 ID를 알아볼 수 없습니다"; return; }
  if (!playerReady) return;
  player.cueVideoById(v);
  $("video-msg").textContent = `불러옴: ${v.videoId}${v.startSeconds ? ` (${v.startSeconds}초부터)` : ""}`;
  try { localStorage.setItem("ztmc.video", $("video-id").value.trim()); } catch {}
  apply();
}

$("load").onclick = loadVideo;
$("video-id").onkeydown = (e) => { if (e.key === "Enter") loadVideo(); };

$("manual").onchange = () => {
  send({ type: "player", event: $("manual").checked ? "manual_on" : "manual_off", ts: Date.now() });
  apply();
};

// ---------- 서버 WebSocket ----------

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/player`);
  ws.onopen = () => setConn(true);
  ws.onclose = () => { setConn(false); setTimeout(connect, 1000); };
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type === "state") {
      serverState = m.state;
      $("state").textContent = STATE_LABEL[m.state] || m.state;
      document.body.dataset.state = m.state;
      const d = m.device || {};
      $("device").textContent = d.connected ? `${d.id} (fw ${d.fw || "?"}, ${d.model || "?"})` : "연결 안 됨";
      apply();
    } else if (m.type === "detect") {
      $("detect").textContent = `${m.face ? "얼굴" : "없음"} · 신뢰도 ${m.score.toFixed(2)} · 추론 ${m.infer_ms ?? "?"}ms · #${m.seq}`;
    } else if (m.type === "ping") {
      send({ type: "pong", t0: m.t0, t1: Date.now() });
    }
  };
}

function setConn(ok) {
  $("conn").textContent = ok ? "서버 연결됨" : "서버 연결 끊김";
  $("conn").className = "badge " + (ok ? "on" : "off");
  if (!ok) { serverState = "no_device"; apply(); }  // 서버가 끊기면 안전하게 정지
}

connect();
