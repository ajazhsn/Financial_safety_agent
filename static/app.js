// Financial Safety Agent — one step at a time (no framework)

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const state = {
  lang: null, ui: {}, languages: [], mode: "text", image: null, audio: null, recorder: null,
  busy: false, last: null, history: [], screen: null,
};
try { state.lang = localStorage.getItem("fsa-lang"); } catch (e) { /* storage blocked */ }

const t = (key) => state.ui[key] || key;

// ---------------------------------------------------------------- screens
function show(name, { push = true } = {}) {
  if (push && state.screen && state.screen !== name) state.history.push(state.screen);
  state.screen = name;
  $$(".screen").forEach((s) => {
    const on = s.dataset.screen === name;
    s.hidden = !on;
    if (on) { s.classList.remove("enter"); void s.offsetWidth; s.classList.add("enter"); }
  });
  hideError();
  window.scrollTo({ top: 0 });
  const h = document.querySelector(`[data-screen="${name}"] .q`);
  if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); }
}
function back() {
  const prev = state.history.pop();
  if (prev) show(prev, { push: false });
}
$$("[data-back]").forEach((b) => b.addEventListener("click", back));

function stepLabels() {
  $$(".step").forEach((el) => {
    const n = el.dataset.step;
    const label = t("step_of");
    el.textContent = label.includes("{n}") ? label.replace("{n}", n) : `${n} / 3`;
    el.style.setProperty("--pct", `${Math.round((n / 3) * 100)}%`);
  });
}

// ---------------------------------------------------------------- language
async function loadLanguage(code) {
  state.lang = code;
  try { localStorage.setItem("fsa-lang", code); } catch (e) {}
  try { state.ui = await (await fetch(`/api/ui/${code}`)).json(); }
  catch (e) { state.ui = await (await fetch("/api/ui/en")).json(); }
  document.documentElement.lang = code;
  document.documentElement.dir = code === "ur" ? "rtl" : "ltr";
  $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $$("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); el.setAttribute("aria-label", t(el.dataset.i18nPh)); });
  $$(".lang-btn").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.code === code)));
  const cur = state.languages.find((l) => l.code === code);
  $("#lang-current").textContent = cur ? cur.name : code;
  $("#lang-switch").setAttribute("aria-label", t("change_language"));
  document.title = t("title");
  stepLabels();
  setInputTitle();
  updateMicStatus();
  setListenLabel();
}

async function chooseLanguage(code) {
  await loadLanguage(code);
  // an answer already on screen must follow the page language
  if (state.last && state.last.lang !== code) { relocalize(code); return; }
  show(state.last ? "result" : "how", { push: false });
}

$("#lang-switch").addEventListener("click", () => { if (!state.busy) show("lang"); });

// light by default; dark only if the user turns it on (remembered on this device)
$("#theme-switch").addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme !== "dark";
  if (dark) document.documentElement.dataset.theme = "dark"; else delete document.documentElement.dataset.theme;
  try { localStorage.setItem("fsa-theme", dark ? "dark" : "light"); } catch (e) {}
});

// ---------------------------------------------------------------- step 1: how
function setMode(mode) {
  state.mode = mode;
  $$(".input").forEach((el) => { el.hidden = el.dataset.input !== mode; });
  setInputTitle();
}
$$(".tile").forEach((b) => b.addEventListener("click", () => {
  setMode(b.dataset.mode);
  show("input");
  if (state.mode === "text") $("#text").focus();
}));
function setInputTitle() {
  $("#input-title").textContent = t({ text: "in_text_title", image: "in_image_title", voice: "in_voice_title" }[state.mode]);
}

// ---------------------------------------------------------------- step 2: input
function setImage(file) {
  if (!file || !file.type.startsWith("image/")) return;
  state.image = file;
  const img = $("#preview"); img.src = URL.createObjectURL(file); img.hidden = false;
  $("#drop-text").dataset.i18n = "change_image"; $("#drop-text").textContent = t("change_image");
}
$("#image").addEventListener("change", (e) => setImage(e.target.files[0]));
const drop = $("#drop");
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); setImage(e.dataTransfer.files[0]); });
document.addEventListener("paste", (e) => {  // paste a screenshot straight from the clipboard
  const file = [...(e.clipboardData?.files || [])].find((f) => f.type.startsWith("image/"));
  if (file && state.screen === "input") { setMode("image"); setImage(file); }
});

function updateMicStatus() {
  const mic = $("#mic");
  const rec = mic.getAttribute("aria-pressed") === "true";
  $("#mic-status").textContent = rec ? t("recording") : (state.audio ? t("recorded") : t("record"));
  mic.setAttribute("aria-label", rec ? t("stop") : t("record"));
}
$("#mic").addEventListener("click", async () => {
  const mic = $("#mic");
  if (state.recorder && state.recorder.state === "recording") { state.recorder.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((tr) => tr.stop());
      const type = rec.mimeType || "audio/webm";
      const ext = type.includes("ogg") ? "ogg" : type.includes("mp4") ? "m4a" : "webm";
      state.audio = new File([new Blob(chunks, { type })], `voice.${ext}`, { type });
      mic.setAttribute("aria-pressed", "false"); updateMicStatus();
    };
    state.recorder = rec; rec.start();
    mic.setAttribute("aria-pressed", "true"); updateMicStatus();
  } catch (e) { showError(t("mic_blocked")); }
});
$("#audio-file").addEventListener("change", (e) => { state.audio = e.target.files[0] || null; updateMicStatus(); });

function showError(msg) { const el = $("#form-error"); el.textContent = msg; el.hidden = false; }
function hideError() { $("#form-error").hidden = true; }

$("#to-acted").addEventListener("click", () => {
  if (state.mode === "text" && !$("#text").value.trim()) return showError(t("need_text"));
  if (state.mode === "image" && !state.image) return showError(t("need_image"));
  if (state.mode === "voice" && !state.audio) return showError(t("need_voice"));
  show("acted");
});

// ---------------------------------------------------------------- step 3: acted? -> check
$$("[data-acted]").forEach((b) => b.addEventListener("click", () => runCheck(b.dataset.acted === "true")));

function setStage(stage) {
  const order = ["reading", "investigating", "writing", "voice"];
  const i = order.indexOf(stage);
  $$("#progress li").forEach((li, j) => { li.classList.toggle("done", j < i); li.classList.toggle("active", j === i); });
}

// Read a streamed response: one JSON event per line ({stage}, {error}, {result}).
async function readEvents(resp, onResult, onError, onVoice = applyVoice, onPart = applyVoicePart) {
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
      if (!line) continue;
      const ev = JSON.parse(line);
      if (ev.stage) setStage(ev.stage);
      if (ev.error) onError(ev.error);
      if (ev.result) onResult(ev.result);
      if (ev.voice_part && onPart) onPart(ev.voice_part);
      if (ev.voice && onVoice) onVoice(ev.voice);
    }
  }
}

async function runCheck(acted) {
  if (state.busy) return;
  const fd = new FormData();
  fd.append("mode", state.mode); fd.append("lang", state.lang);
  fd.append("text", $("#text").value.trim()); fd.append("acted", acted ? "true" : "false");
  if (state.mode === "image") fd.append("image", state.image);
  if (state.mode === "voice") fd.append("audio", state.audio);

  state.busy = true;
  setStage("reading"); show("wait");
  const fail = (key) => { state.history = ["how"]; show("input", { push: false }); showError(t(key)); };
  try {
    const resp = await fetch("/api/check", { method: "POST", body: fd });
    await readEvents(resp, render, fail);
  } catch (err) { fail("failed"); }
  finally { state.busy = false; }
}

// Translate the answer on screen into the newly chosen language (no new agent run).
async function relocalize(code) {
  state.busy = true;
  setStage("writing"); show("wait", { push: false });
  try {
    const resp = await fetch("/api/localize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lang: code, en: state.last.en }),
    });
    await readEvents(resp, (r) => render({ ...state.last, ...r }), () => show("result", { push: false }));
  } catch (err) { show("result", { push: false }); }
  finally { state.busy = false; }
}

// ---------------------------------------------------------------- result
function el(tag, text) { const e = document.createElement(tag); e.textContent = text; return e; }

function render(r) {
  state.last = r;
  state.voice = { parts: [], total: 0, idx: 0, streaming: false, waiting: false };
  const v = $("#verdict");
  v.className = `verdict ${r.kind}`;
  $("#stamp-word").textContent = r.stamp;
  $("#headline").textContent = r.headline;
  $("#explanation").textContent = r.explanation;
  $("#steps").replaceChildren(...r.steps.map((s) => el("li", s)));
  $("#rules").replaceChildren(...r.rules.map((s) => el("li", s)));
  $("#rules-block").hidden = r.rules.length === 0;

  // privacy: what was hidden before the message went to the AI (deduplicated)
  const hidden = r.hidden || [];
  const labels = [...new Set(hidden.map((h) => (h.type === "card" || h.type === "account")
    ? `${t("p_" + h.type)} ${h.label}` : t("p_" + h.type)))];
  $("#privacy-items").textContent = labels.join(" · ");
  $("#privacy").hidden = labels.length === 0;

  const audioEl = $("#audio");
  audioEl.pause(); $("#play").classList.remove("playing"); $("#bar-fill").style.width = "0";
  if (r.audio_url) {
    audioEl.src = r.audio_url; $("#play").hidden = false; $("#play").disabled = false; $("#no-voice").hidden = true;
  } else if (r.voice_pending) {  // text is shown now; the voice arrives a few seconds later
    audioEl.removeAttribute("src"); $("#play").hidden = false; $("#play").disabled = true; $("#no-voice").hidden = true;
  } else { $("#play").hidden = true; $("#no-voice").hidden = false; }
  $("#play").classList.toggle("loading", !r.audio_url && !!r.voice_pending);
  setListenLabel();

  const names = { fast: "t_fast", escalate: "t_escalate", triage: "t_triage", investigate: "t_investigate", reinvestigate: "t_reinvestigate", incident: "t_incident" };
  $("#timeline").replaceChildren(...r.agent.steps.map((s) => {
    const item = document.createElement("li");
    const title = s.kind === "verify" ? (s.ok ? t("t_verify_ok") : t("t_verify_no")) : t(names[s.kind] || s.kind);
    if (s.kind === "verify" && !s.ok) item.className = "no";
    item.appendChild(el("b", title));
    const extra = [s.detail, s.note].filter(Boolean).join(" — ");
    if (extra) item.appendChild(el("span", extra));
    return item;
  }));
  $("#tools").replaceChildren(...r.agent.tools.map((x) => el("code", `${x.tool} ${x.args}`)));
  $("#evidence").replaceChildren(...r.agent.evidence.map((ev) => { const i = el("li", ev.claim + " "); i.appendChild(el("small", `(${ev.source})`)); return i; }));
  const tm = r.timing;
  $("#timing").textContent = timingText(tm);
  $("#read").textContent = r.read_text;
  const en = $("#english");
  en.replaceChildren(el("p", `${r.english.type} (risk: ${r.english.risk})`), el("p", r.english.explanation));
  const ol = document.createElement("ol"); r.english.steps.forEach((s) => ol.appendChild(el("li", s))); en.appendChild(ol);

  state.history = ["how"];
  show("result", { push: false });
  v.classList.remove("reveal"); void v.offsetWidth; v.classList.add("reveal");
  if (r.audio_url) audioEl.play().then(() => { $("#play").classList.add("playing"); setListenLabel(); }).catch(() => {});
}

// voice player: one big button
const audio = $("#audio");
function setListenLabel() {
  const p = $("#play");
  $("#listen-label").textContent = p.classList.contains("loading") ? t("voice_coming")
    : p.classList.contains("playing") ? t("pause") : t("listen");
}

function timingText(tm) {
  const parts = [];
  if (tm.agent !== undefined) parts.push(`agent ${tm.agent}s (${tm.calls} LLM calls)`);
  if (tm.translate !== undefined) parts.push(`translate ${tm.translate}s`);
  if (tm.voice !== undefined) parts.push(`voice ${tm.voice}s`);
  return `${t("time_taken")}: ${parts.join(", ")}.` + (tm.model ? ` Model: ${tm.model}${tm.config ? ", mode: " + tm.config : ""}` : "");
}

// The voice arrives sentence by sentence: play each one as soon as it is ready, in order.
// When the whole answer has arrived, the Listen button replays the full recording.
function sameAnswer(v) { return state.last && (!v.lang || v.lang === state.last.lang); }

function playPart(i) {
  const vs = state.voice, p = $("#play");
  vs.idx = i; vs.waiting = false;
  audio.src = vs.parts[i];
  p.classList.remove("loading"); p.disabled = false; p.hidden = false; $("#no-voice").hidden = true;
  audio.play().then(() => { p.classList.add("playing"); setListenLabel(); }).catch(() => { setListenLabel(); });
}

function applyVoicePart(v) {
  if (!sameAnswer(v)) return;  // an answer the user already left
  const vs = state.voice;
  vs.parts[v.index] = v.url; vs.total = v.total;
  if (v.index === 0 && !vs.streaming) { vs.streaming = true; playPart(0); }
  else if (vs.waiting && v.index === vs.idx) playPart(v.index);
}

function applyVoice(v) {
  if (!sameAnswer(v)) return;
  const vs = state.voice, p = $("#play");
  state.last.audio_url = v.audio_url; state.last.voice_pending = false;
  state.last.timing = { ...(state.last.timing || {}), voice: v.seconds };
  $("#timing").textContent = timingText(state.last.timing);
  p.classList.remove("loading");
  if (!v.audio_url && !vs.streaming) { p.hidden = true; $("#no-voice").hidden = false; setListenLabel(); return; }
  if (!vs.streaming && v.audio_url) {  // no sentence was streamed (e.g. old server): play the whole file
    audio.src = v.audio_url; p.disabled = false; p.hidden = false; $("#no-voice").hidden = true;
    audio.play().then(() => { p.classList.add("playing"); setListenLabel(); }).catch(() => {});
  }
  setListenLabel();
}

$("#play").addEventListener("click", () => {
  if (state.voice && state.voice.waiting) return;
  if (!audio.getAttribute("src") && state.last && state.last.audio_url) audio.src = state.last.audio_url;
  if (audio.paused) { audio.play(); $("#play").classList.add("playing"); }
  else { audio.pause(); $("#play").classList.remove("playing"); }
  setListenLabel();
});
audio.addEventListener("ended", () => {
  const vs = state.voice;
  if (vs && vs.streaming) {
    const next = vs.idx + 1;
    if (next < vs.total && vs.parts[next]) return playPart(next);
    if (next < vs.total) {  // the next sentence is still being recorded
      vs.idx = next; vs.waiting = true;
      $("#play").classList.remove("playing"); $("#play").classList.add("loading"); setListenLabel();
      return;
    }
    vs.streaming = false;  // finished: the button now replays the whole answer
    if (state.last && state.last.audio_url) audio.src = state.last.audio_url;
  }
  $("#play").classList.remove("playing"); setListenLabel();
});
audio.addEventListener("timeupdate", () => {
  if (!audio.duration) return;
  const vs = state.voice, frac = audio.currentTime / audio.duration;
  const done = vs && vs.streaming && vs.total ? (vs.idx + frac) / vs.total : frac;
  $("#bar-fill").style.width = `${done * 100}%`;
});

$("#again").addEventListener("click", () => {
  audio.pause(); $("#play").classList.remove("playing");
  $("#text").value = ""; state.image = null; state.audio = null; state.last = null;
  $("#preview").hidden = true; $("#drop-text").dataset.i18n = "drop_image"; $("#drop-text").textContent = t("drop_image");
  updateMicStatus();
  state.history = []; show("how", { push: false });
});

// ---------------------------------------------------------------- start
async function init() {
  const cfg = await (await fetch("/api/config")).json();
  state.languages = cfg.languages;
  $("#languages").replaceChildren(...cfg.languages.map((l) => {
    const b = el("button", l.name); b.type = "button"; b.className = "lang-btn"; b.dataset.code = l.code; b.lang = l.code;
    b.addEventListener("click", () => chooseLanguage(l.code));
    return b;
  }));
  $("#examples").replaceChildren(...cfg.examples.map((text) => {
    const b = el("button", text); b.type = "button"; b.className = "example"; b.title = text;
    b.addEventListener("click", () => { setMode("text"); $("#text").value = text; show("input"); });
    return b;
  }));
  if (state.lang && cfg.languages.some((l) => l.code === state.lang)) {
    await loadLanguage(state.lang); show("how", { push: false });
  } else {
    await loadLanguage("hi"); show("lang", { push: false });
  }
}
init();
