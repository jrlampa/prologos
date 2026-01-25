import { Router } from "express";

export function createHealthRouter({ sqlitePath, fastapiBaseUrl, corsAllowlist, pdfMaxSizeBytes } = {}) {
  const router = Router();

  router.get("/health", (_req, res) => {
    res.json({ ok: true, service: "prologos-server" });
  });

  router.get("/api/health", (_req, res) => {
    res.json({
      ok: true,
      sqlitePath: sqlitePath ?? null,
      fastapiBaseUrl: fastapiBaseUrl ?? null,
      mlServiceUrl: process.env.ML_SERVICE_URL ?? null,
      corsAllowlist: corsAllowlist ?? null,
      pdfMaxSizeBytes: pdfMaxSizeBytes ?? null,
    });
  });

  return router;
}

