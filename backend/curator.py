"""
Curator — TraceAI Phase B.

Adapté de Hermes Agent agent/curator.py (MIT).

Agent background de maintenance des skills.
Déclenché automatiquement quand :
  - N ingestions ont eu lieu depuis la dernière passe (défaut : 10)
  - Ou appelé explicitement via l'endpoint /api/projects/{id}/curator

Responsabilités :
  - Consolider les skills qui se chevauchent
  - Archiver les skills devenus obsolètes (marquer deprecated)
  - Améliorer la qualité des skills auto-générés (descriptions vagues, etc.)
  - Créer des skills "parapluie" à partir de skills trop granulaires

Strict invariants (copiés de Hermes) :
  - Ne supprime JAMAIS — archive seulement (frontmatter: archived: true)
  - N'écrit QUE dans skills/{project_id}/
  - Utilise mistral-small (pas large)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "traceai.db"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "mistral-small-latest")
LLM_API_URL = "https://api.mistral.ai/v1/chat/completions"

CURATOR_INTERVAL = int(os.getenv("CURATOR_INTERVAL", "10"))  # ingestions entre passes

_CURATOR_SYSTEM = (
    "Tu es un curateur expert en organisation de bibliothèques de skills "
    "pour un système de maintenance industrielle. "
    "Tu améliores la qualité et la cohérence des skills sans en supprimer aucun."
)

_CURATOR_PROMPT = """Voici la liste des skills disponibles pour ce projet :

{skills_list}

Analyse cette collection et propose des améliorations :

1. **Consolidation** : Y a-t-il des skills qui se chevauchent et pourraient être fusionnés ?
   Si oui, propose un skill fusionné avec toutes les informations des deux.

2. **Qualité** : Y a-t-il des skills avec des descriptions vagues (pas de "Use when...") ?
   Si oui, propose une description améliorée.

3. **Obsolescence** : Y a-t-il des skills qui semblent spécifiques à une situation passée ?
   Si oui, marque-les deprecated dans le frontmatter.

Retourne un JSON :
{{
  "actions": [
    {{
      "type": "merge",
      "skills_merged": ["nom1", "nom2"],
      "new_skill": {{
        "name": "nom-fusionné",
        "content": "---\\nname: ...\\n---\\n..."
      }}
    }},
    {{
      "type": "improve_description",
      "skill": "nom",
      "new_description": "Use when..."
    }},
    {{
      "type": "archive",
      "skill": "nom",
      "reason": "pourquoi"
    }}
  ],
  "no_changes_needed": false
}}

Si rien ne nécessite de changement, retourne {{"no_changes_needed": true, "actions": []}}."""


# ---------------------------------------------------------------------------
# État du curator par projet
# ---------------------------------------------------------------------------

_curator_lock = threading.Lock()
_ingestion_counts: dict[int, int] = {}  # project_id → nombre d'ingestions depuis dernière passe


def record_ingestion(project_id: int) -> bool:
    """
    Incrémente le compteur d'ingestions pour un projet.
    Retourne True si le curator doit tourner (seuil atteint).
    """
    with _curator_lock:
        _ingestion_counts[project_id] = _ingestion_counts.get(project_id, 0) + 1
        count = _ingestion_counts[project_id]
        if count >= CURATOR_INTERVAL:
            _ingestion_counts[project_id] = 0
            return True
        return False


# ---------------------------------------------------------------------------
# Curator runner
# ---------------------------------------------------------------------------

def _run_curator(project_id: int) -> dict:
    """
    Analyse et améliore les skills du projet.
    Retourne un résumé des actions effectuées.
    """
    from skills_engine import (
        load_skills_index, list_skills, save_skill, parse_frontmatter
    )
    from pathlib import Path as _Path

    skills_dir = _Path(__file__).parent / "skills" / str(project_id)
    skills = list_skills(project_id)

    if len(skills) < 2:
        return {"message": "Pas assez de skills pour curator (minimum 2)", "actions": 0}

    # Construire le listing détaillé
    lines = []
    for s in skills:
        lines.append(f"### {s['name']}\nDescription : {s['description']}\nTags : {s.get('tags', [])}\n")
    skills_text = "\n".join(lines)

    prompt = _CURATOR_PROMPT.format(skills_list=skills_text)

    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(
                LLM_API_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={
                    "model": LLM_MODEL_FAST,
                    "messages": [
                        {"role": "system", "content": _CURATOR_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(result)
    except Exception as e:
        return {"error": str(e), "actions": 0}

    if data.get("no_changes_needed"):
        return {"message": "Aucune amélioration nécessaire", "actions": 0}

    actions_done = 0
    actions_log = []

    for action in data.get("actions", []):
        atype = action.get("type")
        try:
            if atype == "merge":
                # Créer le skill fusionné
                new_skill = action.get("new_skill", {})
                if new_skill.get("name") and new_skill.get("content"):
                    save_skill(new_skill["name"], project_id, new_skill["content"])
                    # Archiver les skills originaux
                    for old_name in action.get("skills_merged", []):
                        _archive_skill(old_name, project_id, skills_dir)
                    actions_done += 1
                    actions_log.append(f"Fusionné {action.get('skills_merged')} → {new_skill['name']}")

            elif atype == "improve_description":
                skill_name = action.get("skill", "")
                new_desc = action.get("new_description", "")
                if skill_name and new_desc:
                    _update_skill_description(skill_name, project_id, new_desc, skills_dir)
                    actions_done += 1
                    actions_log.append(f"Description améliorée : {skill_name}")

            elif atype == "archive":
                skill_name = action.get("skill", "")
                if skill_name:
                    _archive_skill(skill_name, project_id, skills_dir,
                                   reason=action.get("reason", ""))
                    actions_done += 1
                    actions_log.append(f"Archivé : {skill_name}")

        except Exception as e:
            logger.warning("[curator] Action %s échouée: %s", atype, e)

    logger.info("[curator] Passe terminée (projet %d) : %d actions", project_id, actions_done)
    return {"actions": actions_done, "log": actions_log}


def _archive_skill(name: str, project_id: int, skills_dir: Path,
                   reason: str = "") -> None:
    """Marque un skill comme archivé (jamais supprimé — invariant Hermes)."""
    from skills_engine import parse_frontmatter
    path = skills_dir / f"{name}.md"
    if not path.exists():
        return
    raw = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)
    fm["archived"] = True
    if reason:
        fm["archive_reason"] = reason
    # Reconstruire le frontmatter
    fm_lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, bool):
            fm_lines.append(f"{k}: {str(v).lower()}")
        else:
            fm_lines.append(f"{k}: {json.dumps(v) if isinstance(v, (list, dict)) else v}")
    fm_lines.append("---")
    new_content = "\n".join(fm_lines) + "\n" + body
    path.write_text(new_content, encoding="utf-8")


def _update_skill_description(name: str, project_id: int,
                               new_desc: str, skills_dir: Path) -> None:
    """Met à jour la description d'un skill existant."""
    from skills_engine import parse_frontmatter
    path = skills_dir / f"{name}.md"
    if not path.exists():
        return
    raw = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)
    fm["description"] = new_desc
    fm_lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, bool):
            fm_lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (list, dict)):
            fm_lines.append(f"{k}: {json.dumps(v)}")
        else:
            fm_lines.append(f"{k}: \"{v}\"")
    fm_lines.append("---")
    path.write_text("\n".join(fm_lines) + "\n" + body, encoding="utf-8")


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def maybe_run_curator(project_id: int) -> None:
    """
    Déclenche le curator en background si le seuil d'ingestions est atteint.
    Non-bloquant — tourne dans un thread daemon.
    Adapté de Hermes curator.maybe_run_curator().
    """
    if record_ingestion(project_id):
        thread = threading.Thread(
            target=_run_curator_safe,
            args=(project_id,),
            daemon=True,
            name=f"traceai-curator-{project_id}",
        )
        thread.start()
        logger.debug("[curator] Thread curator spawné (projet %d)", project_id)


def _run_curator_safe(project_id: int) -> None:
    try:
        result = _run_curator(project_id)
        if result.get("actions", 0) > 0:
            logger.info("[curator] %s", result)
    except Exception as e:
        logger.warning("[curator] Passe curator échouée: %s", e)


def run_curator_now(project_id: int) -> dict:
    """Exécute le curator immédiatement (synchrone). Pour l'endpoint API."""
    return _run_curator(project_id)
