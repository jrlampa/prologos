import { Router } from "express";

import { persistCloneResult } from "../db.js";
import { fetchWithTimeout } from "../lib/fetch.js";

export function createJobsRouter({ db, fastapiBaseUrl } = {}) {
  const router = Router();

  const upstreamTimeoutMs = Number(process.env.UPSTREAM_TIMEOUT_MS || 30000);

  // Jobs: clonagem via DataJud (proxy para FastAPI/Python)
  router.post("/clonar-juiz", async (req, res, next) => {
    try {
      const numero_processo = (req.body?.numero_processo ?? "").toString().trim();
      if (!numero_processo) {
        return res.status(400).json({ detail: "numero_processo é obrigatório." });
      }

      const url = `${fastapiBaseUrl}/api/clonar-juiz/async`;
      const r = await fetchWithTimeout(
        url,
        {
        method: "POST",
          headers: {
            "content-type": "application/json",
            "x-request-id": req.requestId || "",
          },
        body: JSON.stringify({ numero_processo }),
        },
        upstreamTimeoutMs,
      );

      const bodyText = await r.text();
      res.status(r.status).type(r.headers.get("content-type") || "application/json").send(bodyText);
    } catch (e) {
      next(e);
    }
  });

  router.get("/jobs/:jobId", async (req, res, next) => {
    try {
      const jobId = (req.params.jobId ?? "").toString().trim();
      if (!jobId) return res.status(400).json({ detail: "jobId é obrigatório." });

      const url = `${fastapiBaseUrl}/api/jobs/${encodeURIComponent(jobId)}`;
      const r = await fetchWithTimeout(
        url,
        {
          method: "GET",
          headers: { "x-request-id": req.requestId || "" },
        },
        upstreamTimeoutMs,
      );
      const contentType = r.headers.get("content-type") || "application/json";

      // Se não vier JSON válido, devolve como texto (compat)
      if (!contentType.includes("application/json")) {
        const bodyText = await r.text();
        return res.status(r.status).type(contentType).send(bodyText);
      }

      const data = await r.json().catch(async () => ({ detail: await r.text() }));
      if (!r.ok) {
        return res.status(r.status).json(data);
      }

      // Single-writer: quando o job terminou com sucesso, persistir no SQLite via Express.
      if (data?.status === "succeeded" && data?.result && db) {
        try {
          const persisted = persistCloneResult(db, data.result);
          data.juiz_id = persisted.juizId;
          data.persisted = persisted;
        } catch (e) {
          // Falha ao persistir: devolve 500 e inclui jobId para diagnóstico
          return res.status(500).json({
            detail: e?.message || "Falha ao persistir resultado do job no SQLite.",
            jobId,
          });
        }
      }

      return res.status(200).json(data);
    } catch (e) {
      next(e);
    }
  });

  return router;
}

