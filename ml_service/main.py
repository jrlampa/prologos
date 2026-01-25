import os
from threading import Lock
from typing import Any, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

APP_VERSION = "0.1.0"

MODEL_NAME = os.getenv("ML_SERVICE_MODEL_NAME", "all-MiniLM-L6-v2")
MODEL_DEVICE = os.getenv("ML_SERVICE_MODEL_DEVICE")  # ex: "cpu", "cuda"

DEFAULT_NORMALIZE = os.getenv("ML_SERVICE_NORMALIZE", "true").lower() in (
    "1",
    "true",
    "yes",
    "y",
)
MAX_CANDIDATES = int(os.getenv("ML_SERVICE_MAX_CANDIDATES", "2000"))
MAX_TEXT_CHARS = int(os.getenv("ML_SERVICE_MAX_TEXT_CHARS", "12000"))

_model: Optional[SentenceTransformer] = None
_model_lock = Lock()


def _truncate(text: str) -> str:
    text = text or ""
    if len(text) <= MAX_TEXT_CHARS:
        return text
    return text[:MAX_TEXT_CHARS]


def get_model() -> SentenceTransformer:
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        if MODEL_DEVICE:
            _model = SentenceTransformer(MODEL_NAME, device=MODEL_DEVICE)
        else:
            _model = SentenceTransformer(MODEL_NAME)
        return _model


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)
    normalize: Optional[bool] = None


class EmbedResponse(BaseModel):
    vector: List[float]
    dim: int
    model: str
    normalized: bool


class RankCandidate(BaseModel):
    id: Any
    text: str = Field(..., min_length=1)


class RankRequest(BaseModel):
    queryText: str = Field(..., min_length=1)
    candidates: List[RankCandidate] = Field(default_factory=list)
    topK: int = Field(10, ge=1, le=200)
    normalize: Optional[bool] = None


class RankItem(BaseModel):
    id: str
    score: float


class RankResponse(BaseModel):
    top: List[RankItem]
    model: str
    totalCandidates: int
    normalized: bool


app = FastAPI(title="Prólogos ML Service", version=APP_VERSION)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ml_service",
        "version": APP_VERSION,
        "model_name": MODEL_NAME,
        "model_loaded": _model is not None,
    }


@app.post("/ml/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest):
    normalize = DEFAULT_NORMALIZE if req.normalize is None else bool(req.normalize)
    text = _truncate(req.text)

    model = get_model()
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=normalize)[0]
    vec = vec.astype(np.float32, copy=False)
    return {
        "vector": [float(x) for x in vec.tolist()],
        "dim": int(vec.shape[0]),
        "model": MODEL_NAME,
        "normalized": normalize,
    }


@app.post("/ml/rank", response_model=RankResponse)
def rank(req: RankRequest):
    if not req.candidates:
        raise HTTPException(status_code=400, detail="candidates vazio")
    if len(req.candidates) > MAX_CANDIDATES:
        raise HTTPException(
            status_code=413,
            detail=f"candidates excede ML_SERVICE_MAX_CANDIDATES ({MAX_CANDIDATES})",
        )

    normalize = DEFAULT_NORMALIZE if req.normalize is None else bool(req.normalize)
    query_text = _truncate(req.queryText)
    cand_texts = [_truncate(c.text) for c in req.candidates]

    model = get_model()
    embeddings = model.encode(
        [query_text] + cand_texts,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    ).astype(np.float32, copy=False)

    q = embeddings[0]
    c = embeddings[1:]

    if normalize:
        scores = c @ q
    else:
        denom = (np.linalg.norm(c, axis=1) * np.linalg.norm(q) + 1e-12).astype(
            np.float32
        )
        scores = (c @ q) / denom

    k = min(int(req.topK), int(scores.shape[0]))
    if k <= 0:
        return {
            "top": [],
            "model": MODEL_NAME,
            "totalCandidates": int(scores.shape[0]),
            "normalized": normalize,
        }

    top_idx = np.argpartition(-scores, kth=range(k))[:k]
    top_sorted = top_idx[np.argsort(-scores[top_idx])]

    top = [
        {"id": str(req.candidates[i].id), "score": float(scores[i])}
        for i in top_sorted.tolist()
    ]

    return {
        "top": top,
        "model": MODEL_NAME,
        "totalCandidates": int(scores.shape[0]),
        "normalized": normalize,
    }

