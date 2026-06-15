const API_PATH = "/api/recommendations";
const TOKEN_KEY = "worldcup.admin.token.v1";
const AFFILIATE_CODE = "serene77mc-g6kj";

let manualItems = [];

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function affiliateUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw);
    if (url.hostname.includes("polymarket.com")) {
      url.searchParams.set("via", AFFILIATE_CODE);
    }
    return url.toString();
  } catch {
    return raw;
  }
}

function renderStrategyText(value) {
  const lines = String(value || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return '<p class="strategy-line">暂无策略正文。</p>';
  return lines
    .map((line) => {
      const clean = escapeHtml(line.replace(/^\*\s*/, ""));
      if (/^(预测|比分预测|理由|下注方向推荐|方向推荐|主推|保守玩法|备选|进攻玩法|取消条件)：?/.test(line)) {
        return `<p class="strategy-line strategy-key">${clean}</p>`;
      }
      if (line.startsWith("*")) {
        return `<p class="strategy-line strategy-bullet">${clean}</p>`;
      }
      return `<p class="strategy-line">${clean}</p>`;
    })
    .join("");
}

function token() {
  return document.getElementById("admin-token").value.trim();
}

function setStatus(message, tone = "") {
  const root = document.getElementById("manual-status");
  root.textContent = message;
  root.className = `form-status ${tone}`.trim();
}

function normalizeItems(items) {
  return (Array.isArray(items) ? items : [])
    .filter((item) => item && item.status !== "draft")
    .map((item) => ({
      id: item.id || `${item.date || ""}-${item.title || ""}`,
      created_at: item.created_at || item.date || "",
      title: item.title || "今日推荐策略",
      direction: item.direction || "重点推荐",
      analysis: item.analysis || "",
      url: affiliateUrl(item.url || ""),
      status: item.status || "active",
    }));
}

async function loadManual() {
  const response = await fetch(`${API_PATH}?v=${Date.now()}`, { cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || "今日推荐加载失败");
  }
  manualItems = normalizeItems(payload.items);
}

async function saveManual(items) {
  if (!token()) throw new Error("请先填写管理口令。");
  localStorage.setItem(TOKEN_KEY, token());
  const response = await fetch(API_PATH, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-admin-token": token(),
    },
    body: JSON.stringify({ items }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || "保存失败");
  }
  manualItems = normalizeItems(payload.items);
}

function buildManualItem(item) {
  const firstLine = String(item.analysis || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);
  return {
    id: String(Date.now()),
    created_at: new Date().toISOString(),
    date: new Date().toISOString().slice(0, 10),
    title: item.title || firstLine || "今日推荐策略",
    direction: item.direction,
    analysis: item.analysis,
    url: affiliateUrl(item.url),
    status: "active",
  };
}

function renderManual() {
  const root = document.getElementById("manual-list");
  if (!manualItems.length) {
    root.innerHTML = '<article class="manual-card empty-manual"><span class="badge watchlist">今日推荐</span><h2>暂无置顶策略</h2></article>';
    return;
  }
  root.innerHTML = manualItems
    .map(
      (item) => `
      <article class="manual-card">
        <div class="card-top">
          <span class="badge hot">今日推荐</span>
          <span class="track yes">${escapeHtml(item.direction || "等待")}</span>
        </div>
        <h2>${escapeHtml(item.title)}</h2>
        <div class="strategy-body">${renderStrategyText(item.analysis)}</div>
        <div class="manual-card-actions">
          ${item.url ? `<a class="market-link" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">前往 Polymarket</a>` : "<span></span>"}
          <button type="button" class="tab" data-manual-delete="${escapeHtml(item.id)}">删除</button>
        </div>
      </article>
    `,
    )
    .join("");
}

document.getElementById("manual-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = document.getElementById("manual-title").value.trim();
  const analysis = document.getElementById("manual-analysis").value.trim();
  const item = buildManualItem({
    title,
    direction: document.getElementById("manual-direction").value,
    analysis,
    url: document.getElementById("manual-url").value.trim(),
  });
  if (!item.title && !item.analysis) return;
  try {
    setStatus("保存中...");
    await saveManual([item, ...manualItems].slice(0, 8));
    event.target.reset();
    document.getElementById("admin-token").value = localStorage.getItem(TOKEN_KEY) || "";
    renderManual();
    setStatus("已保存到线上。", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.getElementById("manual-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-manual-delete]");
  if (!button) return;
  try {
    setStatus("删除中...");
    await saveManual(manualItems.filter((item) => item.id !== button.dataset.manualDelete));
    renderManual();
    setStatus("已删除。", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.getElementById("manual-clear").addEventListener("click", async () => {
  try {
    setStatus("清空中...");
    await saveManual([]);
    renderManual();
    setStatus("已清空。", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.getElementById("admin-token").value = localStorage.getItem(TOKEN_KEY) || "";
loadManual()
  .then(() => {
    renderManual();
    setStatus("线上列表已加载。", "ok");
  })
  .catch((error) => {
    renderManual();
    setStatus(error.message, "error");
  });
