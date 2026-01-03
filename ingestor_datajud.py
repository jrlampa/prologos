import requests
import json
from sqlalchemy.orm import Session
from database_models import SessionLocal, Tribunal, Juiz, Decisao, Base, engine
from datetime import datetime
import re

# Headers da API
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
}


def detectar_tribunal_inteligente(numero_processo):
    """
    Decodifica o número CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) para achar a API correta.
    """
    # Limpa o número
    num_limpo = re.sub(r"\D", "", numero_processo)

    if len(num_limpo) < 20:
        print(
            "⚠️ Número de processo inválido (curto demais). Usando TJSP como fallback."
        )
        return (
            "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search",
            "TJSP",
            "SP",
        )

    # O segmento J.TR começa no índice 13 (se contarmos 7+2+4 = 13 digitos antes)
    # Ex: 5001790-86.2023.8.13.0433 -> O "8.13" indica Justiça Estadual (8) de MG (13)
    # Dígito J (Justiça): posição 13
    # Dígitos TR (Tribunal): posições 14-15

    j_digit = num_limpo[13]
    tr_digits = num_limpo[14:16]

    print(f"🕵️ Decodificando CNJ: Justiça {j_digit}, Tribunal {tr_digits}")

    # Mapeamento Básico de Tribunais Estaduais (J=8)
    mapa_estaduais = {
        "26": ("tjsp", "SP"),
        "19": ("tjrj", "RJ"),
        "13": ("tjmg", "MG"),
        "21": ("tjrs", "RS"),
        "16": ("tjpr", "PR"),
        "05": ("tjba", "BA"),
        "07": ("tjdft", "DF"),
        "24": ("tjsc", "SC"),
        "06": ("tjce", "CE"),
        "08": ("tjpa", "PA"),
        "09": ("tjgo", "GO"),
    }

    # Mapeamento Federal (J=4)
    mapa_federais = {
        "01": ("trf1", "BR"),
        "02": ("trf2", "BR"),
        "03": ("trf3", "BR"),
        "04": ("trf4", "BR"),
        "05": ("trf5", "BR"),
    }

    if j_digit == "8":  # Estadual
        if tr_digits in mapa_estaduais:
            api_code, estado = mapa_estaduais[tr_digits]
            return (
                f"https://api-publica.datajud.cnj.jus.br/api_publica_{api_code}/_search",
                f"TJ{estado}",
                estado,
            )

    elif j_digit == "4":  # Federal
        if tr_digits in mapa_federais:
            api_code, estado = mapa_federais[tr_digits]
            return (
                f"https://api-publica.datajud.cnj.jus.br/api_publica_{api_code}/_search",
                f"TRF{int(tr_digits)}",
                estado,
            )

    # Fallback seguro (se não conhecemos o tribunal, tentamos TJSP que é o maior)
    print(f"⚠️ Tribunal {tr_digits} não mapeado explicitamente. Tentando TJSP.")
    return (
        "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search",
        "TJSP",
        "SP",
    )


def extrair_teor_decisao(processo_source):
    movimentos = processo_source.get("movimentos", [])
    if not movimentos:
        return None

    palavras_chave = [
        "julgamento",
        "concluso",
        "sentença",
        "decisão",
        "despacho",
        "mérito",
    ]
    texto_relevante = ""

    for mov in movimentos:
        nome_mov = mov.get("nome", "").lower()
        complementos = mov.get("complementosTabelados", [])

        if any(p in nome_mov for p in palavras_chave):
            for comp in complementos:
                descricao = comp.get("descricao", "")
                if len(descricao) > 50:
                    texto_relevante += (
                        f" [{mov.get('dataHora', '')[:10]}] {descricao} | "
                    )
            if len(texto_relevante) > 100:
                break

    return texto_relevante if texto_relevante else None


def clonar_perfil_juiz(numero_processo_ref):
    # Usa a nova função inteligente
    api_url, sigla_tribunal, estado = detectar_tribunal_inteligente(numero_processo_ref)

    print(
        f"🔍 Buscando referência: {numero_processo_ref} na API do {sigla_tribunal}..."
    )

    payload_ref = {
        "query": {
            "match": {
                "numeroProcesso": numero_processo_ref.replace(".", "").replace("-", "")
            }
        }
    }

    try:
        resp = requests.post(api_url, json=payload_ref, headers=HEADERS)

        # DEBUG DE REDE (Verifica se a API respondeu)
        if resp.status_code != 200:
            return {
                "sucesso": False,
                "msg": f"O Tribunal {sigla_tribunal} rejeitou a conexão (Erro {resp.status_code}).",
            }

        hits = resp.json().get("hits", {}).get("hits", [])

        if not hits:
            return {
                "sucesso": False,
                "msg": f"Não encontrado no {sigla_tribunal}. Motivos possíveis: 1) Segredo de Justiça (não público); 2) Processo muito recente (delay de indexação).",
            }

        processo_ref = hits[0]["_source"]
        orgao_cod = processo_ref.get("orgaoJulgador", {}).get("codigo")
        orgao_nome = processo_ref.get("orgaoJulgador", {}).get("nome")

        print(f"✅ Vara: {orgao_nome}")

        # Baixa histórico
        payload_history = {
            "size": 50,
            "query": {"match": {"orgaoJulgador.codigo": orgao_cod}},
            "sort": [{"dataAjuizamento": "desc"}],
        }

        resp_hist = requests.post(api_url, json=payload_history, headers=HEADERS)
        hits_hist = resp_hist.json().get("hits", {}).get("hits", [])

        stats = salvar_lote(hits_hist, sigla_tribunal, estado)

        return {
            "sucesso": True,
            "msg": f"Sucesso! {stats['novos']} novos, {stats['com_teor']} com teor completo.",
            "juiz_nome": f"Juízo da {orgao_nome}",
        }

    except Exception as e:
        return {"sucesso": False, "msg": f"Erro técnico: {str(e)}"}


def salvar_lote(lista_processos, nome_tribunal, estado_tribunal):
    session = SessionLocal()

    tribunal = session.query(Tribunal).filter_by(nome=nome_tribunal).first()
    if not tribunal:
        tribunal = Tribunal(nome=nome_tribunal, estado=estado_tribunal)
        session.add(tribunal)
        session.commit()
        session.refresh(tribunal)

    novos = 0
    com_teor = 0

    for proc in lista_processos:
        source = proc["_source"]
        numero_processo = source.get("numeroProcesso")
        orgao_data = source.get("orgaoJulgador", {})
        nome_vara = orgao_data.get("nome", "Vara Desconhecida")
        data_aj = source.get("dataAjuizamento")

        teor_minerado = extrair_teor_decisao(source)

        assuntos = source.get("assuntos", [])
        tema = "Geral"
        if assuntos:
            try:
                tema = (
                    assuntos[0].get("nome") or assuntos[0].get("descricao") or "Geral"
                )
            except:
                pass

        texto_completo = f"Assunto: {tema}."
        if teor_minerado:
            texto_completo += f" \n--- TRECHOS DA DECISÃO ---\n{teor_minerado}"
            com_teor += 1

        nome_juiz = f"Juízo da {nome_vara}"
        juiz = session.query(Juiz).filter_by(nome=nome_juiz).first()
        if not juiz:
            juiz = Juiz(nome=nome_juiz, vara=nome_vara, tribunal_id=tribunal.id)
            session.add(juiz)
            session.commit()
            session.refresh(juiz)

        existe = (
            session.query(Decisao).filter_by(numero_processo=numero_processo).first()
        )
        if not existe:
            dt = None
            if data_aj:
                try:
                    dt = datetime.strptime(data_aj.split("T")[0], "%Y-%m-%d").date()
                except:
                    pass

            nova = Decisao(
                numero_processo=numero_processo,
                texto_decisao=texto_completo,
                resultado="Aguardando Análise",
                tema=tema,
                data_decisao=dt,
                juiz_id=juiz.id,
            )
            session.add(nova)
            novos += 1
        elif teor_minerado:
            existe.texto_decisao = texto_completo
            session.add(existe)

    session.commit()
    session.close()
    return {"novos": novos, "com_teor": com_teor}
