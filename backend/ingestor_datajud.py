import requests
import json
from sqlalchemy.orm import Session
from database_models import SessionLocal, Tribunal, Juiz, Decisao
from datetime import datetime
import re
import os
from dotenv import load_dotenv

load_dotenv()

DATAJUD_KEY = os.getenv("DATAJUD_API_KEY")
if not DATAJUD_KEY:
    print("⚠️ AVISO: DATAJUD_API_KEY não definida.")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"APIKey {DATAJUD_KEY}",
}

def detectar_tribunal_inteligente(numero_processo):
    num_limpo = re.sub(r"\D", "", numero_processo)
    if len(num_limpo) < 20:
        return "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search", "TJSP", "SP"
    j_digit, tr_digits = num_limpo[13], num_limpo[14:16]
    
    mapa_estaduais = {
        "26": ("tjsp", "SP"), "19": ("tjrj", "RJ"), "13": ("tjmg", "MG"),
        "21": ("tjrs", "RS"), "16": ("tjpr", "PR"), "05": ("tjba", "BA")
    }
    if j_digit == "8" and tr_digits in mapa_estaduais:
        api_code, estado = mapa_estaduais[tr_digits]
        return f"https://api-publica.datajud.cnj.jus.br/api_publica_{api_code}/_search", f"TJ{estado}", estado
    
    return "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search", "TJSP", "SP"

def extrair_teor_decisao(processo_source):
    movimentos = processo_source.get("movimentos", [])
    if not movimentos: return None
    palavras_chave = ["julgamento", "sentença", "decisão", "mérito"]
    texto_relevante = ""
    for mov in movimentos:
        if any(p in mov.get("nome", "").lower() for p in palavras_chave):
            for comp in mov.get("complementosTabelados", []):
                descricao = comp.get("descricao", "")
                if len(descricao) > 50: texto_relevante += f"[{mov.get('dataHora', '')[:10]}] {descricao} | "
            if len(texto_relevante) > 100: break
    return texto_relevante

def salvar_lote(lista_processos, nome_tribunal, estado_tribunal):
    session = SessionLocal()
    tribunal = session.query(Tribunal).filter_by(nome=nome_tribunal).first()
    if not tribunal:
        tribunal = Tribunal(nome=nome_tribunal, estado=estado_tribunal)
        session.add(tribunal)
        session.commit()
        session.refresh(tribunal)

    juiz_id_retorno = None
    juiz_obj = None
    novos, com_teor = 0, 0

    if lista_processos:
        source_ref = lista_processos[0]["_source"]
        nome_vara = source_ref.get("orgaoJulgador", {}).get("nome", "Vara Desconhecida")
        nome_juiz = f"Juízo da {nome_vara}"
        juiz_obj = session.query(Juiz).filter_by(nome=nome_juiz).first()
        if not juiz_obj:
            juiz_obj = Juiz(nome=nome_juiz, vara=nome_vara, tribunal_id=tribunal.id)
            session.add(juiz_obj)
            session.commit()
            session.refresh(juiz_obj)
        juiz_id_retorno = juiz_obj.id

    for proc in lista_processos:
        source = proc["_source"]
        numero_processo = source.get("numeroProcesso")
        if not session.query(Decisao).filter_by(numero_processo=numero_processo).first():
            teor = extrair_teor_decisao(source)
            tema = source.get("assuntos", [{}])[0].get("nome", "Geral")
            texto_completo = f"Assunto: {tema}. {teor or ''}"
            if teor: com_teor += 1
            dt = datetime.strptime(source.get("dataAjuizamento").split("T")[0], "%Y-%m-%d").date() if source.get("dataAjuizamento") else None
            nova = Decisao(numero_processo=numero_processo, texto_decisao=texto_completo, resultado="Aguardando Análise", tema=tema, data_decisao=dt, juiz_id=juiz_id_retorno)
            session.add(nova)
            novos += 1
    
    session.commit()
    session.close()
    return {"novos": novos, "com_teor": com_teor, "juiz_id": juiz_id_retorno}

def clonar_perfil_juiz(numero_processo_ref):
    api_url, sigla_tribunal, estado = detectar_tribunal_inteligente(numero_processo_ref)
    payload_ref = {"query": {"match": {"numeroProcesso": re.sub(r'\D', '', numero_processo_ref)}}}
    try:
        resp = requests.post(api_url, json=payload_ref, headers=HEADERS)
        if resp.status_code != 200: return {"sucesso": False, "msg": f"API {sigla_tribunal} falhou ({resp.status_code})"}
        hits = resp.json().get("hits", {}).get("hits", [])
        if not hits: return {"sucesso": False, "msg": "Processo não encontrado."}

        processo_ref = hits[0]["_source"]
        orgao_cod = processo_ref.get("orgaoJulgador", {}).get("codigo")
        orgao_nome = processo_ref.get("orgaoJulgador", {}).get("nome")

        payload_hist = {"size": 50, "query": {"match": {"orgaoJulgador.codigo": orgao_cod}}, "sort": [{"dataAjuizamento": "desc"}]}
        resp_hist = requests.post(api_url, json=payload_hist, headers=HEADERS)
        hits_hist = resp_hist.json().get("hits", {}).get("hits", [])
        stats = salvar_lote(hits_hist, sigla_tribunal, estado)

        return {
            "sucesso": True,
            "msg": f"{stats['novos']} novos processos salvos.",
            "juiz_nome": f"Juízo da {orgao_nome}",
            "juiz_id": stats["juiz_id"]
        }
    except Exception as e:
        return {"sucesso": False, "msg": str(e)}
