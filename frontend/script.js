/* ── Constants ─────────────────────────────────────────────────────────── */
const MAX_SESSIONS = 10;
const LS_KEY       = "rt_agent_sessions";   // localStorage key

/* ── State ─────────────────────────────────────────────────────────────── */
let API_BASE       = "http://localhost:8000";
let connected      = false;
let currentSession = null;          // active session_id (UUID string)
let chatSessions   = {};            // session_id → { title, messages[], lastUpdated }
let lastBotMsgEl   = null;
let isThinking     = false;

/* ── DOM refs ──────────────────────────────────────────────────────────── */
const chatArea     = document.getElementById("chatArea");
const msgInput     = document.getElementById("msgInput");
const sendBtn      = document.getElementById("sendBtn");
const clearBtn     = document.getElementById("clearBtn");
const downloadBtn  = document.getElementById("downloadBtn");
const newChatBtn   = document.getElementById("newChatBtn");
const connectBtn   = document.getElementById("connectBtn");
const hostInput    = document.getElementById("hostInput");
const portInput    = document.getElementById("portInput");
const connStatus   = document.getElementById("connStatus");
const thinkingEl   = document.getElementById("thinkingIndicator");
const thinkingText = document.getElementById("thinkingText");
const toolBadge    = document.getElementById("toolBadge");
const historyList  = document.getElementById("historyList");

/* ── marked config ─────────────────────────────────────────────────────── */
marked.setOptions({
  breaks: true,
  gfm: true,
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang))
      return hljs.highlight(code, { language: lang }).value;
    return hljs.highlightAuto(code).value;
  }
});

/* ══════════════════════════════════════════════════════════════════════════
   SESSION PERSISTENCE  (localStorage ↔ server memory)
══════════════════════════════════════════════════════════════════════════ */

function saveSessions() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(chatSessions));
  } catch (_) {}
}

function loadSessions() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) chatSessions = JSON.parse(raw);
  } catch (_) {
    chatSessions = {};
  }
}

/**
 * Enforce the MAX_SESSIONS cap.
 * When a new session would exceed the limit, drop the oldest one.
 */
function enforceSessionCap() {
  const ids = Object.keys(chatSessions);
  if (ids.length <= MAX_SESSIONS) return;

  // Sort by lastUpdated ascending → oldest first
  ids.sort((a, b) => {
    const ta = chatSessions[a].lastUpdated || "";
    const tb = chatSessions[b].lastUpdated || "";
    return ta.localeCompare(tb);
  });

  // Remove oldest until we're at the cap
  while (Object.keys(chatSessions).length > MAX_SESSIONS) {
    const oldest = ids.shift();
    if (oldest && oldest !== currentSession) {
      delete chatSessions[oldest];
      // Fire-and-forget: also clear server-side memory for that session
      fetch(`${API_BASE}/sessions/${oldest}`, { method: "DELETE" }).catch(() => {});
    }
  }
}

/**
 * After a page reload, re-sync the server's in-memory store from localStorage.
 * We POST a dummy "restore" to /chat for each session — actually we just
 * call GET /sessions to compare, and warn if server restarted (sessions lost).
 */
async function syncSessionsWithServer() {
  if (!connected) return;
  try {
    const res  = await fetch(`${API_BASE}/sessions`);
    const data = await res.json();
    const serverIds = new Set((data.sessions || []).map(s => s.session_id));

    // Sessions in localStorage but not on server means server restarted.
    // The history is still in localStorage (UI), but the LLM won't have
    // memory context. Mark those sessions visually as "(memory reset)".
    Object.keys(chatSessions).forEach(id => {
      if (!serverIds.has(id) && chatSessions[id].messages.length > 0) {
        chatSessions[id].serverMemoryLost = true;
      }
    });
    saveSessions();
    renderHistory();
  } catch (_) {}
}

/* ══════════════════════════════════════════════════════════════════════════
   UI HELPERS
══════════════════════════════════════════════════════════════════════════ */

function buildBase() {
  const host = hostInput.value.trim() || "localhost";
  const port = portInput.value.trim() || "8000";
  API_BASE = `http://${host}:${port}`;
}

function setStatus(ok, msg) {
  connected = ok;
  connStatus.textContent = ok ? `🟢 ${msg}` : `🔴 ${msg}`;
  connStatus.className   = "conn-status " + (ok ? "ok" : "err");
}

function showThinking(text = "Thinking…") {
  isThinking = true;
  thinkingEl.classList.remove("hidden");
  thinkingText.textContent = text;
  scrollBottom();
}

function hideThinking() {
  isThinking = false;
  thinkingEl.classList.add("hidden");
  toolBadge.classList.add("hidden");
}

function showToolBadge(tools) {
  if (!tools?.length) return;
  const labels = { pdf: "📄 PDF Report", excel: "📊 Excel Sales" };
  toolBadge.textContent = "🔧 Using: " + tools.map(t => labels[t] || t).join(" + ");
  toolBadge.classList.remove("hidden");
}

function scrollBottom() {
  setTimeout(() => chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: "smooth" }), 50);
}

function badgeClass(intent) {
  const map = { GENERAL: "badge-general", REPORT: "badge-report", SALES: "badge-sales", BOTH: "badge-both" };
  return map[intent] || "badge-general";
}

function intentLabel(intent) {
  const map = { GENERAL: "💬 General", REPORT: "📄 Report", SALES: "📊 Sales", BOTH: "🔗 Both" };
  return map[intent] || intent;
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => showToast("Copied!"));
}

function showToast(msg) {
  const t = document.createElement("div");
  t.textContent = msg;
  Object.assign(t.style, {
    position: "fixed", bottom: "80px", right: "20px",
    background: "#333", color: "#fff", padding: "8px 16px",
    borderRadius: "8px", fontSize: "0.8rem", zIndex: 9999,
  });
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 1800);
}

function escapeHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function autoResize() {
  msgInput.style.height = "auto";
  msgInput.style.height = Math.min(msgInput.scrollHeight, 160) + "px";
}

/* ══════════════════════════════════════════════════════════════════════════
   EMPTY STATE / SUGGESTION CHIPS
══════════════════════════════════════════════════════════════════════════ */

const SUGGESTIONS = [
  "What products do you manufacture?",
  "Show 2024 sales summary",
  "What are the company's future plans?",
  "Compare keyboard vs mouse units in 2024",
  "Who is the CEO of Rahul Technologies?",
  "CAGR of total sales across all years",
];

function renderEmptyState() {
  chatArea.innerHTML = `
    <div class="empty-state">
      <div class="big-icon">🤖</div>
      <h2>Rahul Technologies Deep Agent</h2>
      <p>Ask me anything about the company — products, strategy, sales data, or annual reports.</p>
      <div class="suggestion-chips">
        ${SUGGESTIONS.map(s => `<span class="chip" onclick="useChip(this)">${s}</span>`).join("")}
      </div>
    </div>`;
}

function useChip(el) {
  msgInput.value = el.textContent;
  msgInput.focus();
  autoResize();
}

/* ══════════════════════════════════════════════════════════════════════════
   MESSAGE RENDERING
══════════════════════════════════════════════════════════════════════════ */

function appendUserMsg(text) {
  const es = chatArea.querySelector(".empty-state");
  if (es) es.remove();

  const row = document.createElement("div");
  row.className = "msg-row user";
  row.innerHTML = `
    <div class="avatar">👤</div>
    <div class="bubble">${escapeHtml(text)}</div>`;
  chatArea.appendChild(row);
  scrollBottom();
}

function appendBotMsg(text, intent, tools, execMs, steps, reasoningLog) {
  const row      = document.createElement("div");
  row.className  = "msg-row bot";

  const toolsHtml = tools?.length
    ? tools.map(t => t === "pdf" ? "📄 PDF" : "📊 Excel").join(" + ") + " &nbsp;|&nbsp; "
    : "";
  const execHtml  = execMs ? `⏱ ${(execMs / 1000).toFixed(2)}s` : "";
  const stepsHtml = steps  ? ` &nbsp;|&nbsp; 🧠 ${steps} step${steps !== 1 ? "s" : ""}` : "";

  // Build collapsible reasoning trace
  let reasoningHtml = "";
  if (reasoningLog && reasoningLog.length) {
    const traceId = "trace-" + Date.now();
    const lines   = reasoningLog.map(l => `<div class="trace-line">${escapeHtml(l)}</div>`).join("");
    reasoningHtml = `
      <details class="reasoning-trace">
        <summary>🧠 Reasoning trace (${reasoningLog.length} steps)</summary>
        <div class="trace-body">${lines}</div>
      </details>`;
  }

  row.innerHTML = `
    <div class="avatar">🤖</div>
    <div style="flex:1;min-width:0">
      <div class="bubble">${marked.parse(text)}</div>
      ${reasoningHtml}
      <div class="msg-meta">
        <span class="badge ${badgeClass(intent)}">${intentLabel(intent)}</span>
        <span style="font-size:0.72rem;color:var(--text2)">${toolsHtml}${execHtml}${stepsHtml}</span>
        <button class="action-btn" onclick="copyText(${JSON.stringify(text)})">📋 Copy</button>
        <button class="action-btn" onclick="regenerateLast()">🔄 Regenerate</button>
      </div>
    </div>`;

  chatArea.appendChild(row);
  lastBotMsgEl = row;
  row.querySelectorAll("pre code").forEach(el => hljs.highlightElement(el));
  scrollBottom();
}

/* ══════════════════════════════════════════════════════════════════════════
   SIDEBAR HISTORY
══════════════════════════════════════════════════════════════════════════ */

function renderHistory() {
  historyList.innerHTML = "";

  // Sort sessions by lastUpdated descending
  const sorted = Object.entries(chatSessions).sort(([, a], [, b]) => {
    return (b.lastUpdated || "").localeCompare(a.lastUpdated || "");
  });

  sorted.forEach(([id, sess]) => {
    const el       = document.createElement("div");
    el.className   = "history-item" + (id === currentSession ? " active" : "");

    const lost     = sess.serverMemoryLost ? " ⚠️" : "";
    const count    = sess.messages.length;
    const turns    = Math.floor(count / 2);   // user+bot pairs
    el.innerHTML   = `
      <div class="history-title">${escapeHtml(sess.title || "New Chat")}${lost}</div>
      <div class="history-meta">${turns} turn${turns !== 1 ? "s" : ""}</div>`;

    el.onclick     = () => switchSession(id);
    historyList.appendChild(el);
  });

  // Show session count badge
  const total = Object.keys(chatSessions).length;
  const badge = document.querySelector(".session-count");
  if (badge) badge.textContent = `${total} / ${MAX_SESSIONS}`;
}

/* ══════════════════════════════════════════════════════════════════════════
   SESSION MANAGEMENT
══════════════════════════════════════════════════════════════════════════ */

function createSession() {
  const id = crypto.randomUUID();
  chatSessions[id] = {
    title: "",
    messages: [],        // { role, content, intent, tools, timestamp }
    lastUpdated: new Date().toISOString(),
    serverMemoryLost: false,
  };
  return id;
}

function switchSession(id) {
  currentSession = id;
  rebuildChatFromSession();
  renderHistory();
}

function rebuildChatFromSession() {
  chatArea.innerHTML = "";
  const sess = chatSessions[currentSession];
  if (!sess?.messages.length) { renderEmptyState(); return; }

  if (sess.serverMemoryLost) {
    const warn = document.createElement("div");
    warn.style.cssText = "text-align:center;color:var(--warn);font-size:0.8rem;padding:8px;";
    warn.textContent = "⚠️ Server was restarted — LLM context for this session was reset. Chat history is shown for reference.";
    chatArea.appendChild(warn);
  }

  sess.messages.forEach(m => {
    if (m.role === "user")
      appendUserMsg(m.content);
    else
      appendBotMsg(m.content, m.intent || "GENERAL", m.tools || [], m.execMs || 0, m.steps || 0, m.reasoningLog || []);
  });
}

function newChat() {
  currentSession = createSession();
  enforceSessionCap();
  saveSessions();
  chatArea.innerHTML = "";
  renderEmptyState();
  renderHistory();
}

async function clearChat() {
  if (!currentSession) return;

  // Clear server-side memory for this session
  await fetch(`${API_BASE}/sessions/${currentSession}`, { method: "DELETE" }).catch(() => {});

  // Reset local session (keep the id + title, wipe messages)
  if (chatSessions[currentSession]) {
    chatSessions[currentSession].messages = [];
    chatSessions[currentSession].serverMemoryLost = false;
    chatSessions[currentSession].lastUpdated = new Date().toISOString();
  }
  saveSessions();
  chatArea.innerHTML = "";
  renderEmptyState();
  renderHistory();
}

/* ══════════════════════════════════════════════════════════════════════════
   CONNECT
══════════════════════════════════════════════════════════════════════════ */

async function connect() {
  buildBase();
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      setStatus(true, "Connected");
      const status = await (await fetch(`${API_BASE}/agent/status`)).json();
      showToast(`Model: ${status.model} | PDF chunks: ${status.pdf_chunks_count} | Excel rows: ${status.excel_row_count}`);
      await syncSessionsWithServer();
    } else {
      setStatus(false, "Server error");
    }
  } catch {
    setStatus(false, "Unreachable");
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   SEND MESSAGE
══════════════════════════════════════════════════════════════════════════ */

async function sendMessage() {
  const text = msgInput.value.trim();
  if (!text || isThinking) return;

  if (!connected) { showToast("⚠️ Not connected. Click Connect first."); return; }

  // Initialise title from first message
  const sess = chatSessions[currentSession];
  if (sess && !sess.title) sess.title = text.slice(0, 60);

  appendUserMsg(text);
  msgInput.value = "";
  autoResize();
  sendBtn.disabled = true;
  showThinking("Planning intent…");

  // Optimistically store user message
  const userEntry = { role: "user", content: text, timestamp: new Date().toISOString() };
  chatSessions[currentSession].messages.push(userEntry);
  chatSessions[currentSession].lastUpdated = userEntry.timestamp;
  saveSessions();
  renderHistory();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: currentSession }),
      signal: AbortSignal.timeout(120000),   // 2 min — allows up to 6 retries
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }));
      const detail = err.detail || `HTTP ${res.status}`;
      // Surface quota errors more helpfully
      if (res.status === 429 || detail.includes("quota") || detail.includes("429")) {
        throw new Error("API quota exceeded. The server retried but the limit persists. Please wait a minute and try again.");
      }
      throw new Error(detail);
    }

    const data = await res.json();

    if (data.tools_used?.length) {
      showThinking("Running tools…");
      showToolBadge(data.tools_used);
      await new Promise(r => setTimeout(r, 350));
    }

    hideThinking();
    appendBotMsg(data.answer, data.intent, data.tools_used, data.execution_time_ms, data.steps_taken, data.reasoning_log);

    // Store assistant turn with full metadata
    const botEntry = {
      role: "assistant",
      content: data.answer,
      intent: data.intent,
      tools: data.tools_used,
      execMs: data.execution_time_ms,
      steps: data.steps_taken,
      reasoningLog: data.reasoning_log,
      timestamp: new Date().toISOString(),
    };
    chatSessions[currentSession].messages.push(botEntry);
    chatSessions[currentSession].lastUpdated = botEntry.timestamp;
    chatSessions[currentSession].serverMemoryLost = false;

    // Enforce 10-turn cap in localStorage (20 messages = 10 user+bot pairs)
    const msgs = chatSessions[currentSession].messages;
    if (msgs.length > MAX_SESSIONS * 2) {
      chatSessions[currentSession].messages = msgs.slice(msgs.length - MAX_SESSIONS * 2);
    }

    saveSessions();
    renderHistory();

  } catch (err) {
    hideThinking();
    appendBotMsg(`❌ **Error:** ${err.message}`, "GENERAL", [], 0);
  } finally {
    sendBtn.disabled = false;
    msgInput.focus();
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   REGENERATE / DOWNLOAD
══════════════════════════════════════════════════════════════════════════ */

async function regenerateLast() {
  const sess = chatSessions[currentSession];
  if (!sess) return;
  const userMsgs = sess.messages.filter(m => m.role === "user");
  if (!userMsgs.length) return;

  const lastUser = userMsgs[userMsgs.length - 1].content;

  // Remove last bot message from store + UI
  const lastBotIdx = sess.messages.map(m => m.role).lastIndexOf("assistant");
  if (lastBotIdx !== -1) sess.messages.splice(lastBotIdx, 1);
  if (lastBotMsgEl) lastBotMsgEl.remove();

  saveSessions();
  msgInput.value = lastUser;
  await sendMessage();
}

function downloadChat() {
  const sess = chatSessions[currentSession];
  if (!sess?.messages.length) { showToast("Nothing to download."); return; }

  const lines = sess.messages.map(m => {
    const meta = m.intent ? ` | ${m.intent}` : "";
    return `[${m.role.toUpperCase()}${meta}]\n${m.content}\n`;
  });
  const blob = new Blob([lines.join("\n---\n\n")], { type: "text/plain" });
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(blob);
  a.download = `chat_${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
}

/* ══════════════════════════════════════════════════════════════════════════
   EVENT LISTENERS
══════════════════════════════════════════════════════════════════════════ */

connectBtn.addEventListener("click", connect);
sendBtn.addEventListener("click", sendMessage);
clearBtn.addEventListener("click", clearChat);
downloadBtn.addEventListener("click", downloadChat);
newChatBtn.addEventListener("click", newChat);
msgInput.addEventListener("input", autoResize);
msgInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

/* ══════════════════════════════════════════════════════════════════════════
   INIT — restore sessions from localStorage, set active session
══════════════════════════════════════════════════════════════════════════ */

loadSessions();

// Pick the most-recently-updated session, or create a fresh one
const existingIds = Object.keys(chatSessions).sort(
  (a, b) => (chatSessions[b].lastUpdated || "").localeCompare(chatSessions[a].lastUpdated || "")
);

if (existingIds.length > 0) {
  currentSession = existingIds[0];
} else {
  currentSession = createSession();
  saveSessions();
}

renderHistory();
rebuildChatFromSession();

// Auto-connect
connect();
