from __future__ import annotations

from typing import Any, List, Literal, Sequence, Union

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="prologos-ml-service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "prologos-ml-service"}


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)


class EmbedResponse(BaseModel):
    vector: List[float]


@app.post("/ml/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    # Placeholder (stateless). Trocar por sentence-transformers na Fase 2.
    return EmbedResponse(vector=[])


CandidateId = Union[str, int]


class Candidate(BaseModel):
    id: CandidateId
    text: str = Field(..., min_length=1)


class RankRequest(BaseModel):
    queryText: str = Field(..., min_length=1)
    candidates: Sequence[Candidate]
    topK: int = Field(5, ge=1, le=200)


class RankedItem(BaseModel):
    id: CandidateId
    score: float


class RankResponse(BaseModel):
    top: List[RankedItem]


@app.post("/ml/rank", response_model=RankResponse)
def rank(req: RankRequest) -> RankResponse:
    # Placeholder (stateless). Retorna os primeiros topK com score=0.
    top = [RankedItem(id=c.id, score=0.0) for c in list(req.candidates)[: req.topK]]
    return RankResponse(top=top)

