const { put, head } = require('@vercel/blob');

const BLOB_PATH = 'worldcup-manual-recommendations.json';
const MAX_ITEMS = 8;

function json(response, status = 200) {
  return { status, response };
}

function cleanItems(value) {
  return (Array.isArray(value) ? value : [])
    .filter((item) => item && item.status !== 'draft')
    .map((item, index) => {
      const title = String(item.title || '').trim();
      const analysis = String(item.analysis || '').trim();
      return {
        id: String(item.id || `manual-${Date.now()}-${index}`),
        created_at: String(item.created_at || new Date().toISOString()),
        date: String(item.date || new Date().toISOString().slice(0, 10)),
        title: title || analysis.split(/\r?\n/).find(Boolean) || '今日推荐策略',
        direction: String(item.direction || '重点推荐'),
        analysis,
        url: String(item.url || ''),
        status: String(item.status || 'active'),
      };
    })
    .filter((item) => item.title || item.analysis)
    .slice(0, MAX_ITEMS);
}

async function readItems() {
  try {
    const blobInfo = await head(BLOB_PATH);
    const res = await fetch(blobInfo.downloadUrl);
    if (!res.ok) return [];
    const raw = await res.json();
    return cleanItems(Array.isArray(raw) ? raw : []);
  } catch {
    return [];
  }
}

async function writeItems(items) {
  const cleaned = cleanItems(items);
  await put(BLOB_PATH, JSON.stringify(cleaned), {
    contentType: 'application/json',
    addRandomSuffix: false,
    access: 'public',
  });
  return cleaned;
}

function authorized(request) {
  const expected = process.env.ADMIN_TOKEN || '';
  if (!expected) return false;
  return request.headers['x-admin-token'] === expected;
}

async function handler(request, response) {
  response.setHeader('content-type', 'application/json; charset=utf-8');
  response.setHeader('cache-control', 'no-store');

  async function send(payload) {
    const result = await payload;
    response.status(result.status).send(JSON.stringify(result.response));
  }

  if (request.method === 'GET') {
    try {
      const items = await readItems();
      return send(json({ ok: true, source: 'blob', items }));
    } catch (error) {
      return send(json({ ok: false, source: 'api', items: [], error: error.message }, 500));
    }
  }

  if (request.method === 'POST') {
    if (!authorized(request)) {
      return send(json({ ok: false, error: 'Unauthorized' }, 401));
    }
    try {
      const payload = request.body || {};
      const items = await writeItems(payload.items);
      return send(json({ ok: true, source: 'blob', items }));
    } catch (error) {
      return send(json({ ok: false, error: error.message }, 500));
    }
  }

  return send(json({ ok: false, error: 'Method not allowed' }, 405));
}

module.exports = handler;
