"""
Orchestrateur TraceAI — Multi-agent avec delegate_task.

Adapté de Hermes Agent tools/delegate_tool.py (MIT).

L'orchestrateur reçoit une tâche de haut niveau, la décompose,
et délègue à des sous-agents spécialisés via le tool delegate_task.
Les sous-agents tournent en parallèle dans un ThreadPoolExecutor.

Différences vs Hermes :
  - Pas de recursion (les enfants ne peuvent pas déléguer)
  - Toolset enfant limité au mode assigné (ingestion/chat/alerte)
  - Pas d'approbation interactive (auto-deny sur tout outil dangereux)
  - Résultats agrégés par l'orchestrateur avant réponse finale
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from typing import Any

from agent_core import TraceAIAgent, TOOL_SCHEMAS, _make_tool

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "traceai.db"

# Timeout par sous-agent (secondes)
SUBAGENT_TIMEOUT = int(os.getenv("SUBAGENT_TIMEOUT", "120"))

# Tools bloqués pour les sous-agents (adapté de Hermes DELEGATE_BLOCKED_TOOLS)
SUBAGENT_BLOCKED_TOOLS = frozenset([
    "delegate_task",   # pas de récursion
    "ask_clarification",  # pas d'interaction utilisateur depuis un sous-agent
])


# ---------------------------------------------------------------------------
# Tool schema delegate_task
# ---------------------------------------------------------------------------

DELEGATE_TASK_SCHEMA = _make_tool(
    "delegate_task",
    "Délègue une tâche à un sous-agent spécialisé. "
    "Plusieurs appels simultanés → exécution en parallèle. "
    "Utiliser pour : ingérer plusieurs documents, chercher dans plusieurs sources, "
    "ou lancer une analyse en background pendant qu'on fait autre chose.",
    {
        "task": {
            "type": "string",
            "description": "Description précise de la tâche à accomplir",
        },
        "mode": {
            "type": "string",
            "enum": ["chat", "ingestion", "alerte"],
            "description": "Mode du sous-agent : chat (recherche/réponse), "
                           "ingestion (traitement docs), alerte (surveillance)",
        },
        "context": {
            "type": "string",
            "description": "Contexte supplémentaire à passer au sous-agent "
                           "(ex: nom du fichier, machine concernée)",
        },
    },
    ["task", "mode"],
)

# Mode orchestration — tools disponibles
ORCHESTRATION_TOOLS = [
    DELEGATE_TASK_SCHEMA,
    _make_tool(
        "orient_wiki",
        "Lis SCHEMA + index + log du wiki pour planifier les délégations.",
        {},
    ),
    _make_tool(
        "search_wiki",
        "Recherche rapide dans le wiki pour décider quoi déléguer.",
        {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 3},
        },
        ["query"],
    ),
    _make_tool(
        "save_memory",
        "Sauvegarde un fait durable découvert pendant l'orchestration.",
        {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        ["key", "value"],
    ),
    _make_tool(
        "ask_clarification",
        "Pose une question à l'utilisateur quand la tâche est ambiguë.",
        {"question": {"type": "string"}},
        ["question"],
    ),
]


# ---------------------------------------------------------------------------
# Exécution d'un sous-agent
# ---------------------------------------------------------------------------

def _run_subagent(
    project_id: int,
    task: str,
    mode: str,
    context: str,
    parent_session_id: str | None,
) -> dict:
    """
    Exécute un sous-agent TraceAI dans un thread worker.
    Retourne le résultat agrégé.
    Adapté de Hermes delegate_tool._run_subagent().
    """
    try:
        full_task = task
        if context:
            full_task = f"{task}\n\nContexte additionnel : {context}"

        subagent = TraceAIAgent(project_id, DB_PATH)
        result = subagent.process(
            task=full_task,
            mode=mode,
            history=[],  # contexte isolé — pas d'historique parent
            session_id=None,  # pas de persistance session pour les sous-agents
        )
        return {
            "success": True,
            "mode": mode,
            "task": task[:100],
            "answer": result.get("answer", ""),
            "iterations": result.get("iterations", 0),
        }
    except Exception as e:
        logger.error("[orchestrator] Sous-agent %s échoué: %s", mode, e)
        return {
            "success": False,
            "mode": mode,
            "task": task[:100],
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# TraceAIOrchestratorAgent
# ---------------------------------------------------------------------------

class TraceAIOrchestratorAgent(TraceAIAgent):
    """
    Orchestrateur multi-agent TraceAI.

    Hérite de TraceAIAgent et surcharge le dispatch pour gérer delegate_task.
    Les sous-agents sont lancés en parallèle via ThreadPoolExecutor.

    Architecture inspirée de Hermes delegate_tool.py :
    - Parent context voit seulement delegate_task call + résumé résultat
    - Enfants ont contexte isolé (pas d'historique parent)
    - Enfants ne peuvent pas déléguer (SUBAGENT_BLOCKED_TOOLS)
    - Timeout par sous-agent configurable
    """

    # Pool réutilisé entre les appels (max 3 sous-agents simultanés)
    _executor: ThreadPoolExecutor | None = None

    def __init__(self, project_id: int, db_path: Path = DB_PATH):
        super().__init__(project_id, db_path)
        if TraceAIOrchestratorAgent._executor is None:
            TraceAIOrchestratorAgent._executor = ThreadPoolExecutor(
                max_workers=3,
                thread_name_prefix="traceai-subagent",
            )

    def process(self, task: str, mode: str = "orchestration",
                history: list[dict] | None = None,
                session_id: str | None = None) -> dict:
        """Mode orchestration : override pour injecter les tools d'orchestration."""
        # Injecter temporairement le mode orchestration dans TOOL_SCHEMAS
        from agent_core import TOOL_SCHEMAS as _TS
        _TS["orchestration"] = ORCHESTRATION_TOOLS
        try:
            result = super().process(
                task=task,
                mode="orchestration",
                history=history or [],
                session_id=session_id,
            )
        finally:
            _TS.pop("orchestration", None)
        return result

    def _dispatch(self, name: str, args: dict,
                   conn: sqlite3.Connection) -> Any:
        """Surcharge : ajoute delegate_task, délègue le reste au parent."""
        if name == "delegate_task":
            return self._tool_delegate_task(args, conn)
        return super()._dispatch(name, args, conn)

    def _tool_delegate_task(self, args: dict,
                             conn: sqlite3.Connection) -> dict:
        """
        Exécute un ou plusieurs sous-agents.
        Si appelé plusieurs fois dans le même tour → parallèle automatique.
        Adapté de Hermes delegate_tool.delegate_task().
        """
        task = args.get("task", "")
        mode = args.get("mode", "chat")
        context = args.get("context", "")

        if not task:
            return {"error": "Le paramètre 'task' est requis"}
        if mode not in ("chat", "ingestion", "alerte"):
            mode = "chat"

        logger.info(
            "[orchestrator] Délégation : mode=%s task=%s",
            mode, task[:60],
        )

        future = self._executor.submit(
            _run_subagent,
            self.project_id,
            task,
            mode,
            context,
            None,
        )

        try:
            result = future.result(timeout=SUBAGENT_TIMEOUT)
        except TimeoutError:
            result = {
                "success": False,
                "mode": mode,
                "task": task[:100],
                "error": f"Timeout après {SUBAGENT_TIMEOUT}s",
            }

        logger.info(
            "[orchestrator] Résultat sous-agent %s : success=%s iterations=%s",
            mode, result.get("success"), result.get("iterations"),
        )
        return result

    def _build_system_prompt(self, mode: str,
                              conn: sqlite3.Connection) -> str:
        """Ajoute la guidance orchestration au system prompt."""
        base = super()._build_system_prompt("chat", conn)
        orchestration_guidance = """
# Mode ORCHESTRATION
Tu coordonnes des sous-agents spécialisés.

1. Analyse la tâche de haut niveau
2. Décompose en sous-tâches indépendantes
3. Lance les sous-agents avec delegate_task (plusieurs appels = parallèle automatique)
4. Attends les résultats et agrège-les
5. Synthétise une réponse finale cohérente

RÈGLES :
- Les sous-agents ont un contexte ISOLÉ — donne-leur tout ce dont ils ont besoin dans 'task' et 'context'
- Préfère l'ingestion parallèle pour plusieurs documents
- L'orchestrateur ne fait PAS le travail lui-même — il délègue
- Si une sous-tâche échoue, continue avec les autres et signale l'échec dans la synthèse"""
        return base + orchestration_guidance
