let sessionId = null;

const chatEl = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const planActions = document.getElementById("plan-actions");
const btnConfirm = document.getElementById("btn-confirm");
const btnCancel = document.getElementById("btn-cancel");
const fileInput = document.getElementById("file-input");
const btnUpload = document.getElementById("btn-upload");
const uploadStatus = document.getElementById("upload-status");

function renderMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br>");
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = renderMarkdown(text);
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function setPlanVisible(visible) {
  planActions.classList.toggle("hidden", !visible);
}

async function sendChat(message) {
  addMessage("user", message);
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  const data = await res.json();
  sessionId = data.session_id;
  addMessage("bot", data.message);
  setPlanVisible(data.response_type === "plan");
}

async function sendConfirm(confirmed) {
  const res = await fetch("/api/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, confirmed }),
  });
  const data = await res.json();
  addMessage("bot", data.message);
  setPlanVisible(false);
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendChat(text);
});

btnConfirm.addEventListener("click", () => sendConfirm(true));
btnCancel.addEventListener("click", () => sendConfirm(false));

btnUpload.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) {
    uploadStatus.textContent = "Choose a file first";
    uploadStatus.style.color = "#f87171";
    return;
  }
  uploadStatus.textContent = "Uploading…";
  uploadStatus.style.color = "";
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: formData });
  if (!res.ok) {
    uploadStatus.textContent = "Upload failed";
    uploadStatus.style.color = "#f87171";
    return;
  }
  const data = await res.json();
  uploadStatus.textContent = `Saved as ${data.path}`;
  uploadStatus.style.color = "";
  input.value = `Load ${data.path} into SQLite table customers`;
  input.focus();
});

document.querySelectorAll(".examples li").forEach((li) => {
  li.addEventListener("click", () => {
    input.value = li.dataset.prompt;
    input.focus();
  });
});

async function loadAgents() {
  const res = await fetch("/api/agents");
  const agents = await res.json();
  const list = document.getElementById("agents-list");
  agents.forEach((a) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="name">${a.name}</span><br><small>${a.agent_id}</small>`;
    list.appendChild(li);
  });
}

addMessage("bot", "Welcome! Describe what you want to ingest (source → destination). I will ask for any missing details, show a plan, and wait for your confirmation before running.");
loadAgents();
