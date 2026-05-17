"""
Agent 5 — Enrichisseur
1 appel LLM par chunk.
Extrait : keywords (5-10), machines_mentioned, category, summary (1 phrase), criticality.
"""
import json
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
from .utils import llm_json, update_agent, append_log, job_should_stop

logger = logging.getLogger(__name__)

CATEGORIES = [
    "sécurité", "mécanique", "électrique", "hydraulique", "pneumatique",
    "test", "vérification", "nettoyage", "documentation", "autre",
]


def _enrich_chunk(chunk: dict) -> dict:
    """Enrichit un seul chunk via LLM avec retry sur 429."""
    prompt = f"""Tu es un expert en maintenance industrielle.

Voici un extrait de documentation technique :

«{chunk['content'][:3000]}»

Retourne UNIQUEMENT ce JSON :
{{
  "keywords": ["mot1", "mot2", "mot3"],
  "machines_mentioned": ["machine1"],
  "category": "mécanique",
  "summary": "Résumé en une phrase.",
  "criticality": "high"
}}

- keywords : 5 à 10 mots-clés techniques
- category : une parmi {CATEGORIES}
- criticality : "high" / "medium" / "low"
- summary : max 120 caractères
"""
    for attempt in range(4):
        try:
            result = llm_json([{"role": "user", "content": prompt}], model_override=os.getenv("LLM_MODEL_FAST", "mistral-small-latest"))
            return {
                "chunk_id": chunk["id"],
                "keywords": result.get("keywords", []),
                "machines": result.get("machines_mentioned", []),
                "category": result.get("category", "autre"),
                "summary": result.get("summary", ""),
                "criticality": result.get("criticality", "low"),
            }
        except Exception as e:
            msg = str(e)
            if "429" in msg:
                wait = 2 ** attempt * 3  # 3s, 6s, 12s, 24s
                logger.warning(f"[enrch] chunk #{chunk['id']} rate limit — attente {wait}s")
                time.sleep(wait)
            else:
                logger.warning(f"[enrch] chunk #{chunk['id']} échoué: {e}")
                break

    return {
        "chunk_id": chunk["id"],
        "keywords": [],
        "machines": [],
        "category": "autre",
        "summary": "",
        "criticality": "low",
    }


def run(
    project_id: int,
    job_id: int,
    chunks: list[dict],
    conn: sqlite3.Connection,
    _job_id_ref: int | None = None,
) -> list[dict]:
    """
    Enrichit tous les chunks en parallèle (max 3 LLM simultanés via Semaphore dans utils).
    Met à jour la table chunks et retourne les chunks enrichis.
    """
    update_agent(conn, job_id, "enrch", "running", f"0/{len(chunks)}", 0.0)
    from .utils import LLM_PROVIDER, LLM_MODEL
    append_log(conn, job_id, "info", "enrch", f"Démarrage · {len(chunks)} chunks · {LLM_MODEL} ({LLM_PROVIDER}) · 1 appel/chunk")

    enriched: list[dict] = []
    done = 0

    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_chunk = {executor.submit(_enrich_chunk, c): c for c in chunks}

        for future in as_completed(future_to_chunk):
            # Arrêt propre si le job a été annulé
            if job_should_stop(conn, job_id):
                executor.shutdown(wait=False, cancel_futures=True)
                append_log(conn, job_id, "warn", "enrch", "Job annulé — arrêt de l'enrichisseur")
                return enriched
            result = future.result()
            enriched.append(result)
            done += 1

            # Persister en base
            conn.execute(
                """UPDATE chunks SET
                   keywords_json=?, category=?, summary=?
                   WHERE id=?""",
                (
                    json.dumps(result["keywords"], ensure_ascii=False),
                    result["category"],
                    result["summary"],
                    result["chunk_id"],
                ),
            )
            conn.commit()

            progress = done / len(chunks)
            update_agent(conn, job_id, "enrch", "running", f"{done}/{len(chunks)}", progress)
            if done % 10 == 0 or done == len(chunks):
                append_log(conn, job_id, "info", "enrch",
                           f"chunk #{result['chunk_id']} enrichi — cat={result['category']} · crit={result['criticality']}")

    # Mettre à jour machine_ref sur les chunks si une machine est mentionnée
    for e in enriched:
        if e["machines"]:
            machine = e["machines"][0]
            conn.execute(
                "UPDATE chunks SET machine_ref=? WHERE id=?",
                (machine, e["chunk_id"]),
            )
    conn.commit()

    counter = f"{len(enriched)} chunks enrichis"
    update_agent(conn, job_id, "enrch", "done", counter, 1.0)
    append_log(conn, job_id, "ok", "enrch", f"Enrichisseur ✓ — {counter}")
    return enriched
