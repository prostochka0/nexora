const els = {
  statusLabel: document.getElementById("status-label"),
  toggle: document.getElementById("toggle"),
  toggleState: document.getElementById("toggle-state"),
  toggleHint: document.getElementById("toggle-hint"),
  feedback: document.getElementById("feedback"),
  meta: document.getElementById("meta"),
  metaSystem: document.getElementById("meta-system"),
  metaAdapters: document.getElementById("meta-adapters"),
  adminNote: document.getElementById("admin-note"),
};

let busy = false;
let online = false;

function setFeedback(text, kind = "") {
  els.feedback.textContent = text || "";
  els.feedback.className = `feedback${kind ? ` ${kind}` : ""}`;
}

function paint(status) {
  online = Boolean(status.online);
  els.toggle.disabled = false;
  els.toggle.setAttribute("aria-pressed", String(online));
  els.statusLabel.textContent = online ? "Сеть активна" : "Сеть отключена";
  els.toggleState.textContent = online ? "Включено" : "Выключено";
  els.toggleHint.textContent = online ? "Нажмите, чтобы отключить интернет" : "Нажмите, чтобы включить интернет";
  els.meta.hidden = false;
  els.metaSystem.textContent = status.system || "—";
  const adapters = Array.isArray(status.adapters) ? status.adapters : [];
  els.metaAdapters.textContent = adapters.length ? adapters.join(", ") : "не обнаружены";
  els.adminNote.hidden = Boolean(status.elevated);
}

async function refresh({ clearFeedback = false } = {}) {
  if (busy) return;
  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error("status " + res.status);
    const data = await res.json();
    paint(data);
    if (clearFeedback) setFeedback("");
  } catch (err) {
    els.statusLabel.textContent = "Нет связи с Nexora";
    setFeedback("Не удалось получить статус сети.", "error");
    els.toggle.disabled = true;
  }
}

async function toggle() {
  if (busy) return;
  busy = true;
  els.toggle.disabled = true;
  setFeedback(online ? "Отключаю интернет…" : "Включаю интернет…");

  try {
    const res = await fetch("/api/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ online: !online }),
    });
    const data = await res.json();
    paint(data);
    if (!data.ok) {
      setFeedback(data.message || "Не удалось переключить сеть.", data.needs_admin ? "warn" : "error");
    } else {
      setFeedback(data.message || "");
    }
  } catch (err) {
    setFeedback("Ошибка запроса к серверу Nexora.", "error");
  } finally {
    busy = false;
    els.toggle.disabled = false;
  }
}

els.toggle.addEventListener("click", toggle);
refresh({ clearFeedback: true });
setInterval(() => refresh(), 8000);
