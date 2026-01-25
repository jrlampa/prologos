import { Router } from "express";

export function createJobsRouter({ fastapiBaseUrl } = {}) {
  const router = Router();

  // Jobs: clonagem via DataJud (proxy para FastAPI/Python)
  router.post("/clonar-juiz", async (req, res, next) => {
    try {
      const numero_processo = (req.body?.numero_processo ?? "").toString().trim();
      if (!numero_processo) {
        return res.status(400).json({ detail: "numero_processo é obrigatório." });
      }

      const url = `${fastapiBaseUrl}/api/clonar-juiz/async`;
      const r = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ numero_processo }),
      });

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
      const r = await fetch(url, { method: "GET" });
      const bodyText = await r.text();
      res.status(r.status).type(r.headers.get("content-type") || "application/json").send(bodyText);
    } catch (e) {
      next(e);
    }
  });

  return router;
}

