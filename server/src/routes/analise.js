import { Router } from "express";

import { groqChatCompletion } from "../groq.js";
import { extractPdfText } from "../pdf.js";
import { requireJuizId } from "../lib/params.js";

function assertPdfBuffer(buffer) {
  if (!Buffer.isBuffer(buffer) || buffer.length < 5) {
    const err = new Error("Arquivo PDF inválido (vazio).");
    err.statusCode = 400;
    throw err;
  }

  const header = buffer.toString("ascii", 0, 5);
  if (header !== "%PDF-") {
    const err = new Error("Arquivo enviado não parece ser um PDF válido.");
    err.statusCode = 400;
    throw err;
  }
}

export function createAnaliseRouter({ db, upload, groqApiKey, groqModel, fastapiBaseUrl } = {}) {
  if (!db) {
    const err = new Error("DB não inicializado.");
    err.statusCode = 500;
    throw err;
  }
  if (!upload) {
    const err = new Error("Upload (multer) não inicializado.");
    err.statusCode = 500;
    throw err;
  }

  const router = Router();

  // Parecer estratégico (equivalente à Aba 2 do Streamlit) - Groq + PDF (+ dossiê opcional)
  router.post("/analise/peticao/parecer", upload.single("file"), async (req, res, next) => {
    try {
      const juizId = requireJuizId(req);
      const juiz = db.prepare("SELECT id, nome FROM juizes WHERE id = ?").get(juizId);
      if (!juiz) return res.status(404).json({ detail: "Juiz não encontrado" });

      if (!req.file) {
        const err = new Error("Arquivo PDF (file) é obrigatório.");
        err.statusCode = 400;
        throw err;
      }

      assertPdfBuffer(req.file.buffer);

      if (!groqApiKey) {
        const err = new Error("GROQ_API_KEY não configurada.");
        err.statusCode = 500;
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
        apiKey: groqApiKey,
        model: groqModel,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.3,
      });

      res.json({ juizId, juizNome: juiz.nome, model: groqModel, parecer: content });
    } catch (e) {
      next(e);
    }
  });

  // Compat: mantém o Simulador atual funcionando enquanto a análise não migra pro ml_service.
  router.post("/analise/peticao", upload.single("file"), async (req, res, next) => {
    try {
      const juizId = requireJuizId(req);
      if (!req.file) {
        const err = new Error("Arquivo PDF (file) é obrigatório.");
        err.statusCode = 400;
        throw err;
      }

      assertPdfBuffer(req.file.buffer);

      const form = new FormData();
      form.append(
        "file",
        new Blob([req.file.buffer], { type: req.file.mimetype || "application/pdf" }),
        req.file.originalname
      );

      const url = `${fastapiBaseUrl}/api/analise/peticao?juiz_id=${encodeURIComponent(String(juizId))}`;
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

  return router;
}

