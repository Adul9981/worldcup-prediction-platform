async function handler(request, response) {
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.setHeader("cache-control", "no-store");

  if (request.method !== "POST") {
    return response.status(405).send(JSON.stringify({ ok: false, error: "Method not allowed" }));
  }

  const expected = (process.env.ACCESS_CODE || "").trim();
  if (!expected) {
    return response.status(503).send(JSON.stringify({ ok: false, error: "Access code not configured" }));
  }

  const body = request.body || {};
  const code = String(body.code || "").trim();
  const valid = code.length > 0 && code === expected;

  return response.status(200).send(JSON.stringify({ ok: valid }));
}

module.exports = handler;
