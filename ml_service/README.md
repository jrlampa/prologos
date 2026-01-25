# `ml_service/` — microserviço stateless (embeddings/ranking)

Microserviço **Python + FastAPI** para gerar embeddings e ranquear candidatos por similaridade (cosine), pensado para ser chamado via HTTP pelo `server/` (Express).

## Rodar localmente

No Windows (PowerShell), na raiz do repo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\ml_service\requirements.txt
python -m uvicorn ml_service.main:app --host 127.0.0.1 --port 9000 --reload
```

Teste rápido:

```powershell
Invoke-RestMethod http://127.0.0.1:9000/health
```

## Variáveis de ambiente

- `ML_SERVICE_MODEL_NAME` (default: `all-MiniLM-L6-v2`)
- `ML_SERVICE_MODEL_DEVICE` (opcional: `cpu`, `cuda`)
- `ML_SERVICE_NORMALIZE` (default: `true`)
- `ML_SERVICE_MAX_CANDIDATES` (default: `2000`)
- `ML_SERVICE_MAX_TEXT_CHARS` (default: `12000`)

## Endpoints

### `POST /ml/embed`

Body:

```json
{ "text": "texto...", "normalize": true }
```

Response:

```json
{ "vector": [0.1, 0.2], "dim": 384, "model": "...", "normalized": true }
```

### `POST /ml/rank`

Body:

```json
{
  "queryText": "petição...",
  "candidates": [{ "id": 1, "text": "decisão..." }],
  "topK": 5,
  "normalize": true
}
```

Response:

```json
{
  "top": [{ "id": "1", "score": 0.73 }],
  "model": "...",
  "totalCandidates": 1,
  "normalized": true
}
```

