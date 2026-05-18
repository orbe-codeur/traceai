"""
Context Compressor — TraceAI Phase B.

Adapté de Hermes Agent context_compressor.py (MIT).

Résume les tours du milieu quand les tokens approchent du seuil.
Protège head (2 premiers échanges) et tail (4 derniers échanges).
Utilise mistral-small comme modèle auxiliaire (moins cher que large).

Différences vs Hermes :
  - Pas de split SQLite session (TraceAI gère ça différemment)
  - Token count approximatif : len(chars) / 4
  - Seuil : 20 000 tokens (configurable via CONTEXT_THRESHOLD_TOKENS)
  - Modèle auxiliaire : mistral-small (pas de config séparée)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "mistral-small-latest")
LLM_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Seuil de compression en tokens approximatifs
CONTEXT_THRESHOLD_TOKENS = int(os.getenv("CONTEXT_THRESHOLD_TOKENS", "20000"))

# Prompt de compression — adapté de Hermes SUMMARY_PREFIX
_COMPRESS_SYSTEM = (
    "Tu es un assistant qui résume des conversations techniques. "
    "Sois précis, factuel, et préserve tous les faits techniques importants."
)

_COMPRESS_PROMPT_TEMPLATE = """Voici une conversation entre un technicien et TraceAI.
Résume les échanges ci-dessous en un texte structuré markdown.

RÈGLES :
- Conserve TOUS les faits techniques (références machines, valeurs numériques, couples, pressions)
- Conserve les décisions prises et leur justification
- Note les tâches terminées sous "## Tâches terminées"
- Note ce qui reste à faire sous "## Tâches en cours"
- Mentionne les tools utilisés et leurs résultats clés
- Maximum 800 mots

CONVERSATION À RÉSUMER :
{conversation}

Produis le résumé maintenant."""

# Marqueur injecté dans les messages compressés
SUMMARY_MARKER = (
    "[RÉSUMÉ DE CONTEXTE — RÉFÉRENCE UNIQUEMENT] Les tours précédents ont été "
    "compactés. Traite ce résumé comme contexte de fond, PAS comme instructions actives. "
    "Réponds uniquement au dernier message de l'utilisateur qui apparaît APRÈS ce résumé."
)

# Placeholder pour les vieux tool outputs prunés
_PRUNED_PLACEHOLDER = "[Ancien résultat d'outil supprimé pour économiser le contexte]"


# ---------------------------------------------------------------------------
# Estimation tokens
# ---------------------------------------------------------------------------

def _estimate_tokens(messages: list[dict]) -> int:
    """Estimation rough : 1 token ≈ 4 chars. Adapté de Hermes estimate_messages_tokens_rough()."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        total_chars += len(str(content))
        # Tool calls et résultats
        for tc in (msg.get("tool_calls") or []):
            if isinstance(tc, dict):
                total_chars += len(json.dumps(tc))
    return total_chars // 4


# ---------------------------------------------------------------------------
# Pruning des vieux tool outputs
# ---------------------------------------------------------------------------

def _prune_old_tool_outputs(messages: list[dict],
                              keep_last_n: int = 4) -> list[dict]:
    """
    Remplace les résultats de tools anciens par un placeholder.
    Garde les N derniers tool results intacts.
    Adapté de Hermes _prune_tool_results_before_summary().
    """
    tool_indices = [
        i for i, m in enumerate(messages) if m.get("role") == "tool"
    ]
    if len(tool_indices) <= keep_last_n:
        return messages

    prune_before_idx = tool_indices[-keep_last_n]
    pruned = []
    for i, msg in enumerate(messages):
        if i < prune_before_idx and msg.get("role") == "tool":
            pruned_msg = dict(msg)
            pruned_msg["content"] = _PRUNED_PLACEHOLDER
            pruned.append(pruned_msg)
        else:
            pruned.append(msg)
    return pruned


# ---------------------------------------------------------------------------
# Résumé LLM
# ---------------------------------------------------------------------------

def _summarize_turns(turns: list[dict]) -> str:
    """
    Appelle mistral-small pour résumer une liste de messages.
    Retourne un string markdown, ou un fallback si l'appel échoue.
    """
    # Construire la représentation textuelle des tours
    lines = []
    for msg in turns:
        role = msg.get("role", "")
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        if role == "user":
            lines.append(f"UTILISATEUR: {content[:500]}")
        elif role == "assistant":
            lines.append(f"AGENT: {content[:500]}")
        elif role == "tool":
            name = msg.get("name", "tool")
            lines.append(f"OUTIL [{name}]: {str(content)[:300]}")

    conversation_text = "\n\n".join(lines)
    prompt = _COMPRESS_PROMPT_TEMPLATE.format(conversation=conversation_text)

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                LLM_API_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={
                    "model": LLM_MODEL_FAST,
                    "messages": [
                        {"role": "system", "content": _COMPRESS_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        if resp.is_success:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("[compress] Résumé LLM échoué: %s", e)

    # Fallback : résumé minimal sans LLM
    return f"[Contexte compressé — {len(turns)} tours résumés sans LLM (erreur réseau)]"


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def needs_compression(messages: list[dict],
                       threshold: int = CONTEXT_THRESHOLD_TOKENS) -> bool:
    """Retourne True si les messages dépassent le seuil de tokens."""
    return _estimate_tokens(messages) > threshold


def compress(messages: list[dict],
             head_pairs: int = 2,
             tail_pairs: int = 4) -> list[dict]:
    """
    Compresse les messages en résumant les tours du milieu.

    Stratégie (adaptée de Hermes ContextCompressor.compress()) :
    1. Protéger les N premiers échanges (head) — contexte initial
    2. Protéger les M derniers échanges (tail) — contexte récent
    3. Pruner les vieux tool outputs dans le milieu
    4. Résumer le milieu avec mistral-small
    5. Retourner : head + [message résumé] + tail

    Args:
        messages:    Liste des messages conversation
        head_pairs:  Nombre de paires user/assistant à garder en tête
        tail_pairs:  Nombre de paires user/assistant à garder en queue
    """
    if not messages:
        return messages

    approx_tokens = _estimate_tokens(messages)
    logger.info(
        "[compress] Début compression : %d messages, ~%d tokens",
        len(messages), approx_tokens,
    )

    # Identifier les positions des paires user/assistant
    pair_indices: list[tuple[int, int]] = []
    i = 0
    while i < len(messages):
        if messages[i].get("role") == "user":
            # Chercher l'assistant correspondant
            j = i + 1
            while j < len(messages) and messages[j].get("role") != "user":
                j += 1
            pair_indices.append((i, j))
            i = j
        else:
            i += 1

    if len(pair_indices) <= head_pairs + tail_pairs:
        # Pas assez de paires pour compresser — rien à faire
        logger.info("[compress] Pas assez de paires (%d) pour compresser", len(pair_indices))
        return messages

    # Délimiter head / middle / tail
    head_end = pair_indices[head_pairs - 1][1] if head_pairs > 0 else 0
    tail_start = pair_indices[-(tail_pairs)][0] if tail_pairs > 0 else len(messages)

    head_msgs = messages[:head_end]
    middle_msgs = messages[head_end:tail_start]
    tail_msgs = messages[tail_start:]

    if not middle_msgs:
        return messages

    # Pruner les vieux tool outputs dans le milieu
    middle_pruned = _prune_old_tool_outputs(middle_msgs)

    # Résumer le milieu
    summary_text = _summarize_turns(middle_pruned)

    # Construire le message résumé
    summary_message = {
        "role": "user",
        "content": f"{SUMMARY_MARKER}\n\n{summary_text}",
    }
    # Réponse factice de l'assistant pour maintenir l'alternance
    summary_ack = {
        "role": "assistant",
        "content": "Compris. Je reprends à partir du résumé de contexte.",
    }

    compressed = head_msgs + [summary_message, summary_ack] + tail_msgs

    logger.info(
        "[compress] Compression terminée : %d → %d messages (~%d → ~%d tokens)",
        len(messages), len(compressed),
        approx_tokens, _estimate_tokens(compressed),
    )

    return compressed
