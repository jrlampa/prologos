import express from "express";
import cors from "cors";
import multer from "multer";
import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { openSqlite, getJuizes, getJuizStats, getJuizContextForDossie } from "./db.js";
import { groqChatCompletion } from "./groq.js";
import { extractPdfText } from "./pdf.js";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = Number(process.env.PORT || 3001);
const SQLITE_PATH =
  process.env.SQLITE_PATH ||
  path.resolve(__dirname, "..", "..", "backend", "prologos_mvp.db");
const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";
const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL || "http://127.0.0.1:8000";

const db = openSqlite(SQLITE_PATH);

const app = express();
app.use(cors({ origin: true, credentials: true }));
app.use(express.json({ limit: "2mb" }));

const upload = multer({ storage: multer.memoryStorage() });

function toInt(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : NaN;
}

function requireJuizId(req) {
  const juizId = toInt(req.params.juizId ?? req.query.juiz_id);
  if (!Number.isFinite(juizId) || juizId <= 0) {
    const err = new Error("juiz_id inválido.");
    err.statusCode = 400;
    throw err;
  }
  return juizId;
}

app.get("/api/health", (req, res) => {
  res.json({
    ok: true,
    sqlitePath: SQLITE_PATH,
    fastapiBaseUrl: FASTAPI_BASE_URL,
  });
});

// Paridade mínima do frontend atual
app.get("/api/juizes", (req, res) => {
  res.json(getJuizes(db));
});

app.get("/api/juiz/:juizId/stats", (req, res) => {
  const juizId = requireJuizId(req);
  const stats = getJuizStats(db, juizId);
  if (!stats) return res.status(404).json({ detail: "Juiz não encontrado" });
  res.json(stats);
});

// Dossiê (migrado do Streamlit)
app.post("/api/juiz/:juizId/dossie", async (req, res, next) => {
  try {
    const juizId = requireJuizId(req);
    const ctx = getJuizContextForDossie(db, juizId, 50);
    if (!ctx) return res.status(404).json({ detail: "Juiz não encontrado" });

    const { juiz, decisoes } = ctx;
    if (!decisoes?.length) {
      return res.status(400).json({
        detail: "Base de decisões do juiz está vazia.",
      });
    }

    const listaTxt = decisoes
      .map((d) => `- Tema '${d.tema ?? "N/A"}', Risco: ${d.resultado ?? "N/A"}`)
      .join("\n");

    const prompt = `
ATUE COMO JURIMETRISTA. Crie um Perfil do juiz: ${juiz.nome}.

DADOS:
${listaTxt}

SAÍDA: Perfil comportamental, principais focos, tendência (rígido/garantista).
`.trim();

    const { content } = await groqChatCompletion({
      apiKey: GROQ_API_KEY,
      model: GROQ_MODEL,
      messages: [{ role: "user", content: prompt }],
      temperature: 0.4,
    });

    res.json({
      juizId,
      juizNome: juiz.nome,
      model: GROQ_MODEL,
      dossie: content,
    });
  } catch (e) {
    next(e);
  }
});

// Parecer estratégico (equivalente à Aba 2 do Streamlit) - Groq + PDF (+ dossiê opcional)
app.post(
  "/api/analise/peticao/parecer",
  upload.single("file"),
  async (req, res, next) => {
    try {
      const juizId = requireJuizId(req);
      const juiz = db
        .prepare("SELECT id, nome FROM juizes WHERE id = ?")
        .get(juizId);
      if (!juiz) return res.status(404).json({ detail: "Juiz não encontrado" });

      if (!req.file) {
        const err = new Error("Arquivo PDF (file) é obrigatório.");
        err.statusCode = 400;
        throw err;
      }

      const textoPeticao = await extractPdfText(req.file.buffer, { maxChars: 6000 });
      const dossie = (req.body?.dossie ?? "").toString().trim();
      const temaMatch = (req.body?.tema_match ?? "").toString().trim();

      const contextoExtra = dossie
        ? `
⚠️ INFORMAÇÃO PRIVILEGIADA (DOSSIÊ JÁ GERADO):
Abaixo está o perfil comportamental deste juiz, gerado previamente.
Use-o para refinar suas sugestões:
---
${dossie}
---
`.trim()
        : "";

      const prompt = `
Você é um Consultor Jurídico Especialista em Processo Civil Brasileiro, atuando como SIMULADOR DECISÓRIO.

CONTEXTO:
Juiz: ${juiz.nome}
Tema do Processo: ${temaMatch || "(não informado)"}

${contextoExtra}

INSTRUÇÕES:
1) LEITURA CRÍTICA DA PETIÇÃO (estrutura, clareza, pedidos, fundamentos, aderência ao perfil do juiz)
2) ANÁLISE SOB A ÓTICA DO JUIZ CLONADO
3) PROBABILIDADE ESTATÍSTICA DE DESFECHO (percentuais + justificativa)
4) FUNDAMENTAÇÃO PROVÁVEL (artigos, precedentes e teses)
5) SUGESTÕES PRÁTICAS (ações concretas de melhoria)
6) ALERTA ÉTICO: “Esta análise é uma simulação estatística baseada em padrões decisórios anteriores, não garantindo o resultado do processo.”

PETIÇÃO:
${textoPeticao}
`.trim();

      const { content } = await groqChatCompletion({
        apiKey: GROQ_API_KEY,
        model: GROQ_MODEL,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.3,
      });

      res.json({ juizId, juizNome: juiz.nome, model: GROQ_MODEL, parecer: content });
    } catch (e) {
      next(e);
    }
  },
);

// Compat: mantém o Simulador atual funcionando enquanto a análise não migra pro ml_service.
app.post("/api/analise/peticao", upload.single("file"), async (req, res, next) => {
  try {
    const juizId = requireJuizId(req);
    if (!req.file) {
      const err = new Error("Arquivo PDF (file) é obrigatório.");
      err.statusCode = 400;
      throw err;
    }

    const form = new FormData();
    form.append("file", new Blob([req.file.buffer], { type: req.file.mimetype }), req.file.originalname);

    const url = `${FASTAPI_BASE_URL}/api/analise/peticao?juiz_id=${encodeURIComponent(String(juizId))}`;
    const r = await fetch(url, { method: "POST", body: form });
    const bodyText = await r.text();
    if (!r.ok) {
      return res.status(502).json({
        detail: "Falha ao encaminhar análise para o serviço legado (FastAPI).",
        upstreamStatus: r.status,
        upstreamBody: bodyText,
      });
    }
    res.type(r.headers.get("content-type") || "application/json").send(bodyText);
  } catch (e) {
    next(e);
  }
});

// Handler de erros
app.use((err, req, res, next) => {
  const status = err?.statusCode && Number.isFinite(err.statusCode) ? err.statusCode : 500;
  res.status(status).json({
    detail: err?.message || "Erro interno",
  });
});

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`[prologos-server] listening on http://127.0.0.1:${PORT}`);
});

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import cors from "cors";
import dotenv from "dotenv";
import express from "express";

// Carrega .env da raiz (útil em dev/local). Em prod, use variáveis de ambiente.
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, "..", "..", ".env") });

const app = express();
app.use(cors());
app.use(express.json({ limit: "2mb" }));

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "prologos-api" });
});

// Se existir um build do Vite, o Express serve o frontend em produção.
// Esperado: rodar a API a partir de `server/` (cwd = server).
const frontendDist = path.resolve(__dirname, "..", "..", "frontend", "dist");
const indexHtml = path.join(frontendDist, "index.html");
const hasFrontendBuild = fs.existsSync(indexHtml);

if (hasFrontendBuild) {
  app.use(express.static(frontendDist));
}

// Rotas da API (placeholder). As rotas "de verdade" entram nas fases anteriores do plano.
app.get("/api/health", (_req, res) => {
  res.json({ ok: true, service: "prologos-api", mlServiceUrl: process.env.ML_SERVICE_URL ?? null });
});

// SPA fallback (apenas se o build existir e não for rota /api)
if (hasFrontendBuild) {
  app.get("*", (req, res, next) => {
    if (req.path.startsWith("/api")) return next();
    res.sendFile(indexHtml);
  });
}

const port = Number(process.env.PORT || 3000);
app.listen(port, "0.0.0.0", () => {
  // eslint-disable-next-line no-console
  console.log(`API listening on :${port}${hasFrontendBuild ? " (serving frontend dist)" : ""}`);
});

import "dotenv/config";

import cors from "cors";
import express from "express";

import { embedText, mlHealth, rankCandidates } from "./mlServiceClient.js";

const app = express();

app.use(cors());
app.use(express.json({ limit: "5mb" }));

app.get("/health", (req, res) => {
  res.json({ ok: true, service: "server", ml_service_url: process.env.ML_SERVICE_URL || null });
});

// Endpoints mínimos para validar a integração HTTP com o ml_service.
app.get("/api/ml/health", async (req, res) => {
  try {
    const data = await mlHealth();
    res.json(data);
  } catch (err) {
    res.status(502).json({ ok: false, error: String(err?.message || err) });
  }
});

app.post("/api/ml/embed", async (req, res) => {
  try {
    const { text, normalize } = req.body || {};
    const data = await embedText({ text, normalize });
    res.json(data);
  } catch (err) {
    res.status(502).json({ ok: false, error: String(err?.message || err) });
  }
});

app.post("/api/ml/rank", async (req, res) => {
  try {
    const { queryText, candidates, topK, normalize } = req.body || {};
    const data = await rankCandidates({ queryText, candidates, topK, normalize });
    res.json(data);
  } catch (err) {
    res.status(502).json({ ok: false, error: String(err?.message || err) });
  }
});

const port = Number(process.env.PORT || 3001);
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`Server (Express) ouvindo em http://127.0.0.1:${port}`);
});

