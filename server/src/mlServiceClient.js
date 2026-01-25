const ML_SERVICE_URL = (process.env.ML_SERVICE_URL || "http://127.0.0.1:9000").replace(
  /\/+$/,
  ""
);

const DEFAULT_TIMEOUT_MS = Number(process.env.ML_SERVICE_TIMEOUT_MS || 30_000);

function withTimeout(signal, timeoutMs) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  return { signal: controller.signal, clear: () => clearTimeout(timeout) };
}

async function postJson(path, body, { timeoutMs = DEFAULT_TIMEOUT_MS, signal } = {}) {
  const url = `${ML_SERVICE_URL}${path}`;
  const t = withTimeout(signal, timeoutMs);

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: t.signal,
    });

    const text = await res.text();
    if (!res.ok) {
      throw new Error(`ml_service ${res.status} em ${path}: ${text}`);
    }

    return text ? JSON.parse(text) : null;
  } finally {
    t.clear();
  }
}

async function getJson(path, { timeoutMs = DEFAULT_TIMEOUT_MS, signal } = {}) {
  const url = `${ML_SERVICE_URL}${path}`;
  const t = withTimeout(signal, timeoutMs);

  try {
    const res = await fetch(url, { method: "GET", signal: t.signal });
    const text = await res.text();
    if (!res.ok) {
      throw new Error(`ml_service ${res.status} em ${path}: ${text}`);
    }
    return text ? JSON.parse(text) : null;
  } finally {
    t.clear();
  }
}

export async function mlHealth(opts) {
  return await getJson("/health", opts);
}

export async function embedText({ text, normalize }, opts) {
  return await postJson("/ml/embed", { text, normalize }, opts);
}

export async function rankCandidates({ queryText, candidates, topK, normalize }, opts) {
  return await postJson(
    "/ml/rank",
    { queryText, candidates, topK, normalize },
    opts
  );
}

