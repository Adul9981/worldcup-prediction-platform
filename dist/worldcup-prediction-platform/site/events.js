const paths = {
  events: "/data/prediction_events/latest_prediction_event_library.csv",
};

let state = {
  events: [],
  availability: "all",
  category: "all",
  direction: "all",
  query: "",
};

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && quoted && next === '"') {
      field += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(field);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const headers = rows.shift() || [];
  return rows.map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] || ""])),
  );
}

async function loadCsv(path) {
  const url = `${path}?v=${Date.now()}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`Cannot load ${path}`);
  return parseCsv(await response.text());
}

function num(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function fmtCompact(value) {
  const number = num(value);
  if (number >= 100000000) return `${(number / 100000000).toFixed(2)}亿`;
  if (number >= 10000) return `${(number / 10000).toFixed(1)}万`;
  if (number >= 1000) return `${(number / 1000).toFixed(1)}千`;
  return number ? number.toFixed(0) : "";
}

function percentNumber(value) {
  return num(String(value || "").replace("%", ""));
}

function statusClass(value) {
  if (value === "已上架") return "active";
  if (value === "待上架/待发现") return "watchlist";
  return "watchlist";
}

function directionClass(value) {
  if (value === "买 YES") return "yes";
  if (value === "回避") return "excluded";
  if (value === "监控") return "upside";
  return "neutral";
}

function riskClass(value) {
  if (value === "回避") return "excluded";
  return "neutral";
}

function passed(row) {
  return row.rule_check_result === "通过";
}

function admitted(row, bucket) {
  return passed(row) && row.focus_bucket === bucket && row.focus_admission_note && row.focus_admission_note !== "未经过人工准入";
}

function isTodayEvent(row) {
  const today = todayKey();
  return row.stage === "小组赛" && row.library_id.includes("M001") || row.event_title_cn.includes("今日");
}

function payoffText(row) {
  if (row.price) return `价格 ${row.price} / 回报率 ${row.return_rate || "--"}`;
  if (row.volume_24hr) return `24h量 ${fmtCompact(row.volume_24hr)}`;
  return "待市场定价";
}

function setOptions(id, values, allLabel) {
  const select = document.getElementById(id);
  select.innerHTML = [
    `<option value="all">${allLabel}</option>`,
    ...values.map((value) => `<option value="${value}">${value}</option>`),
  ].join("");
}

function renderMetrics() {
  const live = state.events.filter((row) => row.availability === "已上架").length;
  const watch = state.events.filter((row) => row.availability === "待上架/待发现").length;
  const focused = state.events.filter((row) => row.focus_bucket && row.focus_bucket !== "未入选").length;
  document.getElementById("event-total").textContent = String(state.events.length);
  document.getElementById("event-live").textContent = String(live);
  document.getElementById("event-yes").textContent = String(focused);
  document.getElementById("event-watch").textContent = String(watch);
}

function renderFilters() {
  setOptions("availability-filter", [...new Set(state.events.map((row) => row.availability).filter(Boolean))], "全部状态");
  setOptions("category-filter", [...new Set(state.events.map((row) => row.event_category_cn).filter(Boolean))].sort(), "全部类型");
  setOptions("direction-filter", [...new Set(state.events.map((row) => row.direction_cn).filter(Boolean))], "全部方向");
}

function renderCompactList(id, rows, emptyText) {
  const root = document.getElementById(id);
  if (!rows.length) {
    root.innerHTML = `<div class="empty">${emptyText}</div>`;
    return;
  }
  root.innerHTML = rows
    .map(
      (row) => `
      <div class="team-row">
        <div>
          <strong>${row.event_title_cn}</strong>
          <span>${row.direction_cn}</span>
        </div>
        <small>${payoffText(row)} · ${row.structure_cn}</small>
        <small>${row.strategy_summary}</small>
      </div>
    `,
    )
    .join("");
}

function renderTopSections() {
  const todayRows = state.events
    .filter((row) => admitted(row, "每日关注"))
    .slice(0, 6);
  document.getElementById("today-event-list").innerHTML = todayRows.length
    ? todayRows
        .map(
          (row) => `
          <article class="ranking-card">
            <div class="card-top">
              <span class="badge ${statusClass(row.availability)}">${row.availability}</span>
              <span class="track ${riskClass(row.risk_tier)}">${row.risk_tier}</span>
            </div>
            <div class="rank-title">${row.event_title_cn}</div>
            <div class="score-grid">
              <div><span>方向</span><strong>${row.direction_cn}</strong></div>
              <div><span>结构</span><strong>${row.structure_cn}</strong></div>
              <div><span>价格</span><strong>${row.price || "--"}</strong></div>
              <div><span>回报率</span><strong>${row.return_rate || "待定"}</strong></div>
            </div>
            <p class="copy-angle">${row.strategy_summary}</p>
          </article>
        `,
        )
        .join("")
    : '<div class="ranking-card">暂无通过准入的每日关注事件。先空着，等规则和人工准入记录补齐后再展示。</div>';

  const lowRisk = state.events
    .filter((row) => admitted(row, "低风险"))
    .sort((a, b) => num(b.liquidity) - num(a.liquidity))
    .slice(0, 6);
  const highRisk = state.events
    .filter((row) => admitted(row, "高风险"))
    .sort((a, b) => percentNumber(b.return_rate) - percentNumber(a.return_rate))
    .slice(0, 6);
  renderCompactList("low-risk-list", lowRisk, "暂无通过准入的低风险事件。");
  renderCompactList("high-risk-list", highRisk, "暂无通过准入的高风险事件。");

  const stageCounts = state.events.reduce((acc, row) => {
    const key = row.stage || "跨阶段";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  document.getElementById("event-progress-list").innerHTML = Object.entries(stageCounts)
    .slice(0, 7)
    .map(
      ([stage, count]) => `
      <div class="side-row">
        <span>${stage}</span>
        <strong>${count}</strong>
      </div>
    `,
    )
    .join("");

  const selectable = state.events
    .filter((row) => admitted(row, "可选策略"))
    .sort((a, b) => num(b.volume_24hr) - num(a.volume_24hr))
    .slice(0, 3);
  document.getElementById("selectable-strategy-list").innerHTML = selectable.length ? selectable
    .map(
      (row) => `
      <article class="focus-card">
        <div class="card-top">
          <span class="track ${directionClass(row.direction_cn)}">${row.direction_cn}</span>
          <span class="badge ${statusClass(row.availability)}">${row.risk_tier}</span>
        </div>
        <h2>${row.event_title_cn}</h2>
        <div class="focus-metrics">
          <div><span>价格</span><strong>${row.price || "--"}</strong></div>
          <div><span>回报率</span><strong>${row.return_rate || "待定"}</strong></div>
          <div><span>24h量</span><strong>${fmtCompact(row.volume_24hr)}</strong></div>
        </div>
        <p>${row.strategy_summary}</p>
        ${row.affiliate_url ? `<a class="market-link" href="${row.affiliate_url}" target="_blank" rel="noreferrer">前往 Polymarket</a>` : ""}
      </article>
    `,
    )
    .join("") : '<article class="focus-card"><h2>暂无通过准入的可选预测策略</h2><p>重点策略先空着，等规则和人工准入记录补齐后再展示。</p></article>';
}

function filteredRows() {
  const query = state.query.trim().toLowerCase();
  return state.events.filter((row) => {
    const availabilityOk = state.availability === "all" || row.availability === state.availability;
    const categoryOk = state.category === "all" || row.event_category_cn === state.category;
    const directionOk = state.direction === "all" || row.direction_cn === state.direction;
    const text = [
      row.event_title_cn,
      row.event_category_cn,
      row.stage,
      row.group_code,
      row.home_team,
      row.away_team,
      row.strategy_summary,
      row.monitor_trigger,
    ]
      .join(" ")
      .toLowerCase();
    return availabilityOk && categoryOk && directionOk && (!query || text.includes(query));
  });
}

function renderTable() {
  const rows = filteredRows();
  document.getElementById("event-visible").textContent = `当前显示 ${rows.length} 个事件`;
  document.getElementById("event-table-body").innerHTML = rows
    .map(
      (row) => `
      <tr>
        <td>
          <strong>${row.event_title_cn}</strong>
          <small>${row.stage || "跨阶段"}${row.group_code ? ` · ${row.group_code}组` : ""}</small>
        </td>
        <td><span class="badge ${statusClass(row.availability)}">${row.availability}</span></td>
        <td>${row.event_category_cn}</td>
        <td>
          <strong>${row.structure_cn}</strong>
          <small>${row.is_mutually_exclusive === "是" ? "互斥" : "非互斥/独立"}</small>
        </td>
        <td>
          <span class="track ${riskClass(row.risk_tier)}">${row.risk_tier || "未分层"}</span>
          <small>${row.focus_bucket || "未入选"} · ${row.focus_admission_note || "未经过人工准入"}</small>
        </td>
        <td><span class="track ${directionClass(row.direction_cn)}">${row.direction_cn}</span></td>
        <td>
          <strong>${row.price || "--"}</strong>
          <small>${row.return_rate ? `回报率 ${row.return_rate}` : row.volume_24hr ? `24h量 ${fmtCompact(row.volume_24hr)}` : "待市场定价"}</small>
        </td>
        <td>${row.strategy_summary}</td>
        <td>${row.monitor_trigger}</td>
        <td>${row.affiliate_url ? `<a class="market-link" href="${row.affiliate_url}" target="_blank" rel="noreferrer">前往 Polymarket</a>` : "待上架"}</td>
      </tr>
    `,
    )
    .join("");
}

function render() {
  renderMetrics();
  renderFilters();
  renderTable();
}

async function main() {
  state.events = await loadCsv(paths.events);
  render();
}

document.getElementById("availability-filter").addEventListener("change", (event) => {
  state.availability = event.target.value;
  renderTable();
});

document.getElementById("category-filter").addEventListener("change", (event) => {
  state.category = event.target.value;
  renderTable();
});

document.getElementById("direction-filter").addEventListener("change", (event) => {
  state.direction = event.target.value;
  renderTable();
});

document.getElementById("event-search").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderTable();
});

main().catch((error) => {
  document.getElementById("event-table-body").innerHTML = `<tr><td colspan="10">数据加载失败：${error.message}</td></tr>`;
});
