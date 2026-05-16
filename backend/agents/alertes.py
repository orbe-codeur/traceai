"""
Agent 10 — Alertes
Analyse le wiki et génère des alertes proactives :
- Maintenance en retard (patterns temporels)
- Pannes récurrentes (≥ 3 occurrences)
- Contradictions non résolues
- Lacunes de documentation
"""
import json
import logging
import sqlite3

from .utils import llm_json, update_agent

logger = logging.getLogger(__name__)


def run(
    project_id: int,
    job_id: int,
    wiki_pages: list[dict],
    conn: sqlite3.Connection,
) -> list[dict]:
    """Analyse le wiki et génère les alertes. Retourne la liste des alertes créées."""
    update_agent(conn, job_id, "alert", "running", "")
    logger.info(f"[alertes] Analyse de {len(wiki_pages)} pages wiki")

    alerts: list[dict] = []

    # 1. Contradictions détectées par le Compilateur → alertes critiques
    for page in wiki_pages:
        for c in page.get("contradictions", []):
            alert = {
                "project_id": project_id,
                "machine_ref": page.get("machine"),
                "alert_type": "contradiction",
                "message": (
                    f"Contradiction sur « {c.get('topic', '?')} » — "
                    f"{c.get('src_a', '?')} : {c.get('val_a', '?')} "
                    f"vs {c.get('src_b', '?')} : {c.get('val_b', '?')}"
                ),
                "severity": "critical",
            }
            alerts.append(alert)

        # 2. Lacunes → alertes info
        for gap in page.get("gaps", []):
            alert = {
                "project_id": project_id,
                "machine_ref": page.get("machine"),
                "alert_type": "gap",
                "message": f"Documentation manquante — {gap}",
                "severity": "info",
            }
            alerts.append(alert)

    # 3. Analyse LLM pour détecter maintenance en retard + pannes récurrentes
    if wiki_pages:
        sample_wiki = "\n\n".join(p["content_md"][:2000] for p in wiki_pages[:5])
        prompt = f"""Analyse ce Machine Wiki industriel et identifie les alertes proactives :

{sample_wiki[:10000]}

Retourne ce JSON :
{{
  "alerts": [
    {{
      "type": "maintenance_overdue",
      "machine": "Nom machine",
      "message": "Description de l'alerte",
      "severity": "warning"
    }}
  ]
}}

Types possibles : "maintenance_overdue", "recurring_failure", "safety_risk"
Severities : "critical", "warning", "info"
Sois conservateur : ne génère des alertes que si clairement supporté par le texte.
"""
        try:
            result = llm_json([{"role": "user", "content": prompt}], timeout=60.0)
            for a in result.get("alerts", []):
                alerts.append({
                    "project_id": project_id,
                    "machine_ref": a.get("machine", ""),
                    "alert_type": a.get("type", "info"),
                    "message": a.get("message", ""),
                    "severity": a.get("severity", "info"),
                })
        except Exception as e:
            logger.warning(f"[alertes] LLM analyse échouée: {e}")

    # Insérer toutes les alertes en base
    for a in alerts:
        conn.execute(
            """INSERT INTO alerts (project_id, machine_ref, alert_type, message, severity)
               VALUES (?, ?, ?, ?, ?)""",
            (
                a["project_id"],
                a.get("machine_ref", ""),
                a["alert_type"],
                a["message"][:1000],
                a["severity"],
            ),
        )
    conn.commit()

    counter = f"{len(alerts)} alerte{'s' if len(alerts) != 1 else ''} générée{'s' if len(alerts) != 1 else ''}"
    update_agent(conn, job_id, "alert", "done", counter)
    logger.info(f"[alertes] {counter}")
    return alerts
