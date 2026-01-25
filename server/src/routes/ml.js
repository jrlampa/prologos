import { Router } from "express";

import { embedText, mlHealth, rankCandidates } from "../mlServiceClient.js";

export function createMlRouter() {
  const router = Router();

  // Endpoints mínimos para validar a integração HTTP com o ml_service.
  router.get("/ml/health", async (_req, res) => {
    try {
      const data = await mlHealth();
      res.json(data);
    } catch (err) {
      res.status(502).json({ ok: false, error: String(err?.message || err) });
    }
  });

  router.post("/ml/embed", async (req, res) => {
    try {
      const { text, normalize } = req.body || {};
      const data = await embedText({ text, normalize });
      res.json(data);
    } catch (err) {
      res.status(502).json({ ok: false, error: String(err?.message || err) });
    }
  });

  router.post("/ml/rank", async (req, res) => {
    try {
      const { queryText, candidates, topK, normalize } = req.body || {};
      const data = await rankCandidates({ queryText, candidates, topK, normalize });
      res.json(data);
    } catch (err) {
      res.status(502).json({ ok: false, error: String(err?.message || err) });
    }
  });

  return router;
}

