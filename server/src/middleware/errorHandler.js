import multer from "multer";

export function createErrorHandler({ pdfMaxSizeBytes } = {}) {
  return (err, _req, res, _next) => {
    if (err instanceof multer.MulterError) {
      if (err.code === "LIMIT_FILE_SIZE") {
        return res.status(413).json({
          detail: `Arquivo muito grande. Limite: ${Number(pdfMaxSizeBytes ?? 0)} bytes.`,
        });
      }
      return res.status(400).json({ detail: err.message || "Erro no upload" });
    }

    const status = err?.statusCode && Number.isFinite(err.statusCode) ? err.statusCode : 500;
    res.status(status).json({
      detail: err?.message || "Erro interno",
    });
  };
}

