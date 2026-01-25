import { Router } from "express";

import { getJuizes, getJuizStats, getJuizContextForDossie } from "../db.js";
import { groqChatCompletion } from "../groq.js";
import { requireJuizId } from "../lib/params.js";

export function createJuizesRouter({ db, groqApiKey, groqModel } = {}) {
  if (!db) {
    const err = new Error("DB não inicializado.");
    err.statusCode = 500;
    throw err;
  }

  const router = Router();

  // Paridade mínima do frontend atual
  router.get("/juizes", (_req, res) => {
    res.json(getJuizes(db));
  });

  router.get("/juiz/:juizId/stats", (req, res) => {
    const juizId = requireJuizId(req);
    const stats = getJuizStats(db, juizId);
    if (!stats) return res.status(404).json({ detail: "Juiz não encontrado" });
    res.json(stats);
  });

  // Dossiê (migrado do Streamlit)
  router.post("/juiz/:juizId/dossie", async (req, res, next) => {
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

      if (!groqApiKey) {
        const err = new Error("GROQ_API_KEY não configurada.");
        err.statusCode = 500;
        throw err;
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
        apiKey: groqApiKey,
        model: groqModel,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.4,
      });

      res.json({
        juizId,
        juizNome: juiz.nome,
        model: groqModel,
        dossie: content,
      });
    } catch (e) {
      next(e);
    }
  });

  return router;
}

