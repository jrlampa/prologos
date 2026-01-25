from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import io
import threading
import uuid
from datetime import datetime, timezone

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

from backend.database_models import SessionLocal, Decisao, Juiz, Tribunal, Base, engine
from backend import schemas
from backend import ingestor_datajud
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, util
import numpy as np

app = FastAPI(title="API PRÓLOGOS", version="1.0.0")

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

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def startup_event():
    global modelo_ia
    # Garante que as tabelas existam (baseline estável independente do CWD)
    Base.metadata.create_all(bind=engine)
    modelo_ia = SentenceTransformer("all-MiniLM-L6-v2")

@app.get("/")
def home(): return {"msg": "API Prólogos Online"}

@app.post("/api/clonar-juiz", response_model=schemas.Juiz)

def clonar_juiz_endpoint(request: ClonarRequest, db: Session = Depends(get_db)):
    resultado = ingestor_datajud.clonar_perfil_juiz(request.numero_processo)
    if not resultado["sucesso"]:
        raise HTTPException(status_code=400, detail=resultado["msg"])
    juiz = db.query(Juiz).filter(Juiz.id == resultado["juiz_id"]).first()
    return juiz

# -----------------------------
# Jobs (clonagem assíncrona)
# -----------------------------

_jobs_lock = threading.Lock()
_jobs: dict = {}

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _update_job(job_id: str, **fields):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = _iso_now()

def _create_job(numero_processo: str) -> str:
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "jobId": job_id,
            "status": "queued",
            "progress": 0,
            "message": "Aguardando execução…",
            "numero_processo": numero_processo,
            "juiz_id": None,
            "error": None,
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        }
    return job_id

def _run_clone_job(job_id: str, numero_processo: str):
    try:
        _update_job(job_id, status="running", progress=1, message="Iniciando clonagem…", error=None)

        def cb(pct: int, msg: str):
            pct_norm = max(0, min(100, int(pct)))
            _update_job(job_id, progress=pct_norm, message=str(msg or ""))

        resultado = ingestor_datajud.clonar_perfil_juiz(numero_processo, progress_cb=cb)
        if not resultado.get("sucesso"):
            raise RuntimeError(resultado.get("msg") or "Falha na clonagem.")

        _update_job(
            job_id,
            status="succeeded",
            progress=100,
            message=resultado.get("msg") or "Concluído.",
            juiz_id=int(resultado.get("juiz_id")) if resultado.get("juiz_id") else None,
        )
    except Exception as e:
        _update_job(job_id, status="failed", message="Falha na clonagem.", error=str(e))

@app.post("/api/clonar-juiz/async", status_code=202, response_model=CloneJobResponse)
def clonar_juiz_async_endpoint(request: ClonarRequest):
    job_id = _create_job(request.numero_processo)
    t = threading.Thread(target=_run_clone_job, args=(job_id, request.numero_processo), daemon=True)
    t.start()
    return {"jobId": job_id, "status": "queued"}

@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado.")
        # retorna cópia para não expor mutação concorrente
        return dict(job)

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

    pdf_content = await file.read()
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
