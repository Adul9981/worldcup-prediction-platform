const paths = {
  opportunities: "/data/polymarket/latest_market_opportunities.csv",
  glossary: "/data/templates/glossary_cn_en.csv",
  refresh: "/data/polymarket/latest_refresh_status.json",
};

let state = {
  direction: "all",
  structure: "all",
  status: "all",
  opportunity: "all",
  sortMode: "direction",
  query: "",
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

function buildGlossary() {
  state.zhMap = new Map(state.glossary.map((row) => [row.en, row.zh]));
}

function zh(value) {
  return state.zhMap.get(value) || value || "";
}

function num(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function fmt(value, digits = 2) {
  return num(value).toFixed(digits).replace(/\.00$/, "");
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

function fmtCompact(value) {
  const number = num(value);
  if (number >= 100000000) return `${fmt(number / 100000000, 2)}亿`;
  if (number >= 10000) return `${fmt(number / 10000, 1)}万`;
  if (number >= 1000) return `${fmt(number / 1000, 1)}千`;
  return fmt(number, 0);
}

function returnRate(value) {
  const price = num(value);
  if (price <= 0 || price >= 1) return price === 1 ? "0%" : "--";
  const rate = (1 / price - 1) * 100;
  if (rate >= 1000) return `${fmt(rate, 0)}%`;
  return `${fmt(rate, 1)}%`;
}

function returnRateValue(value) {
  const price = num(value);
  if (price <= 0 || price >= 1) return 0;
  return (1 / price - 1) * 100;
}

function marketTitle(title) {
  const mapped = zh(title);
  if (mapped !== title) return mapped;
  const winner = title.match(/^Will (.+) win the 2026 FIFA World Cup\?$/);
  if (winner) return `${zh(winner[1])}是否赢得2026年世界杯？`;
  return title.replaceAll("?", "？");
}

function eventGroupTitle(slug, rows) {
  if (slug === "world-cup-winner") return "2026世界杯冠军";
  const first = rows[0];
  return first ? marketTitle(first.title) : slug;
}

function structureLabel(value) {
  return zh(value) || "结构待复核";
}

function statusLabel(value) {
  return zh(value) || value || "未知";
}

function directionLabel(value) {
  return zh(value) || value || "等待";
}

function opportunityKind(row) {
  if (row.selection_direction === "YES") return "buy_direction";
  if (row.selection_direction === "AVOID") return "risk_avoid";
  if (row.market_structure_type === "special_event_binary") return "special_event";
  if (row.recommendation_track === "upside" && returnRateValue(row.implied_yes_probability) >= 1000) {
    return "high_return_watch";
  }
  return "normal_watch";
}

function opportunitySegment(row) {
  return row.opportunity_segment || opportunityKind(row);
}

function opportunityLabel(row) {
  return segmentLabel(opportunitySegment(row)) || {
    buy_direction: "买入方向",
    high_return_watch: "高回报观察",
    special_event: "特殊事件",
    risk_avoid: "风险回避",
    normal_watch: "普通观察",
  }[opportunityKind(row)] || "普通观察";
}

function opportunityClass(row) {
  const segment = opportunitySegment(row);
  if (segment === "risk_avoid") return "excluded";
  if (segment === "strong_team" || segment === "buy_direction") return "yes";
  if (segment === "weak_team_related" || segment === "swing_team") return "upside";
  if (segment === "overheat_risk") return "excluded";
  return {
    buy_direction: "yes",
    high_return_watch: "upside",
    special_event: "watchlist",
    risk_avoid: "excluded",
    normal_watch: "neutral",
  }[opportunityKind(row)] || "neutral";
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
  }[value] || "";
}

const opportunitySummary = [
  ["strong_team", "明显强队", "冠军盘核心"],
  ["weak_team_related", "弱队相关", "低价高波动"],
  ["swing_team", "摇摆队", "出线分歧"],
  ["mutual_group_high_price_anchor", "互斥组锚点", "组内价格锚"],
  ["high_return_watch", "高回报观察", "等待确认"],
  ["risk_avoid", "风险回避", "暂不参与"],
];

function analysisText(row) {
  if (row.selection_direction === "YES") {
    return "模型方向为买 YES；价格、风险和评分通过当前规则。";
  }
  if (row.selection_direction === "AVOID") {
    return "状态或风险规则不合格，当前回避。";
  }
  if (row.recommendation_track === "upside") {
    return "存在高盈亏比观察特征，等待价格或理由确认。";
  }
  return "当前没有明确优势信号，保留观察。";
}

function heatLabel(row) {
  const volume24h = num(row.volume_24hr);
  const liquidity = num(row.liquidity);
  if (volume24h >= 1000000 || liquidity >= 1000000) return "高热度";
  if (volume24h >= 100000 || liquidity >= 100000) return "升温中";
  if (volume24h === 0 && liquidity === 0) return "待成交";
  return "低量观察";
}

function directionRank(value) {
  return { YES: 0, WAIT: 1, AVOID: 2 }[value] ?? 3;
}

function statusRank(value) {
  return { hot: 0, active: 1, watchlist: 2, neutral: 3, excluded: 4, closed: 5, resolved: 6 }[value] ?? 7;
}

function renderMetrics() {
  const yes = state.opportunities.filter((row) => row.selection_direction === "YES").length;
  const wait = state.opportunities.filter((row) => row.selection_direction === "WAIT").length;
  const avoid = state.opportunities.filter((row) => row.selection_direction === "AVOID").length;
  document.getElementById("market-total").textContent = String(state.opportunities.length);
  document.getElementById("market-yes").textContent = String(yes);
  document.getElementById("market-wait").textContent = String(wait);
  document.getElementById("market-avoid").textContent = String(avoid);
}

function renderFilterOptions() {
  const structureSelect = document.getElementById("structure-filter");
  const statusSelect = document.getElementById("status-filter");
  const opportunitySelect = document.getElementById("opportunity-filter");
  const structures = [...new Set(state.opportunities.map((row) => row.market_structure_type).filter(Boolean))]
    .sort((a, b) => structureLabel(a).localeCompare(structureLabel(b), "zh-CN"));
  const statuses = [...new Set(state.opportunities.map((row) => row.current_status).filter(Boolean))]
    .sort((a, b) => statusLabel(a).localeCompare(statusLabel(b), "zh-CN"));
  const segments = [...new Set(state.opportunities.map(opportunitySegment).filter(Boolean))]
    .sort((a, b) => (segmentLabel(a) || a).localeCompare(segmentLabel(b) || b, "zh-CN"));

  structureSelect.innerHTML = [
    '<option value="all">全部结构</option>',
    ...structures.map((value) => `<option value="${value}">${structureLabel(value)}</option>`),
  ].join("");
  statusSelect.innerHTML = [
    '<option value="all">全部状态</option>',
    ...statuses.map((value) => `<option value="${value}">${statusLabel(value)}</option>`),
  ].join("");
  opportunitySelect.innerHTML = [
    '<option value="all">全部机会</option>',
    ...segments.map((value) => `<option value="${value}">${segmentLabel(value) || value}</option>`),
  ].join("");
  opportunitySelect.value = segments.includes(state.opportunity) ? state.opportunity : "all";
  if (opportunitySelect.value !== state.opportunity) state.opportunity = "all";
}

function renderOpportunitySummary() {
  const root = document.getElementById("opportunity-summary");
  const counts = state.opportunities.reduce((acc, row) => {
    const key = opportunitySegment(row);
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  root.innerHTML = opportunitySummary
    .map(
      ([key, label, note]) => `
      <button class="summary-tile ${state.opportunity === key ? "active" : ""}" data-opportunity-quick="${key}">
        <span>${label}</span>
        <strong>${counts[key] || 0}</strong>
        <small>${note}</small>
      </button>
    `,
    )
    .join("");
}

function topBy(kind, sorter) {
  return state.opportunities
    .filter((row) => opportunitySegment(row) === kind)
    .sort(sorter)[0];
}

function focusCards() {
  return [
    [
      "明显强队",
      topBy(
        "strong_team",
        (a, b) =>
          statusRank(a.current_status) - statusRank(b.current_status) ||
          returnRateValue(b.implied_yes_probability) - returnRateValue(a.implied_yes_probability),
      ),
    ],
    [
      "高回报观察",
      topBy(
        "high_return_watch",
        (a, b) => returnRateValue(b.implied_yes_probability) - returnRateValue(a.implied_yes_probability),
      ),
    ],
    [
      "摇摆队",
      topBy(
        "swing_team",
        (a, b) => returnRateValue(b.implied_yes_probability) - returnRateValue(a.implied_yes_probability),
      ),
    ],
  ].filter(([, row]) => row);
}

function renderFocusOpportunities() {
  const root = document.getElementById("focus-opportunities");
  const cards = focusCards();
  if (!cards.length) {
    root.innerHTML = "";
    return;
  }
  root.innerHTML = cards
    .map(
      ([label, row]) => `
      <article class="focus-card">
        <div class="card-top">
          <span class="track ${opportunityClass(row)}">${label}</span>
          <span class="badge ${statusClass(row.current_status)}">${statusLabel(row.current_status)}</span>
        </div>
        <h2>${marketTitle(row.title)}</h2>
        <div class="focus-metrics">
          <div><span>方向</span><strong>${directionLabel(row.selection_direction)}</strong></div>
          <div><span>价格</span><strong>${fmt(row.implied_yes_probability, 4)}</strong></div>
          <div><span>24h量</span><strong>${fmtCompact(row.volume_24hr)}</strong></div>
        </div>
        <div class="focus-metrics two">
          <div><span>回报率</span><strong>${returnRate(row.implied_yes_probability)}</strong></div>
          <div><span>流动性</span><strong>${fmtCompact(row.liquidity)}</strong></div>
        </div>
        <p>${analysisText(row)}</p>
        <a class="market-link" href="${row.affiliate_url}" target="_blank" rel="noreferrer">前往 Polymarket</a>
      </article>
    `,
    )
    .join("");
}

function renderEventGroups() {
  const root = document.getElementById("event-groups");
  const groups = new Map();
  for (const row of state.opportunities) {
    const key = row.event_slug || row.topic_id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  const rows = [...groups.entries()]
    .map(([slug, items]) => {
      const totalPrice = items.reduce((sum, row) => sum + num(row.implied_yes_probability), 0);
      const totalVolume24h = items.reduce((sum, row) => sum + num(row.volume_24hr), 0);
      const totalLiquidity = items.reduce((sum, row) => sum + num(row.liquidity), 0);
      const yesCount = items.filter((row) => row.selection_direction === "YES").length;
      const avoidCount = items.filter((row) => row.selection_direction === "AVOID").length;
      const nonAvoid = items.filter((row) => row.selection_direction !== "AVOID");
      const anchorPool = nonAvoid.length ? nonAvoid : items;
      const anchor = [...anchorPool].sort((a, b) => num(b.implied_yes_probability) - num(a.implied_yes_probability))[0];
      return {
        slug,
        items,
        totalPrice,
        totalVolume24h,
        totalLiquidity,
        yesCount,
        avoidCount,
        anchor,
        structure: structureLabel(items[0]?.market_structure_type || ""),
      };
    })
    .sort((a, b) => b.items.length - a.items.length || b.totalPrice - a.totalPrice);

  root.innerHTML = [
    '<div class="section-head compact"><h2>事件组概览</h2><p>互斥市场必须按组一起看。</p></div>',
    '<div class="group-strip">',
    ...rows.map(
      (group) => `
      <article class="group-card">
        <div class="card-top">
          <span class="track watchlist">${group.structure}</span>
          <span class="badge active">${group.items.length} 个选题</span>
        </div>
        <h2>${eventGroupTitle(group.slug, group.items)}</h2>
        <div class="focus-metrics">
          <div><span>总价格</span><strong>${fmt(group.totalPrice, 3)}</strong></div>
          <div><span>24h量</span><strong>${fmtCompact(group.totalVolume24h)}</strong></div>
          <div><span>流动性</span><strong>${fmtCompact(group.totalLiquidity)}</strong></div>
        </div>
        <div class="focus-metrics two">
          <div><span>买入方向</span><strong>${group.yesCount}</strong></div>
          <div><span>风险回避</span><strong>${group.avoidCount}</strong></div>
        </div>
        <p>组内最高非回避价格：${marketTitle(group.anchor.title)}，价格 ${fmt(group.anchor.implied_yes_probability, 4)}。</p>
      </article>
    `,
    ),
    "</div>",
  ].join("");
}

function filteredRows() {
  const query = state.query.trim().toLowerCase();
  const rows = state.opportunities.filter((row) => {
    const inDirection = state.direction === "all" || row.selection_direction === state.direction;
    const inStructure = state.structure === "all" || row.market_structure_type === state.structure;
    const inStatus = state.status === "all" || row.current_status === state.status;
    const inOpportunity = state.opportunity === "all" || opportunitySegment(row) === state.opportunity;
    const text = [
      marketTitle(row.title),
      directionLabel(row.selection_direction),
      structureLabel(row.market_structure_type),
      statusLabel(row.current_status),
      opportunityLabel(row),
      row.recommendation_track,
      row.title,
    ]
      .join(" ")
      .toLowerCase();
    return inDirection && inStructure && inStatus && inOpportunity && (!query || text.includes(query));
  });
  return rows.sort((a, b) => {
    if (state.sortMode === "return_desc") {
      return returnRateValue(b.implied_yes_probability) - returnRateValue(a.implied_yes_probability);
    }
    if (state.sortMode === "price_asc") {
      return num(a.implied_yes_probability) - num(b.implied_yes_probability);
    }
    if (state.sortMode === "price_desc") {
      return num(b.implied_yes_probability) - num(a.implied_yes_probability);
    }
    return (
      directionRank(a.selection_direction) - directionRank(b.selection_direction) ||
      statusRank(a.current_status) - statusRank(b.current_status) ||
      returnRateValue(b.implied_yes_probability) - returnRateValue(a.implied_yes_probability)
    );
  });
}

function renderTable() {
  const rows = filteredRows();
  const root = document.getElementById("market-table-body");
  renderOpportunitySummary();
  document.getElementById("visible-count").textContent = `当前显示 ${rows.length} 个选题`;
  if (!rows.length) {
    root.innerHTML = '<tr><td colspan="10">没有匹配的选题。</td></tr>';
    return;
  }
  root.innerHTML = rows
    .map(
      (row) => `
      <tr>
        <td>
          <strong>${marketTitle(row.title)}</strong>
          <small>${row.neg_risk_status === "neg_risk_unknown" ? "负风险字段待确认" : row.neg_risk_status}</small>
        </td>
        <td><span class="track ${row.selection_direction.toLowerCase()}">${directionLabel(row.selection_direction)}</span></td>
        <td>${structureLabel(row.market_structure_type)}</td>
        <td><span class="badge ${statusClass(row.current_status)}">${statusLabel(row.current_status)}</span></td>
        <td class="price-cell">
          <strong>${fmt(row.implied_yes_probability, 4)}</strong>
          <small>回报率 ${returnRate(row.implied_yes_probability)}</small>
        </td>
        <td>
          <strong>${heatLabel(row)}</strong>
          <small>24h ${fmtCompact(row.volume_24hr)} / 流动性 ${fmtCompact(row.liquidity)}</small>
        </td>
        <td><span class="track ${opportunityClass(row)}">${opportunityLabel(row)}</span></td>
        <td>
          <strong>${row.schedule_stage || "赛程待映射"}</strong>
          <small>${row.group_code ? `${zh(row.canonical_team)} · ${row.group_code}组` : "无单场绑定"}</small>
        </td>
        <td>${analysisText(row)}</td>
        <td><a class="market-link" href="${row.affiliate_url}" target="_blank" rel="noreferrer">前往 Polymarket</a></td>
      </tr>
    `,
    )
    .join("");
}

function statusClass(status) {
  if (status === "hot" || status === "active") return status;
  if (status === "excluded" || status === "closed" || status === "resolved") return "risk";
  return "watchlist";
}

function render() {
  renderRefreshStatus();
  renderMetrics();
  renderFilterOptions();
  renderOpportunitySummary();
  renderFocusOpportunities();
  renderEventGroups();
  renderTable();
}

async function main() {
  [state.opportunities, state.glossary, state.refresh] = await Promise.all([
    loadCsv(paths.opportunities),
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
    state.direction = button.dataset.direction;
    renderTable();
  });
});

document.getElementById("market-search").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderTable();
});

document.getElementById("structure-filter").addEventListener("change", (event) => {
  state.structure = event.target.value;
  renderTable();
});

document.getElementById("status-filter").addEventListener("change", (event) => {
  state.status = event.target.value;
  renderTable();
});

document.getElementById("opportunity-filter").addEventListener("change", (event) => {
  state.opportunity = event.target.value;
  renderTable();
});

document.getElementById("opportunity-summary").addEventListener("click", (event) => {
  const button = event.target.closest("[data-opportunity-quick]");
  if (!button) return;
  state.opportunity = button.dataset.opportunityQuick;
  document.getElementById("opportunity-filter").value = state.opportunity;
  renderTable();
});

document.getElementById("sort-mode").addEventListener("change", (event) => {
  state.sortMode = event.target.value;
  renderTable();
});

main().catch((error) => {
  document.getElementById("market-table-body").innerHTML = `<tr><td colspan="10">数据加载失败：${error.message}</td></tr>`;
});
