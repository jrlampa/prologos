# Runbook — Release público (PRÓLOGOS)

Este runbook descreve o mínimo operacional para subir, diagnosticar e manter a stack em um cenário de **release público**.

## Serviços

- **API principal (Express)**: `server/` expõe rotas `/api/*` e é o **único writer** do SQLite.
- **FastAPI (legado/compat)**: `backend/` fornece análise de afinidade e executa endpoints de jobs (fila).
- **Worker (RQ)**: processa clonagem DataJud e publica status/resultado no Redis.
- **Redis**: fila + estado/resultado de jobs (TTL configurável).
- **ML service (opcional)**: `ml_service/` (embeddings/ranking).

## Variáveis de ambiente (mínimo)

### Express (`server/`)

- **`SQLITE_PATH`**: caminho do SQLite (deve existir).
- **`FASTAPI_BASE_URL`**: ex.: `http://fastapi:8000`
- **`GROQ_API_KEY`**: obrigatório para dossiê/parecer
- **`CORS_ORIGINS`**: allowlist (produção)
- **Rate limit**:
  - `RATE_LIMIT_WINDOW_MS`, `RATE_LIMIT_MAX`
  - `AI_RATE_LIMIT_WINDOW_MS`, `AI_RATE_LIMIT_MAX`
  - `CLONE_RATE_LIMIT_WINDOW_MS`, `CLONE_RATE_LIMIT_MAX`
- **Upstream**:
  - `UPSTREAM_TIMEOUT_MS` (timeout de chamadas ao FastAPI)

### FastAPI (`backend/`)

- **`REDIS_URL`**: ex.: `redis://redis:6379/0`
- **`DATAJUD_API_KEY`**: obrigatório para clonagem (DataJud)
- **`DATABASE_URL`**: apenas leitura em produção (ex.: `sqlite:////data/prologos_mvp.db`)
- **Single-writer**:
  - `PYTHON_DB_WRITES_ENABLED=false`
  - `AUTO_CREATE_DB=false`
- **`PDF_MAX_SIZE_BYTES`**: limite de upload

### Worker (RQ)

- **`REDIS_URL`**
- **`DATAJUD_API_KEY`**

## Subindo com Docker Compose (recomendado)

O arquivo `docker-compose.yml` já define `api`, `fastapi`, `worker`, `redis` e `ml` (opcional).

- Subir base (sem ML):

```bash
docker compose up --build
```

- Subir com ML:

```bash
docker compose --profile ml up --build
```

## Health checks e diagnóstico rápido

- **Express**:
  - `GET /health`
  - `GET /api/health`
- **FastAPI**:
  - `GET http://fastapi:8000/`
- **Redis**:
  - ver logs do container e/ou `redis-cli ping`
- **ML (opcional)**:
  - `GET /api/ml/health`

### Logs / correlação

- Cada request no Express tem `x-request-id`.
- Em erros upstream, procure o mesmo `requestId` nos logs para correlação.

## Fluxo de clonagem (DataJud) — produção

1. Cliente chama:
   - `POST /api/clonar-juiz` com body `{ "numero_processo": "..." }`
2. Recebe `jobId`.
3. Cliente faz polling:
   - `GET /api/jobs/:jobId`
4. Quando `status == "succeeded"`, o Express persiste o payload no SQLite e responde com:
   - `juiz_id` e `persisted.*`

## Limpeza / manutenção

### Reset de jobs

- Limpar Redis (cuidado!):
  - `redis-cli FLUSHDB`

### Cache DataJud

- Remover cache local (se existir):
  - `backend/datajud_cache.sqlite3`

### SQLite

- Backup do arquivo do banco antes de alterações:
  - copiar `prologos_mvp.db` (snapshot)

## Observações importantes

- Em Windows, `better-sqlite3` pode exigir toolchain C++ para rodar fora do Docker. Para ambiente local/release, prefira **Docker** com Node 20 (imagem oficial).
- Nunca logue conteúdo integral de PDFs/petições/decisões nem segredos (`GROQ_API_KEY`, `DATAJUD_API_KEY`).

