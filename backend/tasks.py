from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from rq import get_current_job

from backend import ingestor_datajud


logger = logging.getLogger("prologos.jobs")


def clone_juiz_datajud_task(numero_processo: str) -> Dict[str, Any]:
    """
    Tarefa de clonagem (DataJud) para rodar em worker (RQ).

    Importante (release público): esta task NÃO escreve no SQLite do produto.
    Ela apenas coleta/normaliza o payload para o Express persistir (single-writer).
    """
    job = get_current_job()
    job_id = getattr(job, "id", None)

    logger.info("[jobId=%s] clone_juiz_datajud_task started", job_id)

    def progress_cb(pct: int, msg: str) -> None:
        if not job:
            return
        try:
            job.meta["progress"] = max(0, min(100, int(pct)))
            job.meta["message"] = str(msg or "")
            job.save_meta()
        except Exception:
            # Nunca falhar a task por erro ao atualizar progresso
            pass

    progress_cb(1, "Iniciando clonagem (DataJud)…")

    payload = ingestor_datajud.clonar_perfil_juiz_payload(
        numero_processo,
        progress_cb=progress_cb,
    )

    # payload já contém sucesso/msg/tribunal/juiz/decisoes/stats
    if not payload.get("sucesso"):
        progress_cb(100, "Falha na clonagem.")
        logger.warning("[jobId=%s] clone_juiz_datajud_task failed: %s", job_id, payload.get("msg"))
        raise RuntimeError(payload.get("msg") or "Falha na clonagem.")

    progress_cb(100, "Concluído.")
    logger.info("[jobId=%s] clone_juiz_datajud_task finished (ok)", job_id)
    return payload

