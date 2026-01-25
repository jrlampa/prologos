import multer from "multer";

export function createErrorHandler({ pdfMaxSizeBytes } = {}) {
  return (err, req, res, _next) => {
    if (err?.name === "AbortError") {
      return res.status(504).json({ detail: "Timeout ao chamar serviço upstream." });
    }

    if (err instanceof multer.MulterError) {
      if (err.code === "LIMIT_FILE_SIZE") {
        return res.status(413).json({
          detail: `Arquivo muito grande. Limite: ${Number(pdfMaxSizeBytes ?? 0)} bytes.`,
        });
      }
      return res.status(400).json({ detail: err.message || "Erro no upload" });
    }

    const status = err?.statusCode && Number.isFinite(err.statusCode) ? err.statusCode : 500;

    // Log estruturado mínimo para diagnóstico (sem conteúdo sensível)
    try {
      const requestId = req?.requestId || req?.headers?.["x-request-id"] || null;
      console.log(
        JSON.stringify({
          level: status >= 500 ? "error" : "warn",
          msg: "request_error",
          requestId,
          status,
          detail: err?.message || "Erro interno",
        }),
      );
    } catch {
      // ignore
    }

    res.status(status).json({
      detail: err?.message || "Erro interno",
    });
  };
}

