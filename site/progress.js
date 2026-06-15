const paths = {
  matches: "/data/templates/matches.csv",
  topics: "/data/polymarket/latest_prediction_market_topics.csv",
  opportunities: "/data/polymarket/latest_market_opportunities.csv",
  glossary: "/data/templates/glossary_cn_en.csv",
  refresh: "/data/polymarket/latest_refresh_status.json",
};

let state = {
  matches: [],
  topics: [],
  opportunities: [],
  glossary: [],
  refresh: {},
  zhMap: new Map(),
};

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
  const url = `${path}${path.includes("?") ? "&" : "?"}v=${Date.now()}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`Cannot load ${path}`);
  return parseCsv(await response.text());
}

async function loadJson(path) {
  const url = `${path}${path.includes("?") ? "&" : "?"}v=${Date.now()}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) return {};
  return response.json();
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function buildGlossary() {
  state.zhMap = new Map(state.glossary.map((row) => [row.en, row.zh]));
}

function zh(value) {
  return state.zhMap.get(value) || value || "";
}

function stageLabel(stage) {
  return {
    "Third Place": "季军赛",
  }[stage] || zh(stage) || "小组赛";
}

function formatDate(value) {
  if (!value) return "日期待补";
  const date = new Date(`${value}T00:00:00+08:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "short" });
}

function formatDateTime(value) {
  if (!value) return "未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function dateKeyInChina(value) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function todayKey() {
  return dateKeyInChina(new Date());
}

function parseChinaTime(value) {
  if (!value) return null;
  const date = new Date(`${value.replace(" ", "T")}:00+08:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatChinaKickoff(row) {
  const date = parseChinaTime(row.china_time);
  if (!date) return `${formatDate(row.date)} · 开球时间待确认`;
  return date.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function stageOrder(stage) {
  return {
    Group: 1,
    "Round of 32": 2,
    "Round of 16": 3,
    Quarterfinal: 4,
    Semifinal: 5,
    "Third Place": 6,
    Final: 7,
  }[stage] || 99;
}

function renderRefreshStatus() {
  const root = document.getElementById("refresh-status");
  if (!root) return;
  const mode = state.refresh.fetched_from_polymarket ? "联网刷新" : "本地重建";
  const status = state.refresh.status === "ok" ? "正常" : "异常";
  const matches = state.refresh.match_rows ? ` · 赛程 ${state.refresh.match_rows} 场` : "";
  root.textContent = `数据${status} · ${mode}${matches} · ${formatDateTime(state.refresh.updated_at)}`;
}

function currentStage() {
  const today = todayKey();
  const sorted = [...state.matches].filter((row) => row.date).sort((a, b) => a.date.localeCompare(b.date));
  if (!sorted.length) return "小组赛";
  const latestStarted = [...sorted].reverse().find((row) => row.date <= today);
  if (latestStarted) return stageLabel(latestStarted.stage);
  return stageLabel(sorted[0].stage);
}

function countBy(rows, key) {
  return rows.reduce((map, row) => {
    const value = row[key] || "未知";
    map[value] = (map[value] || 0) + 1;
    return map;
  }, {});
}

function renderMetrics() {
  setText("progress-current", currentStage());
  setText("progress-matches", String(state.matches.length));
  setText("progress-topics", String(state.topics.length));
}

function renderTimeline() {
  const today = todayKey();
  const phases = [
    ["Group", "2026-06-11", "2026-06-27", "小组出线、冠军盘早期错价、弱队对手盘"],
    ["Round of 32", "2026-06-28", "2026-07-03", "路径定价、晋级概率、强队避坑"],
    ["Round of 16", "2026-07-04", "2026-07-07", "淘汰赛单场、加时点球、热门过热"],
    ["Quarterfinal", "2026-07-09", "2026-07-11", "冠军盘收敛、风险再评估"],
    ["Semifinal", "2026-07-14", "2026-07-15", "冠军和决赛路径再定价"],
    ["Final", "2026-07-18", "2026-07-19", "季军赛与最终冠军盘"],
  ];
  document.getElementById("progress-timeline").innerHTML = phases
    .map(
      ([phase, start, end, focus]) => {
        const status = today < start ? "后续" : today > end ? "已过" : "当前";
        return `
      <article class="stage ${status === "当前" ? "current" : ""}">
        <span>${status}</span>
        <strong>${stageLabel(phase)}</strong>
        <small>${formatDate(start)} - ${formatDate(end)}</small>
        <small>${focus}</small>
      </article>
    `;
      },
    )
    .join("");
}

function renderFocus() {
  const rows = [
    ["小组赛交易重点", "冠军盘、出线预期和弱队相关盘会先积累交易量，低交易量不等于无价值。"],
    ["淘汰赛交易重点", "互斥路径更重要，必须合并看相关风险、方向置信度和取消条件。"],
    ["冠军盘交易重点", "当前大部分世界杯选题属于同一冠军事件下的多选题互斥组。"],
  ];
  document.getElementById("phase-focus").innerHTML = rows
    .map(
      ([title, text]) => `
      <article class="ranking-card">
        <div class="rank-title">${title}</div>
        <p class="copy-angle">${text}</p>
      </article>
    `,
    )
    .join("");
}

function renderSidePanels() {
  renderCounts("progress-structures", countBy(state.opportunities, "market_structure_type"), true);
  renderCounts("progress-directions", countBy(state.opportunities, "selection_direction"), false);
  renderStageCounts();
}

function renderCounts(id, counts, translate) {
  document.getElementById(id).innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(
      ([label, count]) => `
      <div class="side-row">
        <span>${translate ? zh(label) : zh(label)}</span>
        <strong>${count}</strong>
      </div>
    `,
    )
    .join("");
}

function renderStageCounts() {
  const counts = countBy(state.matches, "stage");
  document.getElementById("progress-stage-counts").innerHTML = Object.entries(counts)
    .sort((a, b) => stageOrder(a[0]) - stageOrder(b[0]))
    .map(
      ([label, count]) => `
      <div class="side-row">
        <span>${stageLabel(label)}</span>
        <strong>${count}</strong>
      </div>
    `,
    )
    .join("");
}

function matchStatus(row) {
  const today = todayKey();
  const kickoff = parseChinaTime(row.china_time);
  if (kickoff) {
    const now = new Date();
    const finishedAt = new Date(kickoff.getTime() + 120 * 60 * 1000);
    if (now >= finishedAt) return "已结束";
    if (now >= kickoff) return "进行中";
    return dateKeyInChina(kickoff) === today ? "今日" : "后续";
  }
  if (!row.date) return "时间待确认";
  if (row.date < today) return "已结束";
  if (row.date === today) return "今日";
  return "后续";
}

function matchStatusClass(status) {
  if (status === "今日" || status === "进行中") return "active";
  if (status === "已结束") return "risk";
  return "watchlist";
}

function renderUpcomingMatches() {
  const root = document.getElementById("upcoming-matches");
  const rows = [...state.matches].sort((a, b) => {
    const dateCompare = String(a.date || "9999").localeCompare(String(b.date || "9999"));
    if (dateCompare !== 0) return dateCompare;
    return stageOrder(a.stage) - stageOrder(b.stage);
  });
  root.innerHTML = rows
    .map((row) => {
      const status = matchStatus(row);
      return `
      <article class="match-row">
        <div>
          <span class="badge ${matchStatusClass(status)}">${status} · ${stageLabel(row.stage)}${row.group ? ` · ${row.group}组` : ""}</span>
          <h3>${zh(row.home_team)} 对阵 ${zh(row.away_team)}</h3>
          <p>北京时间 ${formatChinaKickoff(row)} · ${row.venue || "场地待补"}</p>
        </div>
        <div class="priority ${String(row.priority || "").toLowerCase()}">${row.priority || "待评估"}</div>
      </article>
    `;
    })
    .join("");
}

function render() {
  renderRefreshStatus();
  renderMetrics();
  renderTimeline();
  renderUpcomingMatches();
}

async function main() {
  [state.matches, state.topics, state.opportunities, state.glossary, state.refresh] = await Promise.all([
    loadCsv(paths.matches),
    loadCsv(paths.topics),
    loadCsv(paths.opportunities),
    loadCsv(paths.glossary),
    loadJson(paths.refresh),
  ]);
  buildGlossary();
  render();
}

main().catch((error) => {
  document.querySelector("main").innerHTML = `<section class="panel">数据加载失败：${error.message}</section>`;
});
