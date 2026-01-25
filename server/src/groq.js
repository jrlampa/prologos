const GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions";

export async function groqChatCompletion({
  apiKey,
  model,
  messages,
  temperature = 0.3,
  timeoutMs = 120000,
}) {
  if (!apiKey) {
    const err = new Error("GROQ_API_KEY não configurada.");
    err.statusCode = 500;
    throw err;
  }
  if (!model) {
    const err = new Error("Modelo Groq não informado.");
    err.statusCode = 500;
    throw err;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(GROQ_CHAT_COMPLETIONS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages,
        temperature,
      }),
      signal: controller.signal,
    });

    const text = await res.text();
    let json;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = null;
    }

    if (!res.ok) {
      const msg =
        json?.error?.message ||
        `Erro Groq (${res.status}): resposta inválida do provedor.`;
      const err = new Error(msg);
      err.statusCode = 502;
      err.providerStatus = res.status;
      err.providerBody = json ?? text;
      throw err;
    }

    const content = json?.choices?.[0]?.message?.content;
    if (!content) {
      const err = new Error("Resposta Groq sem conteúdo.");
      err.statusCode = 502;
      err.providerBody = json ?? text;
      throw err;
    }

    return { content, raw: json };
  } finally {
    clearTimeout(timeout);
  }
}

