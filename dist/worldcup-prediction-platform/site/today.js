const paths = {
  apiManual: "/api/recommendations",
  opportunities: "/data/polymarket/latest_market_opportunities.csv",
  events: "/data/prediction_events/latest_prediction_event_library.csv",
  rankings: "/data/polymarket/latest_daily_event_rankings.csv",
  matches: "/data/templates/matches.csv",
  glossary: "/data/templates/glossary_cn_en.csv",
  manual: "/data/templates/manual_recommendations.json",
  refresh: "/data/polymarket/latest_refresh_status.json",
};

const AFFILIATE_CODE = "serene77mc-g6kj";

let state = {
  opportunities: [],
  events: [],
  rankings: [],
  matches: [],
  glossary: [],
  refresh: {},
  apiManual: [],
  publishedManual: [],
  zhMap: new Map(),
  manual: [],
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

async function loadApiManual() {
  const url = `${paths.apiManual}?v=${Date.now()}`;
  const response = await fetch(url, { cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) return [];
  return payload.items || [];
}

function buildGlossary() {
  state.zhMap = new Map(state.glossary.map((row) => [row.en, row.zh]));
}

function zh(value) {
  return state.zhMap.get(value) || value || "";
}

function zhText(value) {
  let text = value || "";
  const avoid = text.match(/^Avoid: status\/risk rules block entry for (.+)\.$/);
  if (avoid) return `规则建议回避：${marketTitle(avoid[1])}。`;
  const entries = [...state.zhMap.entries()].sort((a, b) => b[0].length - a[0].length);
  for (const [en, cn] of entries) {
    if (en) text = text.replaceAll(en, cn);
  }
  return text
    .replaceAll("Upside profile is visible; wait for price, quota, or thesis confirmation before entry.", "存在高回报观察特征，等待价格或交易理由确认。")
    .replaceAll("Model direction is YES; price, risk and score passed current rules.", "模型方向为买 YES；价格、风险和评分通过当前规则。")
    .replaceAll("No current edge signal; keep it in the watch pool.", "当前没有明确优势信号，保留观察。")
    .replaceAll("Conservative profile is visible; wait for price or thesis confirmation before entry.", "存在稳健观察特征，等待价格或交易理由确认。")
    .replaceAll("Cancel if market closes, liquidity disappears, or thesis cannot be written in one sentence.", "若市场关闭、流动性消失，或无法用一句话说明理由，则取消。")
    .replaceAll("?", "？");
}

function num(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function fmt(value, digits = 2) {
  return num(value).toFixed(digits).replace(/\.00$/, "");
}

function fmtCompact(value) {
  const number = num(value);
  if (number >= 100000000) return `${fmt(number / 100000000, 2)}亿`;
  if (number >= 10000) return `${fmt(number / 10000, 1)}万`;
  if (number >= 1000) return `${fmt(number / 1000, 1)}千`;
  return fmt(number, 0);
}

function returnRateValue(value) {
  const price = num(value);
  if (price <= 0 || price >= 1) return 0;
  return (1 / price - 1) * 100;
}

function returnRate(value) {
  const rate = returnRateValue(value);
  if (!rate) return "--";
  if (rate >= 1000) return `${fmt(rate, 0)}%`;
  return `${fmt(rate, 1)}%`;
}

function formatDateTime(value) {
  if (!value) return "未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

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
      if (/^(预测|比分预测|理由|下注方向推荐|方向推荐|主推|保守玩法|备选|进攻玩法)：?/.test(line)) {
        return `<p class="strategy-line strategy-key">${clean}</p>`;
      }
      if (line.startsWith("*")) {
        return `<p class="strategy-line strategy-bullet">${clean}</p>`;
      }
      return `<p class="strategy-line">${clean}</p>`;
    })
    .join("");
}

function normalizeManualItems(items) {
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

function loadManual() {
  const apiManual = normalizeManualItems(state.apiManual);
  state.manual = apiManual.length ? apiManual : normalizeManualItems(state.publishedManual);
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
  if (!row.china_time) return `${row.date || "日期待补"} · 开球时间待确认`;
  const date = parseChinaTime(row.china_time);
  if (!date) return `${row.china_time} · 开球时间待确认`;
  return date.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function matchRuntimeStatus(row) {
  const kickoff = parseChinaTime(row.china_time);
  if (!kickoff) return "时间待确认";
  const now = new Date();
  const finishedAt = new Date(kickoff.getTime() + 120 * 60 * 1000);
  if (now >= finishedAt) return "已结束";
  if (now >= kickoff) return "进行中";
  return "未开始";
}

function marketTitle(title) {
  const mapped = zh(title);
  if (mapped !== title) return mapped;
  const winner = title.match(/^Will (.+) win the 2026 FIFA World Cup\?$/);
  if (winner) return `${zh(winner[1])}是否赢得2026年世界杯？`;
  return title.replaceAll("?", "？");
}

function segmentLabel(value) {
  return {
    strong_team: "明显强队",
    weak_team_related: "弱队相关",
    swing_team: "摇摆队",
    overheat_risk: "过热风险",
    mutual_group_high_price_anchor: "互斥组锚点",
    high_return_watch: "高回报观察",
    special_event: "特殊事件",
    risk_avoid: "风险回避",
    buy_direction: "买入方向",
    normal_watch: "普通观察",
  }[value] || value || "普通观察";
}

function directionLabel(value) {
  return zh(value) || value || "等待";
}

function stageLabel(stage) {
  return {
    Group: "小组赛",
    "Round of 32": "32强",
    "Round of 16": "16强",
    Quarterfinal: "八强",
    Semifinal: "半决赛",
    "Third Place": "季军赛",
    Final: "决赛",
  }[stage] || stage || "待赛";
}

function statusClass(status) {
  if (status === "hot" || status === "active") return status;
  if (status === "excluded" || status === "closed" || status === "resolved") return "risk";
  return "watchlist";
}

function trackClass(row) {
  if (row.selection_direction === "YES") return "yes";
  if (row.selection_direction === "AVOID") return "excluded";
  if (row.recommendation_track === "upside") return "upside";
  return "neutral";
}

function todayMatches() {
  const today = todayKey();
  return state.matches
    .filter((row) => row.date === today)
    .filter((row) => matchRuntimeStatus(row) !== "已结束")
    .sort((a, b) => String(a.china_time || a.date).localeCompare(String(b.china_time || b.date)));
}

function admitted(row, bucket) {
  return row.rule_check_result === "通过"
    && row.focus_bucket === bucket
    && row.focus_admission_note
    && row.focus_admission_note !== "未经过人工准入";
}

function primaryRows() {
  return state.events
    .filter((row) => admitted(row, "每日关注"))
    .slice(0, 3);
}

function todayRows() {
  return state.events
    .filter((row) => admitted(row, "每日关注"))
    .slice(0, 10);
}

function analysisText(row) {
  if (row.selection_direction === "YES") return "今日方向为买 YES；仍需点进市场确认盘口深度和成交状态。";
  if (row.selection_direction === "AVOID") return "今日不参与：状态、结构或风险规则不合格。";
  if (row.recommendation_track === "upside") return "高回报观察：价格空间大，但必须等待更清晰理由。";
  return zhText(row.direction_thesis);
}

function renderRefreshStatus() {
  const root = document.getElementById("refresh-status");
  if (!root) return;
  const mode = state.refresh.fetched_from_polymarket ? "联网刷新" : "本地重建";
  const status = state.refresh.status === "ok" ? "正常" : "异常";
  root.textContent = `数据${status} · ${mode} · ${formatDateTime(state.refresh.updated_at)}`;
}

function renderManual() {
  const root = document.getElementById("manual-list");
  if (!state.manual.length) {
    root.innerHTML = '<article class="manual-card empty-manual"><span class="badge watchlist">今日推荐</span><h2>今日推荐待更新</h2></article>';
    return;
  }
  root.innerHTML = state.manual
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
        </div>
      </article>
    `,
    )
    .join("");
}

function renderPrimary() {
  const rows = primaryRows();
  document.getElementById("primary-actions").innerHTML = rows.length ? rows
    .map(
      (row) => `
      <article class="focus-card">
        <div class="card-top">
          <span class="track ${row.selection_direction === "MONITOR" ? "upside" : trackClass(row)}">${row.direction_cn || directionLabel(row.selection_direction)}</span>
          <span class="badge ${statusClass(row.current_status || row.status)}">${row.availability || segmentLabel(row.opportunity_segment)}</span>
        </div>
        <h2>${row.event_title_cn || marketTitle(row.title)}</h2>
        <div class="focus-metrics">
          <div><span>结构</span><strong>${row.structure_cn || "待确认"}</strong></div>
          <div><span>价格</span><strong>${row.price || "--"}</strong></div>
          <div><span>回报率</span><strong>${row.return_rate || "待定"}</strong></div>
        </div>
        <p>${row.strategy_summary || analysisText(row)}</p>
        ${row.affiliate_url ? `<a class="market-link" href="${row.affiliate_url}" target="_blank" rel="noreferrer">前往 Polymarket</a>` : ""}
      </article>
    `,
    )
    .join("") : '<article class="focus-card"><h2>今日比赛策略待准入</h2><p>暂无通过准入的每日关注事件。先空着，等规则和人工准入记录补齐后再展示。</p></article>';
}

function renderMatches() {
  const rows = todayMatches();
  document.getElementById("today-match-list").innerHTML = rows.length ? rows
    .map(
      (row) => `
      <article class="match-row">
        <div>
          <span class="badge active">今日 · ${stageLabel(row.stage)}${row.group ? ` · ${row.group}组` : ""}</span>
          <h3>${zh(row.home_team)} 对阵 ${zh(row.away_team)}</h3>
          <p>北京时间 ${formatChinaKickoff(row)} · ${matchRuntimeStatus(row)} · 关注级别 ${row.priority || "待评估"}</p>
        </div>
        <div class="priority ${String(row.priority || "").toLowerCase()}">${row.priority || "待评估"}</div>
      </article>
    `,
    )
    .join("") : '<article class="match-row"><div><h3>今日暂无比赛</h3><p>北京时间口径下没有匹配到今日比赛。</p></div></article>';
}

function render() {
  renderManual();
  renderRefreshStatus();
  renderMatches();
}

async function main() {
  [state.opportunities, state.events, state.rankings, state.matches, state.glossary, state.apiManual, state.publishedManual, state.refresh] = await Promise.all([
    loadCsv(paths.opportunities),
    loadCsv(paths.events),
    loadCsv(paths.rankings),
    loadCsv(paths.matches),
    loadCsv(paths.glossary),
    loadApiManual(),
    loadJson(paths.manual),
    loadJson(paths.refresh),
  ]);
  buildGlossary();
  loadManual();
  render();
}

main().catch((error) => {
  document.querySelector("main").innerHTML = `<section class="panel">数据加载失败：${error.message}</section>`;
});
