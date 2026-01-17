from pydantic import BaseModel
from datetime import date
from typing import Optional, List


# Schema base para Juiz
class JuizBase(BaseModel):
    nome: str
    vara: str


class JuizResponse(JuizBase):
    id: int

    class Config:
        from_attributes = True


# Schema base para Decisao
class DecisaoBase(BaseModel):
    numero_processo: str
    texto_decisao: Optional[str] = None
    resultado: Optional[str] = None
    tema: Optional[str] = None
    data_decisao: Optional[date] = None


class DecisaoResponse(DecisaoBase):
    id: int
    juiz_id: int
    # Aqui poderiamos aninhar o objeto Juiz, mas vamos manter simples por agora

    class Config:
        from_attributes = True
