"""Utilitaires partagés par tous les agents Phase 2."""
import datetime
import json
import logging
import os
import sqlite3
import threading
import time

import httpx

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "")
LLM_MODEL    = os.getenv("LLM_MODEL", "mistral-large-latest")

# URLs selon le provider
_URLS = {
    "ollama":  "http://localhost:11434/v1/chat/completions",
    "openai":  "https://api.openai.com/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
}
LLM_API_URL = _URLS.get(LLM_PROVIDER, _URLS["mistral"])

# Ollama n'a pas de rate limit → on peut aller plus vite
# Cloud Mistral/OpenAI → limiter à 1 appel à la fois pour éviter les 429
_MAX_PARALLEL = 3 if LLM_PROVIDER == "ollama" else 1
_SEM = threading.Semaphore(_MAX_PARALLEL)

# Délai minimal entre appels (cloud uniquement, Ollama = 0)
_CALL_DELAY = 0.0 if LLM_PROVIDER == "ollama" else 1.2


def _parse_json(content: str) -> dict:
    """Parse JSON robuste — gère les backticks markdown et le texte avant/après."""
    content = content.strip()
    # Retirer les blocs ```json ... ``` ou ``` ... ```
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    # Extraire le premier objet JSON { ... } ou tableau [ ... ]
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = content.find(start_char)
        end   = content.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass
    return json.loads(content)  # lève JSONDecodeError si vraiment invalide


def llm_json(messages: list[dict], timeout: float = 120.0, model_override: str | None = None) -> dict:
    """Appel LLM synchrone, retourne un dict JSON. Supporte Ollama et cloud."""
    model = model_override or LLM_MODEL
    with _SEM:
        if _CALL_DELAY > 0:
            time.sleep(_CALL_DELAY)

        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}

        if LLM_PROVIDER == "ollama":
            payload = {"model": model, "messages": messages, "format": "json", "stream": False}
        else:
            payload = {"model": model, "messages": messages, "response_format": {"type": "json_object"}}

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(LLM_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return _parse_json(content)


_EMBED_URL = "https://api.mistral.ai/v1/embeddings"
_EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "mistral-embed")
_EMBED_BATCH = 32


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Génère des embeddings via Mistral API par lots de _EMBED_BATCH."""
    results: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH):
        batch = texts[i : i + _EMBED_BATCH]
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                _EMBED_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={"model": _EMBED_MODEL, "input": batch},
            )
            resp.raise_for_status()
            results.extend(d["embedding"] for d in resp.json()["data"])
    return results


def update_agent(
    conn: sqlite3.Connection,
    job_id: int,
    agent_key: str,
    status: str,
    counter: str = "",
    progress: float | None = None,
):
    """Met à jour le statut d'un agent dans agents_json."""
    row = conn.execute(
        "SELECT agents_json FROM batch_jobs WHERE id=?", (job_id,)
    ).fetchone()
    agents: dict = json.loads(row[0] or "{}") if row else {}
    agents[agent_key] = {"status": status, "counter": counter}
    if progress is not None:
        agents[agent_key]["progress"] = progress
    conn.execute(
        "UPDATE batch_jobs SET agents_json=? WHERE id=?",
        (json.dumps(agents), job_id),
    )
    conn.commit()


def update_batch_files(conn: sqlite3.Connection, job_id: int,
                       processed: int, errors: int):
    conn.execute(
        "UPDATE batch_jobs SET processed_files=?, error_files=? WHERE id=?",
        (processed, errors, job_id),
    )
    conn.commit()


def append_log(
    conn: sqlite3.Connection,
    job_id: int,
    level: str,
    agent_key: str,
    message: str,
):
    """Ajoute une ligne de log dans logs_json (garde les 60 dernières)."""
    row = conn.execute(
        "SELECT logs_json FROM batch_jobs WHERE id=?", (job_id,)
    ).fetchone()
    logs: list = json.loads(row[0] or "[]") if row else []
    logs.append({
        "t":     datetime.datetime.now().strftime("%H:%M:%S"),
        "lvl":   level,
        "agent": agent_key,
        "msg":   message[:200],
    })
    logs = logs[-60:]
    conn.execute(
        "UPDATE batch_jobs SET logs_json=? WHERE id=?",
        (json.dumps(logs, ensure_ascii=False), job_id),
    )
    conn.commit()
    logger.info(f"[{agent_key}] {message}")


def job_should_stop(conn: sqlite3.Connection, job_id: int) -> bool:
    """Retourne True si le job a été annulé — permet aux agents de s'arrêter proprement."""
    row = conn.execute(
        "SELECT status FROM batch_jobs WHERE id=?", (job_id,)
    ).fetchone()
    return row and row[0] == "cancelled"
