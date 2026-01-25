export function toInt(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : NaN;
}

export function requireJuizId(req) {
  const juizId = toInt(req.params.juizId ?? req.query.juiz_id);
  if (!Number.isFinite(juizId) || juizId <= 0) {
    const err = new Error("juiz_id inválido.");
    err.statusCode = 400;
    throw err;
  }
  return juizId;
}

