const paths = {
  rankings: "/data/polymarket/latest_daily_event_rankings.csv",
  topics: "/data/polymarket/latest_prediction_market_topics.csv",
  opportunities: "/data/polymarket/latest_market_opportunities.csv",
  changes: "/data/polymarket/latest_topic_changes.csv",
  scheduleLinks: "/data/polymarket/latest_market_schedule_links.csv",
  matches: "/data/templates/matches.csv",
  groups: "/data/templates/groups.csv",
  teams: "/data/templates/teams.csv",
  glossary: "/data/templates/glossary_cn_en.csv",
  refresh: "/data/polymarket/latest_refresh_status.json",
};

const labels = {
  most_watched: "最值得关注",
  most_ignored: "最被忽视",
  best_risk_reward: "最大盈亏比",
};

let state = {
  filter: "all",
  query: "",
  rankings: [],
  topics: [],
  opportunities: [],
  changes: [],
  scheduleLinks: [],
  matches: [],
  groups: [],
  teams: [],
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
  }[value] || zhText(value);
}

function buildGlossary() {
  state.zhMap = new Map(state.glossary.map((row) => [row.en, row.zh]));
}

function zh(value) {
  if (!value) return "";
  return state.zhMap.get(value) || value;
}

function zhText(value) {
  let text = value || "";
  if (text === "Model direction is YES; price, risk and score passed current rules.") {
    return "模型方向为买 YES；价格、风险和评分通过当前规则。";
  }
  const avoid = text.match(/^Avoid: status\/risk rules block entry for (.+)\.$/);
  if (avoid) return `回避：状态或风险规则阻止进入，选题为${marketTitle(avoid[1])}。`;
  const entries = [...state.zhMap.entries()].sort((a, b) => b[0].length - a[0].length);
  for (const [en, cn] of entries) {
    if (!en) continue;
    text = text.replaceAll(en, cn);
  }
  text = text
    .replace(/^是否\s+(.+?)\?$/, "是否$1？")
    .replace(/^是否\s+(.+)$/, "是否$1")
    .replaceAll("?", "？")
    .replaceAll(";", "；")
    .replaceAll(" vs ", " 对阵 ")
    .replaceAll("YES", "买 YES")
    .replaceAll("WAIT", "等待")
    .replaceAll("AVOID", "回避")
    .replaceAll("Model direction is", "模型方向为")
    .replaceAll("模型方向为买 YES； price, risk and score passed current rules.", "模型方向为买 YES；价格、风险和评分通过当前规则。")
    .replaceAll("No current edge signal; keep it in the watch pool.", "当前没有明确优势信号，保留在观察池。")
    .replaceAll("Conservative profile is visible; wait for price or thesis confirmation before entry.", "存在稳健观察特征，等待价格或交易理由确认。")
    .replaceAll("Upside profile is visible; wait for price, quota, or thesis confirmation before entry.", "存在高盈亏比观察特征，等待价格或交易理由确认。")
    .replaceAll("Cancel if market closes, liquidity disappears, or thesis cannot be written in one sentence.", "若市场关闭、流动性消失，或无法用一句话说明理由，则取消。")
    .replaceAll("neg_risk_unknown", "负风险字段待确认")
    .replaceAll("medium", "中等")
    .replaceAll("low", "低")
    .replaceAll("high", "高");
  return text;
}

function stageLabel(stage) {
  return {
    Group: "小组赛",
    "Round of 32": "32 强",
    "Round of 16": "16 强",
    Quarterfinal: "8 强",
    Semifinal: "半决赛",
    Final: "决赛",
  }[stage] || stage || "待赛";
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function formatDateTime(value) {
  if (!value) return "未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function renderRefreshStatus() {
  const root = document.getElementById("refresh-status");
  if (!root) return;
  const mode = state.refresh.fetched_from_polymarket ? "联网刷新" : "本地重建";
  const status = state.refresh.status === "ok" ? "正常" : "异常";
  root.textContent = `数据${status} · ${mode} · ${formatDateTime(state.refresh.updated_at)}`;
}

function renderMetrics() {
  const yesCount = state.opportunities.filter((row) => row.selection_direction === "YES").length;
  const structureCount = new Set(state.opportunities.map((row) => row.market_structure_type).filter(Boolean)).size;
  const volume24h = state.opportunities.reduce((sum, row) => sum + num(row.volume_24hr), 0);
  setText("metric-topics", String(state.topics.length || "--"));
  setText("metric-yes", String(yesCount || "0"));
  setText("metric-structure", String(structureCount || "--"));
  setText("metric-volume", fmtCompact(volume24h));
}

function statusClass(status) {
  if (status === "hot" || status === "active") return status;
  if (status === "excluded" || status === "closed" || status === "resolved") return "risk";
  return "watchlist";
}

function renderRankings() {
  const root = document.getElementById("rankings");
  const query = state.query.trim().toLowerCase();
  const rows = state.rankings.filter((row) => {
    const inFilter = state.filter === "all" || row.rank_type === state.filter;
    const haystack = `${row.event_title} ${row.current_status} ${row.recommendation_track} ${row.recommended_action}`.toLowerCase();
    return inFilter && (!query || haystack.includes(query));
  });
  if (!rows.length) {
    root.innerHTML = '<div class="ranking-card">没有匹配的事件。</div>';
    return;
  }
  root.innerHTML = rows
    .map(
      (row) => `
      <article class="ranking-card">
        <div class="card-top">
          <span class="badge ${statusClass(row.current_status)}">${labels[row.rank_type] || row.rank_type} #${row.rank}</span>
          <span class="track ${row.recommendation_track}">${zhText(row.recommended_action)}</span>
        </div>
        <div class="rank-title">${marketTitle(row.event_title)}</div>
        <div class="score-grid">
          <div><span>关注</span><strong>${fmt(row.attention_score)}</strong></div>
          <div><span>忽视</span><strong>${fmt(row.ignored_score)}</strong></div>
          <div><span>盈亏比</span><strong>${fmt(row.risk_reward_score)}</strong></div>
          <div><span>风险</span><strong>${fmt(row.risk_score)}</strong></div>
        </div>
        <div class="card-bottom">
          <p class="copy-angle">${rankingNote(row)}</p>
          <a class="market-link" href="${row.affiliate_url}" target="_blank" rel="noreferrer">前往 Polymarket</a>
        </div>
      </article>
    `,
    )
    .join("");
}

function renderOpportunities() {
  const root = document.getElementById("opportunity-grid");
  const rows = state.opportunities
    .filter((row) => row.selection_direction === "YES")
    .slice(0, 8);
  root.innerHTML = rows
    .map(
      (row) => `
      <article class="opportunity-card">
        <div class="card-top">
          <span class="track ${row.selection_direction.toLowerCase()}">${zh(row.selection_direction)}</span>
          <span class="badge active">${zh(row.direction_confidence)}</span>
        </div>
        <h3>${marketTitle(row.title)}</h3>
        <div class="op-meta">
          <span>${structureLabel(row.market_structure_type)}</span>
          <span>${zhText(row.neg_risk_status)}</span>
          <strong>${zh(row.direction_source)}</strong>
        </div>
        <p>${zhText(row.direction_thesis)}</p>
        <a class="market-link" href="${row.affiliate_url}" target="_blank" rel="noreferrer">前往 Polymarket</a>
      </article>
    `,
    )
    .join("");
}

function renderDailyBrief() {
  const hot = [...state.opportunities]
    .filter((row) => row.selection_direction !== "AVOID")
    .sort((a, b) => num(b.volume_24hr) - num(a.volume_24hr))
    .slice(0, 5);
  const highReturn = [...state.opportunities]
    .filter((row) => row.selection_direction === "WAIT" && returnRateValue(row.implied_yes_probability) >= 1000)
    .sort((a, b) => returnRateValue(b.implied_yes_probability) - returnRateValue(a.implied_yes_probability))
    .slice(0, 5);
  renderMarketMiniList("hot-volume-list", hot, (row) => `24h ${fmtCompact(row.volume_24hr)} · 流动性 ${fmtCompact(row.liquidity)}`);
  renderMarketMiniList("high-return-list", highReturn, (row) => `价格 ${fmt(row.implied_yes_probability, 4)} · 回报率 ${returnRate(row.implied_yes_probability)}`);
  const changeCounts = state.changes.reduce((map, row) => {
    const key = row.change_label || row.change_type || "变化";
    map[key] = (map[key] || 0) + 1;
    return map;
  }, {});
  const mapped = state.scheduleLinks.filter((row) => row.link_type === "team_group_stage").length;
  document.getElementById("today-status-list").innerHTML = [
    ["新增选题", String(changeCounts["新增选题"] || 0)],
    ["本次消失", String(changeCounts["本次消失"] || 0)],
    ["状态变化", String(changeCounts["状态变化"] || 0)],
    ["赛程映射", `${mapped}/${state.scheduleLinks.length || 0}`],
  ]
    .map(
      ([label, value]) => `
      <div class="side-row">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `,
    )
    .join("");
}

function renderMarketMiniList(id, rows, noteFor) {
  const root = document.getElementById(id);
  if (!rows.length) {
    root.innerHTML = '<div class="empty">暂无匹配选题。</div>';
    return;
  }
  root.innerHTML = rows
    .map(
      (row) => `
      <div class="team-row">
        <div>
          <strong>${marketTitle(row.title)}</strong>
          <span>${zh(row.selection_direction)} · ${segmentLabel(row.opportunity_segment)}</span>
        </div>
        <small>${noteFor(row)}</small>
      </div>
    `,
    )
    .join("");
}

function structureLabel(value) {
  return zh(value) || "结构待复核";
}

function marketTitle(title) {
  const mapped = zh(title);
  if (mapped !== title) return mapped;
  const winner = title.match(/^Will (.+) win the 2026 FIFA World Cup\?$/);
  if (winner) return `${zh(winner[1])}是否赢得2026年世界杯？`;
  return zhText(title);
}

function teamFromMarketTitle(title) {
  const winner = title.match(/^Will (.+) win the 2026 FIFA World Cup\?$/);
  return winner ? zh(winner[1]) : "";
}

function rankingNote(row) {
  const team = teamFromMarketTitle(row.event_title);
  if (row.rank_type === "most_watched") {
    return team ? `${team}是当前高关注市场，用来观察市场共识和价格锚点。` : "该选题关注度较高，适合作为市场温度参考。";
  }
  if (row.rank_type === "most_ignored") {
    return team ? `${team}可能存在关注度和定价之间的信息差，先观察再决定。` : "该选题可能存在信息差，但仍需等待更清晰的交易理由。";
  }
  if (row.rank_type === "best_risk_reward") {
    return team ? `${team}进入盈亏比观察区，必须同时检查风险和取消条件。` : "该选题进入盈亏比观察区，不能脱离风控单独判断。";
  }
  return zhText(row.cancel_condition);
}

function renderDirectionPanel() {
  const root = document.getElementById("direction-list");
  const counts = state.opportunities.reduce((map, row) => {
    const key = zh(row.selection_direction);
    map[key] = (map[key] || 0) + 1;
    return map;
  }, {});
  root.innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(
      ([label, count]) => `
      <div class="side-row">
        <span>${label}</span>
        <strong>${count}</strong>
      </div>
    `,
    )
    .join("");
}

function renderMatches() {
  const root = document.getElementById("match-list");
  if (!state.matches.length) {
    root.innerHTML = '<div class="empty">赛程库等待补充。</div>';
    return;
  }
  root.innerHTML = state.matches
    .slice(0, 5)
    .map(
      (row) => `
      <article class="match-row">
        <div>
          <span class="badge active">${stageLabel(row.stage)} ${row.group ? `· ${row.group}组` : ""}</span>
          <h3>${zh(row.home_team)} 对阵 ${zh(row.away_team)}</h3>
          <p>${row.date || "日期待补"} · ${row.venue || "场地待补"} · ${row.city || ""}</p>
        </div>
        <div class="priority ${String(row.priority || "").toLowerCase()}">${row.priority || "待评估"}</div>
      </article>
    `,
    )
    .join("");
}

function groupPriority(group) {
  const heat = String(group.attention_level || "");
  const volume = String(group.trade_volume_estimate || "");
  if (heat.includes("very") || volume.includes("very")) return 3;
  if (heat.includes("high") || volume.includes("high")) return 2;
  return 1;
}

function renderGroups() {
  const root = document.getElementById("group-list");
  const rows = [...state.groups]
    .sort((a, b) => groupPriority(b) - groupPriority(a))
    .slice(0, 6);
  root.innerHTML = rows
    .map(
      (row) => `
      <article class="group-row">
        <div class="group-code">${row.group_code}</div>
        <div>
          <h3>${zhText(row.key_story)}</h3>
          <p>${zhText(row.teams)}</p>
          <small>${zhText(row.primary_opportunities)}</small>
        </div>
        <span class="badge ${groupPriority(row) >= 3 ? "hot" : "active"}">${zhText(row.attention_level)}</span>
      </article>
    `,
    )
    .join("");
}

function renderTeamRadar() {
  const strong = state.teams
    .filter((row) => row.tier === "elite" || row.strong_team_level === "high")
    .slice(0, 8);
  const weak = state.teams
    .filter((row) => row.weak_team_level === "high")
    .slice(0, 8);
  const swing = state.teams
    .filter((row) => row.swing_level === "high")
    .slice(0, 8);
  renderTeamList("strong-team-list", strong, "strong");
  renderTeamList("weak-team-list", weak, "weak");
  renderTeamList("swing-team-list", swing, "swing");
}

function renderTeamList(id, rows, type) {
  const root = document.getElementById(id);
  root.innerHTML = rows
    .map(
      (row) => `
      <div class="team-row">
        <div>
          <strong>${zh(row.team)}</strong>
          <span>${row.group_code}组 · ${zh(row.likely_role)}</span>
        </div>
        <small>${zhText(teamAngle(row, type))}</small>
      </div>
    `,
    )
    .join("");
}

function teamAngle(row, type) {
  if (type === "strong") return row.primary_opportunities || "强队胜负与出线盘";
  if (type === "weak") return row.primary_opportunities || "对手让球、进球数、牌角球";
  return row.primary_opportunities || "小组第二/第三、低比分、平局";
}

function renderStatusPanel() {
  const root = document.getElementById("status-list");
  const counts = state.topics.reduce((map, row) => {
    const key = row.current_status || "unknown";
    map[key] = (map[key] || 0) + 1;
    return map;
  }, {});
  root.innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(
      ([status, count]) => `
      <div class="side-row">
        <span class="badge ${statusClass(status)}">${zh(status)}</span>
        <strong>${count}</strong>
      </div>
    `,
    )
    .join("");
}

function renderStructurePanel() {
  const root = document.getElementById("structure-list");
  const counts = state.opportunities.reduce((map, row) => {
    const key = structureLabel(row.market_structure_type);
    map[key] = (map[key] || 0) + 1;
    return map;
  }, {});
  root.innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(
      ([label, count]) => `
      <div class="side-row">
        <span>${label}</span>
        <strong>${count}</strong>
      </div>
    `,
    )
    .join("");
}

function render() {
  renderRefreshStatus();
  renderMetrics();
  renderDailyBrief();
  renderOpportunities();
  renderMatches();
  renderGroups();
  renderTeamRadar();
  renderRankings();
  renderDirectionPanel();
  renderStatusPanel();
  renderStructurePanel();
}

async function main() {
  [state.rankings, state.topics, state.opportunities, state.changes, state.scheduleLinks, state.matches, state.groups, state.teams, state.glossary, state.refresh] = await Promise.all([
    loadCsv(paths.rankings),
    loadCsv(paths.topics),
    loadCsv(paths.opportunities),
    loadCsv(paths.changes),
    loadCsv(paths.scheduleLinks),
    loadCsv(paths.matches),
    loadCsv(paths.groups),
    loadCsv(paths.teams),
    loadCsv(paths.glossary),
    loadJson(paths.refresh),
  ]);
  buildGlossary();
  render();
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    button.classList.add("active");
    state.filter = button.dataset.filter;
    renderRankings();
  });
});

document.getElementById("search-input").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderRankings();
});

main().catch((error) => {
  document.getElementById("rankings").innerHTML = `<div class="ranking-card">数据加载失败：${error.message}</div>`;
});
