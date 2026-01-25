from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Any, List, Optional
import uvicorn
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
import io
import uuid
from datetime import datetime

from rq.exceptions import NoSuchJobError
from rq.job import Job

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("prologos.fastapi")

from backend.database_models import SessionLocal, Decisao, Juiz, Tribunal, Base, engine
from backend import schemas
from backend import ingestor_datajud
from backend.queue import get_queue, get_redis
from backend.tasks import clone_juiz_datajud_task
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, util
import numpy as np

app = FastAPI(title="API PRÓLOGOS", version="1.0.0")

AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "true").lower() in ("1", "true", "yes", "y")
PYTHON_DB_WRITES_ENABLED = os.getenv("PYTHON_DB_WRITES_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "y",
)
PDF_MAX_SIZE_BYTES = int(os.getenv("PDF_MAX_SIZE_BYTES", str(10 * 1024 * 1024)))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class ClonarRequest(BaseModel):
    numero_processo: str

class CloneJobResponse(BaseModel):
    jobId: str
    status: str

class JobStatusResponse(BaseModel):
    jobId: str
    status: str
    progress: int = 0
    message: str = ""
    numero_processo: Optional[str] = None
    juiz_id: Optional[int] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    result: Optional[Any] = None

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def startup_event():
    global modelo_ia
    # Em prod com SQLite, preferimos evitar writes aqui (single-writer).
    # Use migrations/bootstrapping fora do processo, ou habilite via env.
    if AUTO_CREATE_DB:
        Base.metadata.create_all(bind=engine)
    modelo_ia = SentenceTransformer("all-MiniLM-L6-v2")

@app.get("/")
def home(): return {"msg": "API Prólogos Online"}

@app.post("/api/clonar-juiz", response_model=schemas.Juiz)

def clonar_juiz_endpoint(request: ClonarRequest, db: Session = Depends(get_db)):
    if not PYTHON_DB_WRITES_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Escrita no banco pelo serviço Python está desabilitada (single-writer). Use /api/clonar-juiz/async via Express.",
        )
    resultado = ingestor_datajud.clonar_perfil_juiz(request.numero_processo)
    if not resultado["sucesso"]:
        raise HTTPException(status_code=400, detail=resultado["msg"])
    juiz = db.query(Juiz).filter(Juiz.id == resultado["juiz_id"]).first()
    return juiz

# -----------------------------
# Jobs (clonagem assíncrona)
# -----------------------------

JOB_TIMEOUT_SECONDS = int(os.getenv("CLONE_JOB_TIMEOUT_SECONDS", "600"))
JOB_RESULT_TTL_SECONDS = int(os.getenv("CLONE_JOB_RESULT_TTL_SECONDS", str(60 * 60)))
JOB_FAILURE_TTL_SECONDS = int(os.getenv("CLONE_JOB_FAILURE_TTL_SECONDS", str(24 * 60 * 60)))


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if isinstance(dt, datetime) else None


def _map_rq_status(status: str) -> str:
    # RQ: queued/started/finished/failed/deferred/scheduled
    return {
        "queued": "queued",
        "deferred": "queued",
        "scheduled": "queued",
        "started": "running",
        "finished": "succeeded",
        "failed": "failed",
    }.get(status or "", status or "unknown")

@app.post("/api/clonar-juiz/async", status_code=202, response_model=CloneJobResponse)
def clonar_juiz_async_endpoint(request: ClonarRequest):
    q = get_queue()
    job_id = uuid.uuid4().hex
    logger.info("enqueue_clone_job jobId=%s", job_id)
    job = q.enqueue(
        clone_juiz_datajud_task,
        request.numero_processo,
        job_id=job_id,
        job_timeout=JOB_TIMEOUT_SECONDS,
        result_ttl=JOB_RESULT_TTL_SECONDS,
        failure_ttl=JOB_FAILURE_TTL_SECONDS,
    )
    return {"jobId": job.id, "status": _map_rq_status(job.get_status())}

@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    conn = get_redis()
    try:
        job = Job.fetch(job_id, connection=conn)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    rq_status = job.get_status()
    status = _map_rq_status(rq_status)
    progress = int(job.meta.get("progress") or 0)
    message = str(job.meta.get("message") or "")

    numero_processo = None
    try:
        if job.args:
            numero_processo = str(job.args[0])
    except Exception:
        numero_processo = None

    error = None
    if status == "failed":
        # Evita retornar stack enorme; expõe uma mensagem curta
        exc = (job.exc_info or "").strip().splitlines()
        if exc:
            error = exc[-1][:500]
        else:
            error = "Falha no job."

    created_at = _iso(job.enqueued_at)
    updated_at = _iso(job.ended_at or job.started_at or job.enqueued_at)

    result: Optional[Any] = None
    if status == "succeeded":
        # Resultado do job (payload para persistência no Express)
        result = job.result
        logger.info("job_succeeded jobId=%s", job.id)
    elif status == "failed":
        logger.warning("job_failed jobId=%s", job.id)

    return {
        "jobId": job.id,
        "status": status,
        "progress": max(0, min(100, progress)),
        "message": message,
        "numero_processo": numero_processo,
        "juiz_id": None,  # definido no Express após persistência (single-writer)
        "error": error,
        "created_at": created_at,
        "updated_at": updated_at,
        "result": result,
    }

@app.get("/api/juizes", response_model=List[schemas.Juiz])

def listar_juizes(db: Session = Depends(get_db)):
    return db.query(Juiz).all()

@app.get("/api/juiz/{juiz_id}/stats")

def get_juiz_stats(juiz_id: int, db: Session = Depends(get_db)):
    juiz = db.query(Juiz).filter(Juiz.id == juiz_id).first()
    if not juiz: raise HTTPException(404, "Juiz não encontrado")
    total_decisoes = len(juiz.decisoes)
    return {"nome": juiz.nome, "total_decisoes": total_decisoes}

@app.post("/api/analise/peticao")
async def analisar_peticao(juiz_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    juiz = db.query(Juiz).filter(Juiz.id == juiz_id).first()
    if not juiz or not juiz.decisoes:
        raise HTTPException(404, "Base de decisões do juiz está vazia.")

    pdf_content = await file.read(PDF_MAX_SIZE_BYTES + 1)
    if len(pdf_content) > PDF_MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (limite excedido).")
    if not pdf_content or len(pdf_content) < 5 or pdf_content[:5] != b"%PDF-":
        raise HTTPException(status_code=400, detail="Arquivo enviado não parece ser um PDF válido.")
    texto_peticao = ""
    with io.BytesIO(pdf_content) as f:
        reader = PdfReader(f)
        for page in reader.pages:
            texto_peticao += page.extract_text() or ""
    
    embedding_peticao = modelo_ia.encode(texto_peticao, convert_to_tensor=True)
    
    textos_decisoes = [d.texto_decisao for d in juiz.decisoes]
    embeddings_decisoes = modelo_ia.encode(textos_decisoes, convert_to_tensor=True)
    
    cos_scores = util.pytorch_cos_sim(embedding_peticao, embeddings_decisoes)[0]
    top_k = min(5, len(cos_scores))
    top_indices = np.argpartition(-cos_scores, range(top_k))[:top_k]

    parecer_ia = f"## Análise de Afinidade da Petição com o Juiz {juiz.nome}\n\n"
    parecer_ia += f"**Score de Afinidade Geral (média dos top 5): {np.mean(cos_scores[top_indices].numpy()):.2f}**\n\n"
    parecer_ia += "### Decisões mais Similares:\n"

    for i in top_indices:
        parecer_ia += f"- **Processo:** {juiz.decisoes[i].numero_processo} | **Similaridade:** {cos_scores[i]:.2f}\n"
        parecer_ia += f"  - **Trecho:** ...{juiz.decisoes[i].texto_decisao[:200]}...\n\n"

    return {"parecer": parecer_ia}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
