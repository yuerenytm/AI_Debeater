const $ = (sel) => document.querySelector(sel);

const topicInput = $("#topic");
const proModelSelect = $("#pro-model");
const conModelSelect = $("#con-model");
const startBtn = $("#start-btn");
const proMessages = $("#pro-messages");
const conMessages = $("#con-messages");
const refereeSection = $("#referee-section");
const refereeLoading = $("#referee-loading");
const refereeReport = $("#referee-report");
const reportSections = $("#report-sections");
const reportRaw = $("#report-raw");
const reportTopic = $("#report-topic");
const emptyState = $("#empty-state");

let isDebating = false;
const streamingBubbles = { pro: null, con: null };

const SECTION_PATTERNS = [
  { num: "壹", title: "核心交锋点拆解", keywords: ["核心交锋", "底层冲突"] },
  { num: "贰", title: "正方逻辑解剖", keywords: ["正方逻辑", "正方"] },
  { num: "叁", title: "反方逻辑解剖", keywords: ["反方逻辑", "反方"] },
  { num: "肆", title: "胜负裁决", keywords: ["胜负裁决", "胜方", "判胜"] },
  { num: "伍", title: "客观总结", keywords: ["客观总结", "概括"] },
];

async function loadModels() {
  const res = await fetch("/api/models");
  const { models } = await res.json();
  for (const sel of [proModelSelect, conModelSelect]) {
    sel.innerHTML = models.map((m) => `<option value="${m}">${m}</option>`).join("");
    sel.selectedIndex = 0;
  }
}

function createBubble(role, round, content, streaming = false) {
  const div = document.createElement("div");
  div.className = `bubble bubble-${role}`;
  const tagClass = role === "pro" ? "round-tag-pro" : "round-tag-con";
  const label = role === "pro" ? "正方" : "反方";
  const cursor = streaming ? '<span class="cursor">▌</span>' : "";
  div.innerHTML = `<div class="round-tag ${tagClass}">${label} · 第 ${round} 轮</div>${escapeHtml(content)}${cursor}`;
  return div;
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

function updateStreamingBubble(role, round, content) {
  const container = role === "pro" ? proMessages : conMessages;
  const key = role;

  if (!streamingBubbles[key]) {
    streamingBubbles[key] = createBubble(role, round, content, true);
    container.appendChild(streamingBubbles[key]);
  } else {
    const tagClass = role === "pro" ? "round-tag-pro" : "round-tag-con";
    const label = role === "pro" ? "正方" : "反方";
    streamingBubbles[key].innerHTML =
      `<div class="round-tag ${tagClass}">${label} · 第 ${round} 轮</div>${escapeHtml(content)}<span class="cursor">▌</span>`;
  }
  streamingBubbles[key].scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function finalizeBubble(role, round, content) {
  const container = role === "pro" ? proMessages : conMessages;
  if (streamingBubbles[role]) {
    streamingBubbles[role].remove();
    streamingBubbles[role] = null;
  }
  container.appendChild(createBubble(role, round, content, false));
}

function parseReportSections(markdown) {
  const sections = [];
  const lines = markdown.split("\n");
  let current = null;

  for (const line of lines) {
    const heading = line.match(/^#{1,3}\s+(.+)|^(\d+)[.、．]\s*(.+)/);
    if (heading) {
      if (current) sections.push(current);
      current = { title: heading[1] || heading[3] || line, body: [] };
    } else if (current) {
      current.body.push(line);
    } else if (line.trim()) {
      if (!current) current = { title: "综述", body: [] };
      current.body.push(line);
    }
  }
  if (current) sections.push(current);
  return sections;
}

function renderReportCards(markdown) {
  const parsed = parseReportSections(markdown);
  reportSections.innerHTML = "";

  parsed.forEach((sec, i) => {
    const meta = SECTION_PATTERNS[i] || { num: String(i + 1), title: sec.title };
    const card = document.createElement("div");
    card.className = "report-card";
    card.style.animationDelay = `${i * 0.1}s`;
    card.innerHTML = `
      <div class="report-card-num">第 ${meta.num} 章</div>
      <div class="report-card-title">${meta.title || sec.title}</div>
      <div class="report-card-body">${marked.parse(sec.body.join("\n"))}</div>
    `;
    reportSections.appendChild(card);
  });
}

function showRefereeLoading() {
  refereeSection.classList.remove("hidden");
  refereeLoading.classList.remove("hidden");
  refereeReport.classList.add("hidden");
  reportSections.innerHTML = "";
  reportRaw.classList.add("hidden");
  reportRaw.classList.remove("streaming");
}

function showRefereeStreaming(content) {
  refereeLoading.classList.add("hidden");
  refereeReport.classList.remove("hidden");
  reportRaw.classList.remove("hidden");
  reportRaw.classList.add("streaming");
  reportRaw.innerHTML = marked.parse(content) + '<span class="cursor">▌</span>';
  refereeSection.scrollIntoView({ behavior: "smooth" });
}

function showRefereeFinal(content, topic) {
  refereeLoading.classList.add("hidden");
  refereeReport.classList.remove("hidden");
  reportRaw.classList.remove("streaming");
  reportRaw.classList.add("hidden");
  reportTopic.textContent = `辩题：${topic}`;
  renderReportCards(content);
  refereeSection.scrollIntoView({ behavior: "smooth" });
}

function setDebating(val) {
  isDebating = val;
  startBtn.disabled = val;
  topicInput.disabled = val;
  proModelSelect.disabled = val;
  conModelSelect.disabled = val;
}

async function startDebate() {
  const topic = topicInput.value.trim();
  if (!topic) {
    alert("请先输入辩论主题");
    return;
  }

  setDebating(true);
  emptyState.classList.add("hidden");
  proMessages.innerHTML = "";
  conMessages.innerHTML = "";
  refereeSection.classList.add("hidden");
  streamingBubbles.pro = null;
  streamingBubbles.con = null;

  const params = new URLSearchParams({
    topic,
    pro_model: proModelSelect.value,
    con_model: conModelSelect.value,
  });

  const res = await fetch(`/api/debate/stream?${params}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));
      handleEvent(event, topic);
    }
  }

  setDebating(false);
}

function handleEvent(event, topic) {
  switch (event.type) {
    case "speech_delta":
      updateStreamingBubble(event.role, event.round, event.content);
      break;
    case "speech_end":
      finalizeBubble(event.role, event.round, event.content);
      break;
    case "referee_start":
      showRefereeLoading();
      break;
    case "referee_delta":
      showRefereeStreaming(event.content);
      break;
    case "referee_end":
      showRefereeFinal(event.content, topic);
      break;
    case "error":
      alert(`辩论出错：${event.message}`);
      setDebating(false);
      break;
  }
}

startBtn.addEventListener("click", startDebate);
topicInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !isDebating) startDebate();
});

loadModels();
