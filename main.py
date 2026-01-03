from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uvicorn

# A chave GROQ foi movida para o .env (variável de ambiente GROQ_API_KEY). Não deixe chaves em código.

# Importamos os nossos ficheiros anteriores
from database_models import SessionLocal, Decisao, Juiz, Tribunal
import schemas

app = FastAPI(
    title="API PRÓLOGOS",
    description="Motor de Jurimetria e Previsibilidade",
    version="1.0.0",
)


# Dependência: Função que abre e fecha a conexão com o banco a cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- ROTAS (ENDPOINTS) ---


@app.get("/")
def home():
    return {"mensagem": "API do PRÓLOGOS está online! 🚀"}


# Rota 1: Listar todos os juízes monitorados
@app.get("/juizes/", response_model=List[schemas.JuizResponse])
def listar_juizes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    juizes = db.query(Juiz).offset(skip).limit(limit).all()
    return juizes


# Rota 2: Listar decisões (com filtro opcional por tema)
@app.get("/decisoes/", response_model=List[schemas.DecisaoResponse])
def listar_decisoes(tema: str = None, db: Session = Depends(get_db)):
    query = db.query(Decisao)
    if tema:
        # Filtra onde o tema contém a palavra pesquisada
        query = query.filter(Decisao.tema.contains(tema))

    decisoes = query.limit(50).all()
    return decisoes


# Rota 3: Dashboard Simples (Jurimetria Básica)
@app.get("/dashboard/metricas")
def metricas_gerais(db: Session = Depends(get_db)):
    """
    Retorna contagens simples para testarmos a saúde do sistema.
    """
    total_juizes = db.query(Juiz).count()
    total_decisoes = db.query(Decisao).count()

    # Exemplo de agregação simples: Quantos processos 'Procedente' (exemplo futuro)
    # Por enquanto, mostramos apenas o volume coletado
    return {
        "total_juizes_monitorados": total_juizes,
        "total_decisoes_indexadas": total_decisoes,
        "status_sistema": "Operacional",
    }


if __name__ == "__main__":
    # Altere aqui para 8001 ou outra porta livre
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
