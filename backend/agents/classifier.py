"""
Agent 3.5 — BatchIngestPlanner
Un ingénieur humain ne lit pas chaque document un par un — il regarde le lot,
comprend le contexte du projet, puis décide l'organisation de tout le batch
en un coup d'œil.

Ce module fait pareil : 1 seul appel LLM voit tous les documents en même temps,
comprend les relations entre eux, et produit un plan d'ingestion pour le batch.

Stratégie :
  1. Extraire un aperçu de chaque doc (nom + taille + 300 premiers chars)
  2. 1 appel mistral-small → plan complet (doc_type + machine_ref par doc)
  3. Mettre à jour documents en base
  4. Enrichir la liste parsed_docs pour le chunker

Fallback : si l'appel échoue → classification regex doc par doc.
"""
import json
import logging
import os
import re
import sqlite3

from .utils import update_agent, append_log, llm_json

logger = logging.getLogger(__name__)

_LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "mistral-small-latest")

# Aperçu envoyé au LLM par document (chars) — assez pour identifier sans surcharger
PREVIEW_CHARS = 400

# Nombre max de docs dans un seul appel LLM
# Au-delà → découpage en sous-batches
MAX_DOCS_PER_CALL = 20

DOC_TYPES = [
    "manual_constructor",    # Manuel d'utilisation / maintenance constructeur
    "intervention_report",   # Rapport d'intervention / bon de travail
    "technical_datasheet",   # Fiche technique / datasheet produit
    "parts_inventory",       # Inventaire / liste de pièces (CSV, XLSX, tableau)
    "procedure_checklist",   # Procédure ou checklist opératoire
    "unknown",
]

_PLAN_PROMPT = """\
Tu es un ingénieur RAG qui reçoit un lot de documents industriels à ingérer.
Analyse TOUS les documents d'un coup, comprends le contexte du projet, et \
produis un plan d'ingestion structuré.

--- DOCUMENTS DU LOT ({n} fichiers) ---
{doc_list}
--- FIN DU LOT ---

Types documentaires disponibles : {types}

Réponds UNIQUEMENT avec ce JSON (pas de texte avant/après) :
{{
  "project_context": {{
    "main_machines": ["<liste des machines/équipements identifiés>"],
    "manufacturer": "<constructeur principal, vide si inconnu>",
    "industry": "<secteur industriel, ex: air comprimé, hydraulique...>",
    "language": "fr" | "en" | "bilingual"
  }},
  "documents": [
    {{
      "filename": "<nom exact du fichier>",
      "doc_type": "<type parmi {types}>",
      "machine_ref": "<machine concernée ou vide>",
      "manufacturer": "<constructeur ou vide>",
      "model": "<modèle exact ou vide>",
      "language": "fr" | "en" | "bilingual",
      "notes": "<1 phrase sur le contenu>"
    }}
  ]
}}
"""

# ---------------------------------------------------------------------------
# Fallback regex par document (si LLM échoue)
# ---------------------------------------------------------------------------

_FALLBACK_RULES = [
    (r"\b(bon de travail|rapport d.intervention|ordre de réparation)\b", "intervention_report"),
    (r"\b(parts list|spare parts|liste de pièces|nomenclature)\b",       "parts_inventory"),
    (r"\b(datasheet|fiche technique|caractéristiques techniques)\b",     "technical_datasheet"),
    (r"\b(checklist|liste de contrôle|procédure)\b",                     "procedure_checklist"),
    (r"\b(manuel|manual|user guide|guide d.utilisation|maintenance)\b",  "manual_constructor"),
]


def _fallback_doc(filename: str, content: str) -> dict:
    text = (filename + " " + content[:1000]).lower()
    for pattern, doc_type in _FALLBACK_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return {"doc_type": doc_type, "machine_ref": "", "manufacturer": "",
                    "model": "", "language": "fr", "notes": "regex fallback"}
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("csv", "xls", "xlsx"):
        return {"doc_type": "parts_inventory", "machine_ref": "", "manufacturer": "",
                "model": "", "language": "fr", "notes": "extension fallback"}
    return {"doc_type": "unknown", "machine_ref": "", "manufacturer": "",
            "model": "", "language": "fr", "notes": "fallback générique"}


# ---------------------------------------------------------------------------
# Appel LLM batch
# ---------------------------------------------------------------------------

def _plan_batch(docs: list[dict]) -> dict | None:
    """
    Envoie un lot de docs au LLM et retourne le plan.
    docs = [{filename, content}]
    Retourne le JSON parsé ou None si échec.
    """
    doc_lines = []
    for i, doc in enumerate(docs, 1):
        preview = doc["content"][:PREVIEW_CHARS].replace("\n", " ").strip()
        size_kb = len(doc["content"]) // 1024
        doc_lines.append(
            f"[{i}] {doc['filename']} ({size_kb} Ko)\n    Aperçu : {preview}"
        )

    prompt = _PLAN_PROMPT.format(
        n=len(docs),
        doc_list="\n\n".join(doc_lines),
        types=", ".join(DOC_TYPES),
    )

    try:
        result = llm_json(
            [{"role": "user", "content": prompt}],
            timeout=60.0,
            model_override=_LLM_MODEL_FAST,
        )
        return result
    except Exception as e:
        logger.warning("[classifier] LLM batch échoué : %s", e)
        return None


# ---------------------------------------------------------------------------
# Agent run()
# ---------------------------------------------------------------------------

def run(
    project_id: int,
    job_id: int,
    parsed_docs: list[dict],
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Planifie l'ingestion de tout le batch en 1-2 appels LLM.
    Enrichit chaque doc avec doc_type, machine_ref, manufacturer, model, language.
    Met à jour documents en base.
    """
    update_agent(conn, job_id, "classify", "running", "")
    append_log(conn, job_id, "info", "classify",
               f"BatchIngestPlanner · {len(parsed_docs)} documents")

    if not parsed_docs:
        update_agent(conn, job_id, "classify", "done", "0 docs")
        return parsed_docs

    # --- Appel LLM par sous-batches ---
    plan_by_filename: dict[str, dict] = {}
    project_context: dict = {}

    for batch_start in range(0, len(parsed_docs), MAX_DOCS_PER_CALL):
        batch = parsed_docs[batch_start : batch_start + MAX_DOCS_PER_CALL]
        plan = _plan_batch(batch)

        if plan:
            # Mémoriser le contexte projet (premier sous-batch fait foi)
            if not project_context and plan.get("project_context"):
                project_context = plan["project_context"]

            for doc_plan in plan.get("documents", []):
                fname = doc_plan.get("filename", "")
                if fname:
                    plan_by_filename[fname] = doc_plan

            machines = project_context.get("main_machines", [])
            append_log(conn, job_id, "ok", "classify",
                       f"Plan batch {batch_start//MAX_DOCS_PER_CALL + 1} OK"
                       + (f" · machines: {', '.join(machines)}" if machines else ""))
        else:
            # Fallback regex pour ce sous-batch
            append_log(conn, job_id, "warn", "classify",
                       f"LLM indisponible — fallback regex pour {len(batch)} docs")
            for doc in batch:
                plan_by_filename[doc["filename"]] = _fallback_doc(
                    doc["filename"], doc.get("content", "")
                )

    # --- Enrichir les docs et persister en base ---
    enriched: list[dict] = []

    for doc in parsed_docs:
        fname   = doc.get("filename", "")
        doc_id  = doc.get("doc_id")
        meta    = plan_by_filename.get(fname) or _fallback_doc(fname, doc.get("content", ""))

        # Héritage du contexte projet si le doc n'a pas de machine_ref
        if not meta.get("machine_ref") and project_context.get("main_machines"):
            # N'affecter une machine que s'il n'y en a qu'une dans le projet
            if len(project_context["main_machines"]) == 1:
                meta["machine_ref"] = project_context["main_machines"][0]

        if not meta.get("manufacturer") and project_context.get("manufacturer"):
            meta["manufacturer"] = project_context["manufacturer"]

        doc_enriched = {
            **doc,
            "doc_type":     meta.get("doc_type", "unknown"),
            "machine_ref":  meta.get("machine_ref") or doc.get("machine_ref") or "",
            "manufacturer": meta.get("manufacturer", ""),
            "model":        meta.get("model", ""),
            "language":     meta.get("language", "fr"),
        }

        # Persistance en base
        if doc_id:
            existing_meta = {}
            row = conn.execute(
                "SELECT metadata_json FROM documents WHERE id=?", (doc_id,)
            ).fetchone()
            if row and row[0]:
                try:
                    existing_meta = json.loads(row[0])
                except Exception:
                    pass

            existing_meta.update({
                "manufacturer":    meta.get("manufacturer", ""),
                "model":           meta.get("model", ""),
                "language":        meta.get("language", "fr"),
                "notes":           meta.get("notes", ""),
                "project_context": project_context,
            })

            conn.execute(
                """UPDATE documents
                   SET doc_type=?, machine_ref=?, metadata_json=?
                   WHERE id=?""",
                (
                    doc_enriched["doc_type"],
                    doc_enriched["machine_ref"],
                    json.dumps(existing_meta, ensure_ascii=False),
                    doc_id,
                ),
            )
            conn.commit()

        log_line = (
            f"✓ {fname} → {doc_enriched['doc_type']}"
            + (f" | {doc_enriched['machine_ref']}" if doc_enriched["machine_ref"] else "")
            + (f" | {doc_enriched['manufacturer']}" if doc_enriched["manufacturer"] else "")
            + (f" {doc_enriched['model']}" if doc_enriched["model"] else "")
        )
        append_log(conn, job_id, "ok", "classify", log_line)
        logger.info("[classifier] %s", log_line)
        enriched.append(doc_enriched)

    # Log contexte projet global
    if project_context:
        append_log(conn, job_id, "info", "classify",
                   f"Contexte projet : {json.dumps(project_context, ensure_ascii=False)}")

    update_agent(conn, job_id, "classify", "done",
                 f"{len(enriched)} docs · 1 appel LLM batch")
    return enriched
