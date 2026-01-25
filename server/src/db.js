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

export function persistCloneResult(db, payload) {
  const tribunalNome = payload?.tribunal?.nome;
  const tribunalEstado = payload?.tribunal?.estado ?? null;
  const juizNome = payload?.juiz?.nome;
  const juizVara = payload?.juiz?.vara ?? null;
  const decisoes = Array.isArray(payload?.decisoes) ? payload.decisoes : [];

  if (!tribunalNome || !juizNome) {
    const err = new Error("Payload inválido para persistência (tribunal/juiz).");
    err.statusCode = 400;
    throw err;
  }

  const tx = db.transaction(() => {
    // Tribunal (nome é UNIQUE)
    db.prepare(
      `
      INSERT INTO tribunais (nome, estado)
      VALUES (?, ?)
      ON CONFLICT(nome) DO UPDATE SET estado = excluded.estado
      `
    ).run(tribunalNome, tribunalEstado);

    const tribunal = db.prepare("SELECT id FROM tribunais WHERE nome = ?").get(tribunalNome);
    if (!tribunal?.id) {
      const err = new Error("Falha ao resolver tribunal após upsert.");
      err.statusCode = 500;
      throw err;
    }

    // Juiz (não há UNIQUE; aplicamos idempotência por (nome, tribunal_id))
    let juiz = db
      .prepare("SELECT id, nome, vara FROM juizes WHERE nome = ? AND tribunal_id = ? LIMIT 1")
      .get(juizNome, tribunal.id);

    if (!juiz) {
      const info = db
        .prepare("INSERT INTO juizes (nome, vara, tribunal_id) VALUES (?, ?, ?)")
        .run(juizNome, juizVara, tribunal.id);
      juiz = { id: Number(info.lastInsertRowid), nome: juizNome, vara: juizVara };
    }

    const upsertDecisao = db.prepare(
      `
      INSERT INTO decisoes (numero_processo, texto_decisao, resultado, tema, data_decisao, juiz_id)
      VALUES (@numero_processo, @texto_decisao, @resultado, @tema, @data_decisao, @juiz_id)
      ON CONFLICT(numero_processo) DO UPDATE SET
        texto_decisao = excluded.texto_decisao,
        tema = excluded.tema,
        data_decisao = excluded.data_decisao,
        juiz_id = excluded.juiz_id,
        resultado = CASE
          WHEN decisoes.resultado IS NULL OR decisoes.resultado = 'Aguardando Análise'
            THEN excluded.resultado
          ELSE decisoes.resultado
        END
      `
    );

    let processed = 0;
    for (const d of decisoes) {
      const numero_processo = (d?.numero_processo ?? "").toString().trim();
      if (!numero_processo) continue;

      upsertDecisao.run({
        numero_processo,
        texto_decisao: (d?.texto_decisao ?? "").toString(),
        resultado: (d?.resultado ?? "Aguardando Análise").toString(),
        tema: (d?.tema ?? "Geral").toString(),
        data_decisao: d?.data_decisao ? String(d.data_decisao) : null,
        juiz_id: juiz.id,
      });
      processed += 1;
    }

    return {
      tribunalId: Number(tribunal.id),
      juizId: Number(juiz.id),
      processed,
    };
  });

  return tx();
}

