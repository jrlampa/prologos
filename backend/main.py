from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import io

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

from database_models import SessionLocal, Decisao, Juiz, Tribunal
import schemas
import ingestor_datajud
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

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def startup_event():
    global modelo_ia
    modelo_ia = SentenceTransformer("all-MiniLM-L6-v2")

@app.get("/")
def home(): return {"msg": "API Prólogos Online"}

@app.post("/api/clonar-juiz", response_model=schemas.JuizBase)

def clonar_juiz_endpoint(request: ClonarRequest, db: Session = Depends(get_db)):
    resultado = ingestor_datajud.clonar_perfil_juiz(request.numero_processo)
    if not resultado["sucesso"]:
        raise HTTPException(status_code=400, detail=resultado["msg"])
    juiz = db.query(Juiz).filter(Juiz.id == resultado["juiz_id"]).first()
    return juiz

@app.get("/api/juizes", response_model=List[schemas.Juiz])

def listar_juizes(db: Session = Depends(get_db)):
    return db.query(Juiz).all()

@app.get("/api/juiz/{juiz_id}/stats")

def get_juiz_stats(juiz_id: int, db: Session = Depends(get_db)):
    juiz = db.query(Juiz).filter(Juiz.id == juiz_id).first()
    if not juiz: raise HTTPException(404, "Juiz não encontrado")
    total_decisoes = len(juiz.decisoes)
    return {"nome": juiz.nome, "total_decisoes": total_decisoes}

@app.get("/api/dashboard/{juiz_id}")
def get_dashboard(juiz_id: int, db: Session = Depends(get_db)):
    juiz = db.query(Juiz).filter(Juiz.id == juiz_id).first()
    if not juiz:
        raise HTTPException(404, "Juiz não encontrado")
    distribuicao_temas: dict[str, int] = {}
    for decisao in juiz.decisoes:
        tema = decisao.tema or "Outros"
        distribuicao_temas[tema] = distribuicao_temas.get(tema, 0) + 1
    return {
        "nome": juiz.nome,
        "vara": juiz.vara,
        "total_decisoes": len(juiz.decisoes),
        "distribuicao_temas": distribuicao_temas,
    }

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
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
