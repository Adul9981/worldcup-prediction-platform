const STORE_KEY = "worldcup:manual_recommendations:v1";
const MAX_ITEMS = 8;

function json(response, status = 200) {
  return { status, response };
}

function storageConfig() {
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "";
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";
  return { url: url.replace(/\/$/, ""), token };
}

function cleanItems(value) {
  return (Array.isArray(value) ? value : [])
    .filter((item) => item && item.status !== "draft")
    .map((item, index) => {
      const title = String(item.title || "").trim();
      const analysis = String(item.analysis || "").trim();
      return {
        id: String(item.id || `manual-${Date.now()}-${index}`),
        created_at: String(item.created_at || new Date().toISOString()),
        date: String(item.date || new Date().toISOString().slice(0, 10)),
        title: title || analysis.split(/\r?\n/).find(Boolean) || "今日推荐策略",
        direction: String(item.direction || "重点推荐"),
        analysis,
        url: String(item.url || ""),
        status: String(item.status || "active"),
      };
    })
    .filter((item) => item.title || item.analysis)
    .slice(0, MAX_ITEMS);
}

async function redisCommand(command) {
  const { url, token } = storageConfig();
  if (!url || !token) {
    const error = new Error("KV storage is not configured.");
    error.code = "NO_STORAGE";
    throw error;
  }
  const response = await fetch(`${url}/pipeline`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body: JSON.stringify([command]),
  });
  if (!response.ok) {
    throw new Error(`KV request failed: ${response.status}`);
  }
  const payload = await response.json();
  const first = Array.isArray(payload) ? payload[0] : null;
  if (first && first.error) throw new Error(first.error);
  return first ? first.result : null;
}

async function readItems() {
  const raw = await redisCommand(["GET", STORE_KEY]);
  if (!raw) return [];
  if (Array.isArray(raw)) return cleanItems(raw);
  return cleanItems(JSON.parse(raw));
}

async function writeItems(items) {
  const cleaned = cleanItems(items);
  await redisCommand(["SET", STORE_KEY, JSON.stringify(cleaned)]);
  return cleaned;
}

function authorized(request) {
  const expected = process.env.ADMIN_TOKEN || "";
  if (!expected) return false;
  return request.headers["x-admin-token"] === expected;
}

async function handler(request, response) {
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.setHeader("cache-control", "no-store");

  async function send(payload) {
    const result = await payload;
    response.status(result.status).send(JSON.stringify(result.response));
  }

  if (request.method === "GET") {
    try {
      const items = await readItems();
      return send(json({ ok: true, source: "kv", items }));
    } catch (error) {
      const status = error.code === "NO_STORAGE" ? 503 : 500;
      return send(json({ ok: false, source: "api", items: [], error: error.message }, status));
    }
  }

  if (request.method === "POST") {
    if (!authorized(request)) {
      return send(json({ ok: false, error: "Unauthorized" }, 401));
    }
    try {
      const payload = request.body || {};
      const items = await writeItems(payload.items);
      return send(json({ ok: true, source: "kv", items }));
    } catch (error) {
      const status = error.code === "NO_STORAGE" ? 503 : 500;
      return send(json({ ok: false, error: error.message }, status));
    }
  }

  return send(json({ ok: false, error: "Method not allowed" }, 405));
}

module.exports = handler;
