from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uvicorn
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Carrega variáveis de ambiente
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Imports locais
from database_models import SessionLocal, Decisao, Juiz, Tribunal
import schemas
import ingestor_datajud
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, util
import numpy as np

try:
    from groq import Groq
except ImportError:
    Groq = None

app = FastAPI(
    title="API PRÓLOGOS",
    description="Motor de Jurimetria e Previsibilidade",
    version="1.0.0",
)

# --- CORS --- (Passo 3)
origins = [
    "http://localhost:5173",
    "http://localhost:3000", # Adicione outras origens se necessário
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Modelos de Requisição ---
class ClonarRequest(BaseModel):
    numero_processo: str

# --- Dependências ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_modelo_ia():
    return SentenceTransformer("all-MiniLM-L6-v2")

# --- Endpoints ---

@app.get("/")
def home():
    return {"mensagem": "API do PRÓLOGOS está online! 🚀"}

# --- Passo 1: Refatorização do Backend ---

@app.post("/api/juizes/clonar")
def clonar_juiz_endpoint(request: ClonarRequest):
    resultado = ingestor_datajud.clonar_perfil_juiz(request.numero_processo)
    if not resultado["sucesso"]:
        raise HTTPException(status_code=400, detail=resultado["msg"])
    return resultado

@app.post("/api/analise/peticao")
async def analisar_peticao(
    juiz_id: int,
    file: UploadFile = File(...),
    modelo_ia: SentenceTransformer = Depends(get_modelo_ia),
    db: Session = Depends(get_db)
):
    if not Groq or not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Groq AI não configurado.")

    # Extrair texto do PDF
    try:
        leitor = PdfReader(file.file)
        texto_peticao = "".join([p.extract_text() for p in leitor.pages])[:6000]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler PDF: {e}")

    # Obter temas do juiz
    juiz = db.query(Juiz).filter(Juiz.id == juiz_id).first()
    if not juiz:
        raise HTTPException(status_code=404, detail="Juiz não encontrado.")

    decisoes = db.query(Decisao).filter(Decisao.juiz_id == juiz_id).all()
    temas_juiz = [d.tema for d in decisoes]

    if not temas_juiz:
        raise HTTPException(status_code=404, detail="Juiz sem decisões para análise.")

    # Análise de similaridade
    v_pet = modelo_ia.encode(texto_peticao, convert_to_tensor=True)
    v_juiz = modelo_ia.encode(temas_juiz, convert_to_tensor=True)
    scores = util.cos_sim(v_pet, v_juiz)
    tema_match = temas_juiz[np.argmax(scores.cpu().numpy())]

    # Chamada à Groq AI
    client = Groq(api_key=GROQ_API_KEY)
    prompt_sistema = f"""
    Você é um Consultor Jurídico Especialista. Analise a petição abaixo no contexto do juiz {juiz.nome}, cujo tema de maior aderência foi '{tema_match}'.
    PETIÇÃO: {texto_peticao}
    """
    try:
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_sistema}],
            model="llama3-70b-8192",
        )
        parecer = resp.choices[0].message.content
        return {"parecer": parecer, "tema_detectado": tema_match}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na Groq AI: {e}")

@app.get("/api/dashboard/{juiz_id}")
def get_dashboard_data(juiz_id: int, db: Session = Depends(get_db)):
    decisoes = db.query(Decisao).filter(Decisao.juiz_id == juiz_id).all()
    if not decisoes:
        raise HTTPException(status_code=404, detail="Nenhuma decisão encontrada para este juiz.")

    # Exemplo de dados para o dashboard
    temas = [d.tema for d in decisoes]
    dist_temas = {tema: temas.count(tema) for tema in set(temas)}

    return {
        "total_decisoes": len(decisoes),
        "distribuicao_temas": dist_temas,
        "ultimas_decisoes": [schemas.DecisaoResponse.from_orm(d) for d in decisoes[-5:]]
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
