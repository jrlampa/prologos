import requests
import json
from sqlalchemy.orm import Session
from backend.database_models import SessionLocal, Tribunal, Juiz, Decisao
from datetime import datetime
import re
import os
import time
import sqlite3
import threading
import hashlib
from typing import Any, Callable, Optional, Dict
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

DATAJUD_KEY = os.getenv("DATAJUD_API_KEY")
if not DATAJUD_KEY:
    print("⚠️ AVISO: DATAJUD_API_KEY não definida.")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"APIKey {DATAJUD_KEY}",
}

#
# DataJud: mitigação imediata (curto prazo)
# - Throttling (intervalo mínimo entre chamadas)
# - Retry/backoff (inclui 429/5xx)
# - Cache persistente (SQLite local) para evitar chamadas repetidas
#

_BACKEND_DIR = os.path.dirname(__file__)

DATAJUD_TIMEOUT_SECONDS = float(os.getenv("DATAJUD_TIMEOUT_SECONDS", "20"))
DATAJUD_MIN_INTERVAL_SECONDS = float(os.getenv("DATAJUD_MIN_INTERVAL_SECONDS", "0.35"))
DATAJUD_MAX_RETRIES = int(os.getenv("DATAJUD_MAX_RETRIES", "5"))
DATAJUD_BACKOFF_FACTOR = float(os.getenv("DATAJUD_BACKOFF_FACTOR", "0.7"))
DATAJUD_CACHE_TTL_SECONDS = int(os.getenv("DATAJUD_CACHE_TTL_SECONDS", str(7 * 24 * 3600)))
DATAJUD_CACHE_PATH = os.getenv(
    "DATAJUD_CACHE_PATH",
    os.path.join(_BACKEND_DIR, "datajud_cache.sqlite3"),
)

_last_call_lock = threading.Lock()
_last_call_monotonic = 0.0

_cache_lock = threading.Lock()
_cache_initialized = False

_session_lock = threading.Lock()
_session: Optional[requests.Session] = None


def _now_epoch() -> int:
    return int(time.time())


def _init_cache_if_needed() -> None:
    global _cache_initialized
    if _cache_initialized:
        return
    with _cache_lock:
        if _cache_initialized:
            return
        conn = sqlite3.connect(DATAJUD_CACHE_PATH)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS datajud_cache (
                    cache_key TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    response_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_datajud_cache_expires_at ON datajud_cache(expires_at)"
            )
            conn.commit()
        finally:
            conn.close()
        _cache_initialized = True


def _cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    _init_cache_if_needed()
    now = _now_epoch()
    conn = sqlite3.connect(DATAJUD_CACHE_PATH)
    try:
        row = conn.execute(
            "SELECT response_json, expires_at FROM datajud_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if not row:
            return None
        response_json, expires_at = row
        if int(expires_at) <= now:
            # expirada
            try:
                conn.execute("DELETE FROM datajud_cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
            except Exception:
                pass
            return None
        try:
            return json.loads(response_json)
        except Exception:
            return None
    finally:
        conn.close()


def _cache_set(cache_key: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
    _init_cache_if_needed()
    now = _now_epoch()
    expires_at = now + int(ttl_seconds)
    conn = sqlite3.connect(DATAJUD_CACHE_PATH)
    try:
        conn.execute(
            """
            INSERT INTO datajud_cache(cache_key, created_at, expires_at, response_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
              created_at=excluded.created_at,
              expires_at=excluded.expires_at,
              response_json=excluded.response_json
            """,
            (cache_key, now, expires_at, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def _throttle() -> None:
    global _last_call_monotonic
    if DATAJUD_MIN_INTERVAL_SECONDS <= 0:
        return
    with _last_call_lock:
        now = time.monotonic()
        wait = (_last_call_monotonic + DATAJUD_MIN_INTERVAL_SECONDS) - now
        if wait > 0:
            time.sleep(wait)
        _last_call_monotonic = time.monotonic()


def _get_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session
    with _session_lock:
        if _session is not None:
            return _session

        sess = requests.Session()

        retry = Retry(
            total=DATAJUD_MAX_RETRIES,
            connect=DATAJUD_MAX_RETRIES,
            read=DATAJUD_MAX_RETRIES,
            status=DATAJUD_MAX_RETRIES,
            backoff_factor=DATAJUD_BACKOFF_FACTOR,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["POST"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        sess.mount("https://", adapter)
        sess.mount("http://", adapter)

        _session = sess
        return _session


def _make_cache_key(api_url: str, payload: Dict[str, Any]) -> str:
    raw = f"{api_url}|{json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def datajud_search(
    api_url: str,
    payload: Dict[str, Any],
    *,
    cache_key: Optional[str] = None,
    cache_ttl_seconds: int = DATAJUD_CACHE_TTL_SECONDS,
    timeout_seconds: float = DATAJUD_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Executa POST _search no DataJud com throttle + retry/backoff + cache.
    Retorna o JSON decodificado (dict).
    """
    if cache_key is None:
        cache_key = _make_cache_key(api_url, payload)

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if not DATAJUD_KEY:
        # Evita bater no endpoint sem credencial (ajuda dev local)
        raise RuntimeError("DATAJUD_API_KEY não configurada.")

    sess = _get_session()

    # Tentativa adicional simples quando o provedor insiste em 429 mesmo após retries do adapter.
    resp = None
    for attempt in range(2):
        _throttle()
        resp = sess.post(api_url, json=payload, headers=HEADERS, timeout=timeout_seconds)
        if resp.status_code != 429 or attempt == 1:
            break
        retry_after = resp.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after else max(1.0, DATAJUD_BACKOFF_FACTOR * 2)
        except Exception:
            delay = max(1.0, DATAJUD_BACKOFF_FACTOR * 2)
        time.sleep(delay)

    if resp is None or resp.status_code != 200:
        # não cacheia erro
        status = getattr(resp, "status_code", None)
        body_preview = (getattr(resp, "text", "") or "")[:500]
        raise RuntimeError(f"DataJud falhou ({status}): {body_preview}")

    data = resp.json()
    _cache_set(cache_key, data, cache_ttl_seconds)
    return data


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

def clonar_perfil_juiz(
    numero_processo_ref: str,
    *,
    progress_cb: Optional[Callable[[int, str], None]] = None,
):
    api_url, sigla_tribunal, estado = detectar_tribunal_inteligente(numero_processo_ref)
    numero_limpo = re.sub(r"\D", "", str(numero_processo_ref or ""))
    payload_ref = {"query": {"match": {"numeroProcesso": numero_limpo}}}
    try:
        if progress_cb:
            progress_cb(10, "Buscando processo de referência no DataJud…")
        hits = datajud_search(
            api_url,
            payload_ref,
            cache_key=f"proc_ref:{sigla_tribunal}:{numero_limpo}",
        ).get("hits", {}).get("hits", [])
        if not hits: return {"sucesso": False, "msg": "Processo não encontrado."}

        processo_ref = hits[0]["_source"]
        orgao_cod = processo_ref.get("orgaoJulgador", {}).get("codigo")
        orgao_nome = processo_ref.get("orgaoJulgador", {}).get("nome")

        if not orgao_cod:
            return {"sucesso": False, "msg": "Processo encontrado, mas sem orgaoJulgador.codigo."}

        if progress_cb:
            progress_cb(45, "Buscando histórico do órgão julgador no DataJud…")
        payload_hist = {"size": 50, "query": {"match": {"orgaoJulgador.codigo": orgao_cod}}, "sort": [{"dataAjuizamento": "desc"}]}
        hits_hist = datajud_search(
            api_url,
            payload_hist,
            cache_key=f"hist_orgao:{sigla_tribunal}:{orgao_cod}:size=50",
        ).get("hits", {}).get("hits", [])

        if progress_cb:
            progress_cb(75, "Salvando processos no banco…")
        stats = salvar_lote(hits_hist, sigla_tribunal, estado)

        if progress_cb:
            progress_cb(100, "Concluído.")
        return {
            "sucesso": True,
            "msg": f"{stats['novos']} novos processos salvos.",
            "juiz_nome": f"Juízo da {orgao_nome}",
            "juiz_id": stats["juiz_id"]
        }
    except Exception as e:
        return {"sucesso": False, "msg": str(e)}
