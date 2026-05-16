"""
Agent 1 — Arborescence
Analyse la structure du dossier uploadé.
Déduit pour chaque fichier : machine (dossier parent), type, catégorie.
Fait 1 appel LLM avec l'arbre de fichiers complet.
"""
import logging
import sqlite3
from pathlib import Path

from .utils import llm_json, update_agent, append_log

logger = logging.getLogger(__name__)


def run(
    project_id: int,
    job_id: int,
    file_paths: list[Path],
    conn: sqlite3.Connection,
) -> dict[str, list[Path]]:
    """
    Analyse l'arborescence et détecte les machines.
    Retourne {machine_name: [file_paths]}.
    """
    update_agent(conn, job_id, "arbo", "running", "")
    append_log(conn, job_id, "info", "arbo", f"{len(file_paths)} fichiers détectés — appel LLM classification")

    tree_lines = [f"- {p.name}" for p in file_paths]
    tree_text = "\n".join(tree_lines)

    prompt = f"""Tu es un expert en maintenance industrielle.

Voici la liste des fichiers uploadés pour constituer une base de connaissances industrielle :

{tree_text}

Ta mission : identifier les machines distinctes mentionnées dans ces noms de fichiers et regrouper les fichiers par machine.

Retourne UNIQUEMENT ce JSON :
{{
  "machines": [
    {{"name": "Nom complet de la machine", "files": ["fichier1.pdf", "fichier2.docx"]}}
  ]
}}

Si un fichier est générique (plan d'atelier, catalogue général…), associe-le à "Général".
"""

    try:
        result = llm_json([{"role": "user", "content": prompt}])
    except Exception as e:
        logger.warning(f"[arbo] LLM échoué ({e}), fallback Général")
        result = {"machines": [{"name": "Général", "files": [p.name for p in file_paths]}]}

    file_map = {p.name: p for p in file_paths}
    machines: dict[str, list[Path]] = {}

    for machine in result.get("machines", []):
        name = machine.get("name", "Général").strip() or "Général"
        machines[name] = []
        for fname in machine.get("files", []):
            if fname in file_map:
                machines[name].append(file_map[fname])

    # Fichiers non classés → Général
    classified = {p for paths in machines.values() for p in paths}
    unclassified = [p for p in file_paths if p not in classified]
    if unclassified:
        machines.setdefault("Général", []).extend(unclassified)

    # Persister machine_ref sur chaque document
    for machine_name, paths in machines.items():
        for p in paths:
            conn.execute(
                "UPDATE documents SET machine_ref=? WHERE project_id=? AND filename=?",
                (machine_name, project_id, p.name),
            )
    conn.commit()

    n_machines = len(machines)
    counter = f"{len(file_paths)} fichiers · {n_machines} machine{'s' if n_machines > 1 else ''}"
    update_agent(conn, job_id, "arbo", "done", counter)
    append_log(conn, job_id, "ok", "arbo", f"Arborescence ✓ — {counter}")
    return machines
