import Database from "better-sqlite3";

export function openSqlite(sqlitePath) {
  if (!sqlitePath) {
    const err = new Error("SQLITE_PATH não configurado.");
    err.statusCode = 500;
    throw err;
  }

  const db = new Database(sqlitePath, {
    fileMustExist: true,
  });

  // Melhor chance de evitar locks no SQLite em cenários com múltiplos processos.
  try {
    db.pragma("journal_mode = WAL");
  } catch {
    // ignore
  }
  db.pragma("foreign_keys = ON");

  return db;
}

export function getJuizes(db) {
  return db
    .prepare("SELECT id, nome, vara, tribunal_id AS tribunalId FROM juizes ORDER BY nome")
    .all();
}

export function getJuizStats(db, juizId) {
  const juiz = db
    .prepare("SELECT id, nome, vara, tribunal_id AS tribunalId FROM juizes WHERE id = ?")
    .get(juizId);
  if (!juiz) return null;

  const row = db
    .prepare("SELECT COUNT(1) AS total_decisoes FROM decisoes WHERE juiz_id = ?")
    .get(juizId);

  return {
    nome: juiz.nome,
    total_decisoes: Number(row?.total_decisoes ?? 0),
  };
}

export function getJuizContextForDossie(db, juizId, limit = 50) {
  const juiz = db
    .prepare("SELECT id, nome FROM juizes WHERE id = ?")
    .get(juizId);
  if (!juiz) return null;

  const decisoes = db
    .prepare(
      "SELECT tema, resultado FROM decisoes WHERE juiz_id = ? ORDER BY data_decisao DESC, id DESC LIMIT ?",
    )
    .all(juizId, limit);

  return { juiz, decisoes };
}

