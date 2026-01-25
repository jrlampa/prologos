import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import multer from "multer";

import { openSqlite } from "./db.js";
import { createErrorHandler } from "./middleware/errorHandler.js";
import { createAnaliseRouter } from "./routes/analise.js";
import { createHealthRouter } from "./routes/health.js";
import { createJobsRouter } from "./routes/jobs.js";
import { createJuizesRouter } from "./routes/juizes.js";
import { createMlRouter } from "./routes/ml.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Carrega .env da raiz (útil em dev/local). Em prod, use variáveis de ambiente.
dotenv.config({ path: path.resolve(__dirname, "..", "..", ".env") });
dotenv.config();

const PORT = Number(process.env.PORT || 3001);
const SQLITE_PATH =
  process.env.SQLITE_PATH || path.resolve(__dirname, "..", "..", "backend", "prologos_mvp.db");
const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";
const FASTAPI_BASE_URL = (process.env.FASTAPI_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);

const CORS_ORIGINS = (process.env.CORS_ORIGINS || "http://localhost:5173,http://127.0.0.1:5173")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const corsAllowlist = new Set(CORS_ORIGINS);

const PDF_MAX_SIZE_BYTES = Number(process.env.PDF_MAX_SIZE_BYTES || 10 * 1024 * 1024);

const db = openSqlite(SQLITE_PATH);

const app = express();
app.disable("x-powered-by");
if (process.env.TRUST_PROXY === "true") app.set("trust proxy", 1);

// Observabilidade mínima: requestId + logs estruturados (JSON) sem dependências.
app.use((req, res, next) => {
  const requestId = (req.headers["x-request-id"] || "").toString().trim() || crypto.randomUUID();
  req.requestId = requestId;
  res.setHeader("x-request-id", requestId);

  const start = process.hrtime.bigint();
  res.on("finish", () => {
    const end = process.hrtime.bigint();
    const durationMs = Number(end - start) / 1e6;
    const level =
      res.statusCode >= 500 ? "error" : res.statusCode >= 400 ? "warn" : "info";
    // Não loga body/headers sensíveis.
    console.log(
      JSON.stringify({
        level,
        msg: "http_request",
        requestId,
        method: req.method,
        path: req.originalUrl,
        status: res.statusCode,
        durationMs: Math.round(durationMs * 1000) / 1000,
      }),
    );
  });

  next();
});

app.use(
  helmet({
    // Se estivermos servindo SPA também, um CSP default tende a quebrar.
    contentSecurityPolicy: false,
    // Evita bloquear consumo cross-origin quando a UI está em outro host.
    crossOriginResourcePolicy: { policy: "cross-origin" },
  }),
);

app.use(
  cors({
    origin(origin, cb) {
      // Sem Origin (ex.: curl/servidor) -> permite
      if (!origin) return cb(null, true);
      if (corsAllowlist.has(origin)) return cb(null, true);
      const err = new Error("Not allowed by CORS");
      err.statusCode = 403;
      return cb(err);
    },
    credentials: true,
  }),
);

app.use(express.json({ limit: "2mb" }));

const apiLimiter = rateLimit({
  windowMs: Number(process.env.RATE_LIMIT_WINDOW_MS || 10 * 60 * 1000),
  max: Number(process.env.RATE_LIMIT_MAX || 300),
  standardHeaders: true,
  legacyHeaders: false,
  // Evita aplicar duas vezes em rotas que já têm um limit mais restritivo
  skip: (req) => req.path.startsWith("/analise") || /^\/juiz\/\d+\/dossie$/.test(req.path),
  handler: (_req, res) => {
    res.status(429).json({ detail: "Muitas requisições. Tente novamente mais tarde." });
  },
});

const aiLimiter = rateLimit({
  windowMs: Number(process.env.AI_RATE_LIMIT_WINDOW_MS || 10 * 60 * 1000),
  max: Number(process.env.AI_RATE_LIMIT_MAX || 30),
  standardHeaders: true,
  legacyHeaders: false,
  handler: (_req, res) => {
    res.status(429).json({ detail: "Muitas requisições em endpoints de IA. Aguarde e tente novamente." });
  },
});

const cloneLimiter = rateLimit({
  windowMs: Number(process.env.CLONE_RATE_LIMIT_WINDOW_MS || 60 * 60 * 1000),
  max: Number(process.env.CLONE_RATE_LIMIT_MAX || 20),
  standardHeaders: true,
  legacyHeaders: false,
  handler: (_req, res) => {
    res.status(429).json({
      detail: "Muitas requisições de clonagem. Aguarde e tente novamente mais tarde.",
    });
  },
});

app.use("/api", apiLimiter);
app.use("/api/analise", aiLimiter);
app.use("/api/juiz/:juizId/dossie", aiLimiter);
app.use("/api/clonar-juiz", cloneLimiter);

const uploadPdf = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: PDF_MAX_SIZE_BYTES },
  fileFilter: (_req, file, cb) => {
    const mime = (file?.mimetype || "").toLowerCase();
    const ok =
      mime === "application/pdf" || mime === "application/x-pdf" || mime === "application/octet-stream";
    if (ok) return cb(null, true);
    const err = new Error("Tipo de arquivo inválido. Envie um PDF.");
    err.statusCode = 400;
    return cb(err);
  },
});

// Healths (inclui /health e /api/health)
app.use(
  createHealthRouter({
    sqlitePath: SQLITE_PATH,
    fastapiBaseUrl: FASTAPI_BASE_URL,
    corsAllowlist: CORS_ORIGINS,
    pdfMaxSizeBytes: PDF_MAX_SIZE_BYTES,
  }),
);

// Se existir um build do Vite, o Express serve o frontend em produção.
const frontendDist = path.resolve(__dirname, "..", "..", "frontend", "dist");
const indexHtml = path.join(frontendDist, "index.html");
const hasFrontendBuild = fs.existsSync(indexHtml);
if (hasFrontendBuild) {
  app.use(express.static(frontendDist));
}

// Rotas /api (separadas por módulos)
app.use("/api", createJuizesRouter({ db, groqApiKey: GROQ_API_KEY, groqModel: GROQ_MODEL }));
app.use(
  "/api",
  createAnaliseRouter({
    db,
    upload: uploadPdf,
    groqApiKey: GROQ_API_KEY,
    groqModel: GROQ_MODEL,
    fastapiBaseUrl: FASTAPI_BASE_URL,
  }),
);
app.use("/api", createJobsRouter({ db, fastapiBaseUrl: FASTAPI_BASE_URL }));
app.use("/api", createMlRouter());

// SPA fallback (apenas se o build existir e não for rota /api)
if (hasFrontendBuild) {
  app.get("*", (req, res, next) => {
    if (req.path.startsWith("/api")) return next();
    res.sendFile(indexHtml);
  });
}

// Handler de erros (inclui Multer e CORS)
app.use(createErrorHandler({ pdfMaxSizeBytes: PDF_MAX_SIZE_BYTES }));

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(
    `[prologos-server] listening on http://127.0.0.1:${PORT}${hasFrontendBuild ? " (serving frontend dist)" : ""}`,
  );
});
