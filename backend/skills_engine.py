"""
Skills Engine — TraceAI Phase B.

Gestion des skills auto-améliorés par projet.
Chaque skill est un fichier .md avec frontmatter YAML + body markdown.

Références Hermes (code copié verbatim indiqué) :
  - agent/skill_utils.py       → parse_frontmatter() (copié verbatim)
  - tools/skills_tool.py       → MAX_NAME_LENGTH, MAX_DESCRIPTION_LENGTH,
                                  _INJECTION_PATTERNS, structure SKILL.md
  - prompt_builder.py          → SKILLS_GUIDANCE (copié verbatim),
                                  format index "- name: description"
  - agent/conversation_loop.py → nudge post-tour : budget.used >= 5
                                  → trigger_skill_update()

Nudge post-tour (adapté de conversation_loop.py ligne 589) :
  Après chaque tâche avec budget.used >= 5 (même seuil que Hermes),
  trigger_skill_update() appelle mistral-small pour décider si un skill
  doit être créé ou mis à jour.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes — copiées de tools/skills_tool.py
# ---------------------------------------------------------------------------

MAX_NAME_LENGTH = 64        # Copié de skills_tool.py
MAX_DESCRIPTION_LENGTH = 1024

SKILLS_DIR_BASE = Path(__file__).parent / "skills"

# Copié de tools/skills_tool.py _INJECTION_PATTERNS
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "you are now",
    "disregard your",
    "forget your instructions",
    "new instructions:",
    "system prompt:",
    "<system>",
]

# Copié verbatim de prompt_builder.py SKILLS_GUIDANCE
SKILLS_GUIDANCE = (
    "After completing a complex task (5+ tool calls), fixing a tricky error, "
    "or discovering a non-trivial workflow, save the approach as a "
    "skill with the create_skill tool so you can reuse it next time.\n"
    "When using a skill and finding it outdated, incomplete, or wrong, "
    "patch it immediately — don't wait to be asked. "
    "Skills that aren't maintained become liabilities."
)


# ---------------------------------------------------------------------------
# parse_frontmatter — copié verbatim de agent/skill_utils.py
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from a markdown string.
    Returns (frontmatter_dict, remaining_body).
    Copié verbatim de Hermes agent/skill_utils.py.
    """
    frontmatter: dict[str, Any] = {}
    body = content

    if not content.startswith("---"):
        return frontmatter, body

    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return frontmatter, body

    yaml_content = content[3: end_match.start() + 3]
    body = content[end_match.end() + 3:]

    try:
        import yaml
        loader = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader
        parsed = yaml.load(yaml_content, Loader=loader)
        if isinstance(parsed, dict):
            frontmatter = parsed
    except Exception:
        for line in yaml_content.strip().split("\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, body


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_skill(name: str, content: str) -> None:
    """
    Valide un skill avant sauvegarde.
    Contraintes copiées de skills_tool.py (MAX_NAME_LENGTH, MAX_DESCRIPTION_LENGTH).
    Raise ValueError si invalide.
    """
    # Nom : lowercase, tirets, ≤64 chars
    if not name or len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Nom skill invalide: '{name}' (max {MAX_NAME_LENGTH} chars)")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
        raise ValueError(f"Nom skill '{name}' invalide : lowercase, tirets uniquement, commence par lettre/chiffre")

    # Taille totale ≤100 000 chars
    if len(content) > 100_000:
        raise ValueError(f"Skill '{name}' trop grand ({len(content)} chars, max 100 000)")

    # Frontmatter obligatoire
    fm, body = parse_frontmatter(content)
    if not fm.get("name"):
        raise ValueError(f"Skill '{name}' : frontmatter 'name' manquant")
    if not fm.get("description"):
        raise ValueError(f"Skill '{name}' : frontmatter 'description' manquant")

    # Description : ≤1024 chars, commence par "Use when"
    desc = str(fm["description"])
    if len(desc) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(
            f"Skill '{name}' : description trop longue ({len(desc)} chars, max {MAX_DESCRIPTION_LENGTH})"
        )
    if not desc.strip().startswith("Use when"):
        raise ValueError(
            f"Skill '{name}' : description doit commencer par 'Use when...'"
        )

    # Body non vide
    if not body.strip():
        raise ValueError(f"Skill '{name}' : body vide")

    # Anti-injection (copié de tools/skills_tool.py)
    content_lower = content.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in content_lower:
            raise ValueError(
                f"Skill '{name}' : contenu suspect (pattern '{pattern}')"
            )


# ---------------------------------------------------------------------------
# Chemin
# ---------------------------------------------------------------------------

def _skills_dir(project_id: int) -> Path:
    return SKILLS_DIR_BASE / str(project_id)


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

def load_skills_index(project_id: int) -> str:
    """
    Retourne l'index des skills disponibles pour ce projet.
    Format : "- nom: description" (une ligne par skill).

    Adapté de prompt_builder.py build_skills_system_prompt() :
    même format compact pour injection dans le system prompt.
    """
    skills_dir = _skills_dir(project_id)
    if not skills_dir.exists():
        return ""

    lines = []
    for skill_file in sorted(skills_dir.glob("*.md")):
        try:
            raw = skill_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(raw)
            skill_name = fm.get("name") or skill_file.stem
            desc = str(fm.get("description", "")).strip().strip("'\"")
            if len(desc) > 80:
                desc = desc[:77] + "..."
            lines.append(f"- {skill_name}: {desc}")
        except Exception as e:
            logger.debug("[skills] Erreur lecture %s: %s", skill_file.name, e)

    return "\n".join(lines)


def build_skills_prompt_block(project_id: int) -> str:
    """
    Construit le bloc skills pour le system prompt.
    Adapté de prompt_builder.py build_skills_system_prompt().
    """
    index = load_skills_index(project_id)
    if not index:
        return ""
    return (
        "## Skills disponibles\n"
        "Si un skill est pertinent pour la tâche, charge-le avec load_skill(name).\n"
        f"<available_skills>\n{index}\n</available_skills>"
    )


# ---------------------------------------------------------------------------
# Chargement / sauvegarde
# ---------------------------------------------------------------------------

def load_skill(name: str, project_id: int) -> str:
    """
    Charge le body (sans frontmatter) d'un skill par son nom.
    Retourne '' si le skill n'existe pas.
    """
    path = _skills_dir(project_id) / f"{name}.md"
    if not path.exists():
        return ""
    try:
        raw = path.read_text(encoding="utf-8")
        _, body = parse_frontmatter(raw)
        return body.strip()
    except Exception as e:
        logger.error("[skills] Erreur lecture skill '%s': %s", name, e)
        return ""


def save_skill(name: str, project_id: int, content: str) -> None:
    """
    Crée ou met à jour un skill après validation.
    Adapté de tools/skills_tool.py skill_manage(action='create'/'patch').
    """
    validate_skill(name, content)
    skills_dir = _skills_dir(project_id)
    skills_dir.mkdir(parents=True, exist_ok=True)
    path = skills_dir / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    action = "mis à jour" if path.exists() else "créé"
    logger.info("[skills] Skill '%s' %s (projet %d)", name, action, project_id)


def list_skills(project_id: int) -> list[dict[str, Any]]:
    """Liste tous les skills d'un projet avec leurs métadonnées."""
    skills_dir = _skills_dir(project_id)
    if not skills_dir.exists():
        return []
    result = []
    for skill_file in sorted(skills_dir.glob("*.md")):
        try:
            raw = skill_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(raw)
            result.append({
                "name": fm.get("name") or skill_file.stem,
                "description": str(fm.get("description", "")).strip("'\""),
                "version": fm.get("version", ""),
                "tags": fm.get("metadata", {}).get("hermes", {}).get("tags", []),
                "size": len(raw),
            })
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Nudge post-tour — adapté de conversation_loop.py _iters_since_skill
# ---------------------------------------------------------------------------

def trigger_skill_update(project_id: int, task: str,
                          messages: list[dict]) -> None:
    """
    Déclenchée après une tâche complexe (budget.used >= 5).
    Appelle mistral-SMALL pour réfléchir sur les patterns appris.
    Si un skill doit être créé/mis à jour → save_skill().

    Adapté du nudge post-tour de conversation_loop.py (ligne 589).
    Utilise mistral-small (pas large) — même logique que Hermes qui
    utilise un modèle auxiliaire pour la réflexion post-tour.
    """
    import os
    import json as _json
    from agents.utils import llm_json

    # Extraire les noms des tools appelés cette session
    tool_calls_summary = []
    for msg in messages:
        if msg.get("role") == "assistant":
            for tc in (msg.get("tool_calls") or []):
                if isinstance(tc, dict) and "function" in tc:
                    tool_calls_summary.append(tc["function"].get("name", ""))

    # Charger l'index des skills existants
    existing = load_skills_index(project_id)

    reflection_prompt = f"""Tu viens de traiter cette tâche pour un projet de maintenance industrielle :
"{task[:300]}"

Tools utilisés : {', '.join(dict.fromkeys(tool_calls_summary)) or 'aucun'}

Skills déjà existants pour ce projet :
{existing or '(aucun)'}

Question : As-tu découvert un pattern, une stratégie ou un savoir-faire qui mérite
d'être sauvegardé en skill pour les prochains documents similaires ?

Si OUI, retourne :
{{
  "create_skill": true,
  "name": "nom-du-skill",
  "description": "Use when ...",
  "content": "---\\nname: nom-du-skill\\ndescription: \\"Use when ...\\"\\nversion: 1.0.0\\nauthor: TraceAI\\nmetadata:\\n  hermes:\\n    tags: [tag1, tag2]\\n---\\n\\n# Titre\\n\\n## Quand utiliser\\n...\\n\\n## Patterns spécifiques\\n...\\n\\n## Pièges courants\\n...\\n\\n## Checklist de validation\\n- [ ] ..."
}}

Si NON (tâche simple, pattern déjà dans un skill existant, ou pas de nouveauté) :
{{"create_skill": false}}

Réponds UNIQUEMENT avec le JSON."""

    try:
        model_fast = os.getenv("LLM_MODEL_FAST", "mistral-small-latest")
        result = llm_json(
            [{"role": "user", "content": reflection_prompt}],
            timeout=60.0,
            model_override=model_fast,
        )

        if result.get("create_skill") and result.get("name") and result.get("content"):
            name = result["name"]
            content = result["content"]
            try:
                save_skill(name, project_id, content)
                logger.info("[skills] Skill '%s' créé automatiquement post-tour", name)
            except ValueError as e:
                logger.warning("[skills] Skill auto-généré invalide '%s': %s", name, e)

    except Exception as e:
        logger.debug("[skills] trigger_skill_update échoué (non-critique): %s", e)
