"""
Background Review — TraceAI Phase B.

Adapté de Hermes Agent background_review.py (MIT).

Après chaque tour complexe (budget.used >= 3), spawne un thread daemon
qui relit la conversation et décide si skills ou mémoire doivent être
mis à jour. Tourne en silence — n'impacte jamais le prompt cache principal.

Différences vs Hermes :
  - LLM : Mistral (pas Anthropic)
  - Tools whitelist : save_memory + create_skill uniquement
  - Pas de callback UI — résultat dans les logs + fichiers
  - Budget : 8 itérations max (16 chez Hermes)
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

# ---------------------------------------------------------------------------
# Prompts de review — adaptés de Hermes background_review.py
# ---------------------------------------------------------------------------

_SKILL_REVIEW_PROMPT = """Relis la conversation ci-dessus et mets à jour la bibliothèque de skills.
Sois ACTIF — la plupart des sessions produisent au moins une mise à jour.
Une passe qui ne fait rien est une opportunité d'apprentissage manquée.

Signaux qui justifient une action :
  • L'utilisateur a corrigé ton approche, ton style, ou ta séquence d'étapes
  • Une technique non-triviale, un pattern de debugging, ou un workflow a émergé
  • Un skill chargé s'est révélé incorrect ou incomplet — patche-le maintenant
  • 5+ tool calls ont été nécessaires pour accomplir la tâche

Format des skills TraceAI :
---
name: nom-du-skill
description: "Use when ingérant/répondant/analysant des [type de doc]..."
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [tag1, tag2]
---

## Quand utiliser
...

## Patterns spécifiques
1. ...

## Pièges courants
- ...
---

Utilise create_skill pour créer ou mettre à jour.
Si vraiment rien à sauvegarder, réponds 'Rien à sauvegarder.' et arrête."""

_MEMORY_REVIEW_PROMPT = """Relis la conversation ci-dessus et envisage de sauvegarder en mémoire.

Focus sur :
1. Le client/site a-t-il révélé des informations durables ?
   (constructeur connu, conventions locales, noms de machines)
2. Des préférences de travail ont-elles été exprimées ?

Règle TraceAI : ne mémoriser QUE les faits durables > 7 jours.
Ne PAS mémoriser : avancement des jobs, SHA256, sessions passées.

Utilise save_memory si quelque chose en vaut la peine.
Sinon, réponds 'Rien à mémoriser.' et arrête."""

_COMBINED_REVIEW_PROMPT = """Relis la conversation ci-dessus et mets à jour deux choses :

**Mémoire** : faits durables sur le projet/client/machine.
Les mémoriser si : constructeur, site, conventions locales, préférences.
NE PAS mémoriser : avancement, sessions, SHA256, éphémère.

**Skills** : patterns réutilisables pour ce type de tâche.
Sois ACTIF — la plupart des sessions produisent au moins un skill.
Signaux : correction de ton approche, pattern non-trivial découvert,
skill chargé qui était incomplet.

Utilise save_memory et/ou create_skill selon les signaux.
Si vraiment rien sur les deux dimensions, réponds 'Rien à sauvegarder.' et arrête."""

# Tools whitelist pour le review agent (memory + skills uniquement)
_REVIEW_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Sauvegarde un fait durable sur le projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_skill",
            "description": "Crée ou met à jour un skill réutilisable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["name", "content"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Thread worker
# ---------------------------------------------------------------------------

def _run_review(
    project_id: int,
    messages_snapshot: list[dict],
    prompt: str,
    cached_system_prompt: str,
) -> None:
    """
    Worker exécuté dans un thread daemon.
    Relit la conversation, exécute save_memory / create_skill si nécessaire.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # Construire les messages pour le review agent
        # On hérite le system prompt caché du parent (même prefix cache)
        review_messages = list(messages_snapshot)
        review_messages.append({"role": "user", "content": prompt})

        actions: list[str] = []
        max_iters = 8

        for _ in range(max_iters):
            payload = {
                "model": LLM_MODEL_FAST,
                "messages": [
                    {"role": "system", "content": cached_system_prompt},
                ] + review_messages,
                "tools": _REVIEW_TOOLS,
            }

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    LLM_API_URL,
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json=payload,
                )

            if resp.status_code == 429:
                break
            if not resp.is_success:
                break

            msg = resp.json()["choices"][0]["message"]
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                break

            review_messages.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    fn_args = {}

                result = _execute_review_tool(fn_name, fn_args, project_id, conn)
                result_data = json.loads(result)
                if result_data.get("success"):
                    actions.append(fn_name)

                review_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "name": fn_name,
                    "content": result,
                })

        if actions:
            summary = " · ".join(dict.fromkeys(actions))
            logger.info("[review] Auto-amélioration : %s (projet %d)", summary, project_id)

        conn.close()

    except Exception as e:
        logger.debug("[review] Background review échoué: %s", e)


def _execute_review_tool(name: str, args: dict,
                          project_id: int,
                          conn: sqlite3.Connection) -> str:
    """Exécute uniquement les tools memory + skill (whitelist stricte)."""
    try:
        if name == "save_memory":
            from memory_engine import save_memory
            result = save_memory(
                project_id,
                args.get("key", ""),
                args.get("value", ""),
                conn,
            )
            return json.dumps(result, ensure_ascii=False)

        if name == "create_skill":
            from skills_engine import save_skill
            save_skill(args["name"], project_id, args["content"])
            return json.dumps({"success": True, "name": args["name"]},
                              ensure_ascii=False)

        # Tout autre tool → refusé (whitelist)
        return json.dumps({"success": False, "error": f"Tool '{name}' non autorisé en review"})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def spawn_background_review(
    project_id: int,
    messages_snapshot: list[dict],
    cached_system_prompt: str,
    *,
    review_memory: bool = False,
    review_skills: bool = True,
) -> None:
    """
    Spawne un thread daemon de review post-tour.
    Adapté de Hermes spawn_background_review_thread().

    Ne bloque JAMAIS le thread principal.
    Le snapshot des messages est passé par valeur (copie) pour isolation.
    """
    if review_memory and review_skills:
        prompt = _COMBINED_REVIEW_PROMPT
    elif review_memory:
        prompt = _MEMORY_REVIEW_PROMPT
    else:
        prompt = _SKILL_REVIEW_PROMPT

    snapshot = list(messages_snapshot)  # copie pour isolation

    thread = threading.Thread(
        target=_run_review,
        args=(project_id, snapshot, prompt, cached_system_prompt),
        daemon=True,
        name=f"traceai-review-{project_id}",
    )
    thread.start()
    logger.debug("[review] Thread review spawné (projet %d)", project_id)
