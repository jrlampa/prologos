import requests
import json
import time
from sqlalchemy.orm import Session
from database_models import SessionLocal, Tribunal, Juiz, Decisao, Base, engine
from datetime import datetime

# Garante que as tabelas existem
Base.metadata.create_all(bind=engine)

# Header padrão
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
}


def detectar_tribunal(numero_processo):
    """
    Tenta descobrir a URL da API baseada no número CNJ.
    Ex: 0000000-00.0000.8.26.0000 -> 8.26 = TJSP
    """
    if ".8.26." in numero_processo:
        return (
            "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search",
            "TJSP",
            "SP",
        )
    elif ".8.19." in numero_processo:
        return (
            "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search",
            "TJRJ",
            "RJ",
        )
    # Adicionar outros tribunais conforme necessidade
    return (
        "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search",
        "TJRJ",
        "RJ",
    )  # Fallback


def clonar_perfil_juiz(numero_processo_ref):
    """
    1. Busca o processo de referência.
    2. Identifica a Vara (Órgão Julgador).
    3. Baixa 50 processos recentes dessa mesma Vara.
    """
    api_url, sigla_tribunal, estado = detectar_tribunal(numero_processo_ref)

    # --- PASSO 1: Encontrar o Processo Mãe ---
    print(f"Buscando processo referência {numero_processo_ref} no {sigla_tribunal}...")

    payload_ref = {
        "query": {
            "match": {
                "numeroProcesso": numero_processo_ref.replace(".", "").replace(
                    "-", ""
                )  # Remove formatação
            }
        }
    }

    try:
        resp = requests.post(api_url, json=payload_ref, headers=HEADERS)
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])

        if not hits:
            return {
                "sucesso": False,
                "msg": "Processo de referência não encontrado na API pública.",
            }

        processo_ref = hits[0]["_source"]
        orgao_cod = processo_ref.get("orgaoJulgador", {}).get("codigo")
        orgao_nome = processo_ref.get("orgaoJulgador", {}).get("nome")

        if not orgao_cod:
            return {
                "sucesso": False,
                "msg": "O processo existe, mas não tem Órgão Julgador vinculado.",
            }

        print(f"Vara identificada: {orgao_nome} (Cód: {orgao_cod})")

        # --- PASSO 2: Clonar a Vara (Baixar Histórico) ---
        print("Baixando histórico da vara para criar perfil...")

        payload_history = {
            "size": 50,  # O volume que pediste
            "query": {"match": {"orgaoJulgador.codigo": orgao_cod}},
            "sort": [{"dataAjuizamento": "desc"}],
        }

        resp_hist = requests.post(api_url, json=payload_history, headers=HEADERS)
        hits_hist = resp_hist.json().get("hits", {}).get("hits", [])

        # 3. Salva com proteção contra duplicatas
        stats = salvar_lote(hits_hist, sigla_tribunal, estado)

        return {
            "sucesso": True,
            "msg": f"Sucesso! {stats['novos']} novos processos, {stats['atualizados']} atualizados/ignorados.",
            "juiz_nome": f"Juízo da {orgao_nome}",
            "qtd": len(hits_hist),
        }

    except Exception as e:
        return {"sucesso": False, "msg": f"Erro técnico: {str(e)}"}


def salvar_lote(lista_processos, nome_tribunal, estado_tribunal):
    """
    Salva processos garantindo NÃO DUPLICAÇÃO.
    Retorna um dicionário com contadores: novos e atualizados.
    """
    session = SessionLocal()

    # Garante Tribunal
    tribunal = session.query(Tribunal).filter_by(nome=nome_tribunal).first()
    if not tribunal:
        tribunal = Tribunal(nome=nome_tribunal, estado=estado_tribunal)
        session.add(tribunal)
        session.commit()
        session.refresh(tribunal)

    contador_novos = 0
    contador_existentes = 0

    for proc in lista_processos:
        source = proc["_source"]
        numero_processo = source.get("numeroProcesso")

        # Metadados
        orgao_data = source.get("orgaoJulgador", {})
        nome_vara = orgao_data.get("nome", "Vara Desconhecida")
        data_ajuizamento_raw = source.get("dataAjuizamento")
        classe_nome = source.get("classe", {}).get("nome", "Não informado")

        # Tema (Assunto Principal)
        lista_assuntos = source.get("assuntos", [])
        tema_principal = "Geral"
        if lista_assuntos:
            primeiro = lista_assuntos[0]
            if isinstance(primeiro, list) and len(primeiro) > 0:
                tema_principal = primeiro[0].get("nome", "Geral")
            elif isinstance(primeiro, dict):
                tema_principal = primeiro.get("nome", "Geral")

        # Juiz (Vinculado à Vara)
        nome_juiz_estimado = f"Juízo da {nome_vara}"

        juiz = session.query(Juiz).filter_by(nome=nome_juiz_estimado).first()
        if not juiz:
            juiz = Juiz(
                nome=nome_juiz_estimado, vara=nome_vara, tribunal_id=tribunal.id
            )
            session.add(juiz)
            session.commit()
            session.refresh(juiz)

        # --- PROTEÇÃO CONTRA DUPLICIDADE ---
        decisao_existente = (
            session.query(Decisao).filter_by(numero_processo=numero_processo).first()
        )

        if decisao_existente:
            # Já existe: Apenas atualizamos se necessário (opcional) ou pulamos
            contador_existentes += 1
            # Se quiser atualizar algo, faria aqui:
            # decisao_existente.tema = tema_principal
            continue
        else:
            # Novo: Cria
            data_formatada = None
            if data_ajuizamento_raw:
                try:
                    data_limpa = data_ajuizamento_raw.split("T")[0]
                    data_formatada = datetime.strptime(data_limpa, "%Y-%m-%d").date()
                except:
                    pass

            nova_decisao = Decisao(
                numero_processo=numero_processo,
                texto_decisao=f"Classe: {classe_nome}. Assunto: {tema_principal}",
                resultado="Aguardando Análise",
                tema=tema_principal,
                data_decisao=data_formatada,
                juiz_id=juiz.id,
            )
            session.add(nova_decisao)
            contador_novos += 1

    session.commit()
    session.close()

    print(
        f"Lote processado: {contador_novos} inseridos, {contador_existentes} já existiam."
    )
    return {"novos": contador_novos, "atualizados": contador_existentes}


if __name__ == "__main__":
    # Teste rápido se rodar direto
    print("Ingestor pronto para clonagem.")
