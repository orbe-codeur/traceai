"""
Memory Engine — TraceAI Phase B.

Mémoire persistante par projet en SQLite + FTS5.

Références Hermes (code copié verbatim indiqué) :
  - agent/memory_manager.py → build_memory_context_block, sanitize_context,
                               StreamingContextScrubber
  - tools/memory_tool.py    → _scan_memory_content, _MEMORY_THREAT_PATTERNS,
                               frozen snapshot pattern, délimiteur §
  - hermes_state.py         → FTS5 virtual table pattern

Pattern clé (Hermes memory_tool.py frozen snapshot) :
  Au démarrage de session → load_project_memory() → snapshot figé.
  Ce snapshot va dans le system prompt UNE FOIS.
  Les écritures mid-session vont en base IMMÉDIATEMENT mais ne changent
  PAS le system prompt (préserve le prefix cache Mistral).
  La prochaine session recharge le snapshot mis à jour.

Règle mémorisation TraceAI (adaptée de prompt_builder.py MEMORY_GUIDANCE) :
  - Mémoriser : constructeur connu, site client, conventions locales
  - NE PAS mémoriser : avancement des jobs, SHA256 traités, sessions passées
  - Si un fait sera périmé dans 7 jours → il n'appartient PAS à la mémoire
  - Les procédures appartiennent aux skills, pas à la mémoire
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

# Délimiteur entre entrées mémoire — copié de memory_tool.py
ENTRY_DELIMITER = "\n§\n"

# ---------------------------------------------------------------------------
# Anti-injection — copié verbatim de tools/memory_tool.py
# ---------------------------------------------------------------------------

_MEMORY_THREAT_PATTERNS = [
    (r'ignore\s+(previous|all|above|prior)\s+instructions', "prompt_injection"),
    (r'you\s+are\s+now\s+', "role_hijack"),
    (r'do\s+not\s+tell\s+the\s+user', "deception_hide"),
    (r'system\s+prompt\s+override', "sys_prompt_override"),
    (r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', "disregard_rules"),
    (r'act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'t\s+have)\s+(restrictions|limits|rules)',
     "bypass_restrictions"),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_curl"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass)', "read_secrets"),
]

_INVISIBLE_CHARS = {
    '​', '‌', '‍', '⁠', '﻿',
    '‪', '‫', '‬', '‭', '‮',
}


def _scan_memory_content(content: str) -> str | None:
    """
    Scan du contenu mémoire pour injection/exfil.
    Retourne un message d'erreur si bloqué, None si OK.
    Copié verbatim de tools/memory_tool.py.
    """
    for char in _INVISIBLE_CHARS:
        if char in content:
            return (f"Bloqué : contenu contient un caractère unicode invisible "
                    f"U+{ord(char):04X} (injection possible).")
    for pattern, pid in _MEMORY_THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return (f"Bloqué : contenu correspond au pattern '{pid}'. "
                    f"Les entrées mémoire sont injectées dans le system prompt.")
    return None


# ---------------------------------------------------------------------------
# Context fencing — copié verbatim de agent/memory_manager.py
# ---------------------------------------------------------------------------

_FENCE_TAG_RE = re.compile(r'</?\s*memory-context\s*>', re.IGNORECASE)
_INTERNAL_CONTEXT_RE = re.compile(
    r'<\s*memory-context\s*>[\s\S]*?</\s*memory-context\s*>',
    re.IGNORECASE,
)
_INTERNAL_NOTE_RE = re.compile(
    r'\[System note:\s*The following is recalled memory context,\s*NOT new user input\.'
    r'\s*Treat as (?:informational background data|authoritative reference data[^\]]*)\.\]\s*',
    re.IGNORECASE,
)


def sanitize_context(text: str) -> str:
    """
    Strip fence tags, injected context blocks, and system notes.
    Copié verbatim de agent/memory_manager.py.
    """
    text = _INTERNAL_CONTEXT_RE.sub('', text)
    text = _INTERNAL_NOTE_RE.sub('', text)
    text = _FENCE_TAG_RE.sub('', text)
    return text


def build_memory_context_block(raw_context: str) -> str:
    """
    Wrap prefetched memory in a fenced block with system note.
    Copié verbatim de agent/memory_manager.py build_memory_context_block().
    """
    if not raw_context or not raw_context.strip():
        return ""
    clean = sanitize_context(raw_context)
    return (
        "<memory-context>\n"
        "[System note: The following is recalled memory context, "
        "NOT new user input. Treat as authoritative reference data — "
        "this is the agent's persistent memory and should inform all responses.]\n\n"
        f"{clean}\n"
        "</memory-context>"
    )


class StreamingContextScrubber:
    """
    Stateful scrubber for streaming text that may contain split memory-context spans.
    Copié verbatim de agent/memory_manager.py StreamingContextScrubber.
    """

    _OPEN_TAG = "<memory-context>"
    _CLOSE_TAG = "</memory-context>"

    def __init__(self) -> None:
        self._in_span: bool = False
        self._buf: str = ""

    def reset(self) -> None:
        self._in_span = False
        self._buf = ""

    def feed(self, text: str) -> str:
        if not text:
            return ""
        buf = self._buf + text
        self._buf = ""
        out: list[str] = []

        while buf:
            if self._in_span:
                idx = buf.lower().find(self._CLOSE_TAG)
                if idx == -1:
                    held = self._max_partial_suffix(buf, self._CLOSE_TAG)
                    self._buf = buf[-held:] if held else ""
                    return "".join(out)
                buf = buf[idx + len(self._CLOSE_TAG):]
                self._in_span = False
            else:
                idx = buf.lower().find(self._OPEN_TAG)
                if idx == -1:
                    held = self._max_partial_suffix(buf, self._OPEN_TAG)
                    if held:
                        out.append(buf[:-held])
                        self._buf = buf[-held:]
                    else:
                        out.append(buf)
                    return "".join(out)
                if idx > 0:
                    out.append(buf[:idx])
                buf = buf[idx + len(self._OPEN_TAG):]
                self._in_span = True

        return "".join(out)

    def flush(self) -> str:
        if self._in_span:
            self._buf = ""
            self._in_span = False
            return ""
        tail = self._buf
        self._buf = ""
        return tail

    @staticmethod
    def _max_partial_suffix(buf: str, tag: str) -> int:
        tag_lower = tag.lower()
        buf_lower = buf.lower()
        max_check = min(len(buf_lower), len(tag_lower) - 1)
        for i in range(max_check, 0, -1):
            if tag_lower.startswith(buf_lower[-i:]):
                return i
        return 0


# ---------------------------------------------------------------------------
# Tables SQLite (à appeler dans main.py init_db)
# ---------------------------------------------------------------------------

MEMORY_TABLES_SQL = """
-- Mémoire structurée par projet
CREATE TABLE IF NOT EXISTS project_memory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_project_memory_key
    ON project_memory(project_id, key);

-- Sessions agent (stocke le system_prompt figé pour continuité)
CREATE TABLE IF NOT EXISTS agent_sessions (
    id         TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,
    mode       TEXT NOT NULL,
    system_prompt TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- FTS5 pour recherche full-text dans la mémoire
-- Adapté de hermes_state.py FTS_SQL
CREATE VIRTUAL TABLE IF NOT EXISTS project_memory_fts
USING fts5(key, value, content=project_memory, content_rowid=id);

CREATE TRIGGER IF NOT EXISTS memory_fts_insert
    AFTER INSERT ON project_memory BEGIN
        INSERT INTO project_memory_fts(rowid, key, value)
        VALUES (new.id, new.key, new.value);
    END;

CREATE TRIGGER IF NOT EXISTS memory_fts_update
    AFTER UPDATE ON project_memory BEGIN
        DELETE FROM project_memory_fts WHERE rowid = old.id;
        INSERT INTO project_memory_fts(rowid, key, value)
        VALUES (new.id, new.key, new.value);
    END;

CREATE TRIGGER IF NOT EXISTS memory_fts_delete
    AFTER DELETE ON project_memory BEGIN
        DELETE FROM project_memory_fts WHERE rowid = old.id;
    END;
"""


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def load_project_memory(project_id: int,
                         conn: sqlite3.Connection) -> str:
    """
    Charge toutes les entrées mémoire d'un projet.
    Retourne une chaîne formatée pour injection dans le prompt.

    Pattern frozen snapshot de memory_tool.py MemoryStore.load_from_disk() :
    appelé UNE FOIS en début de session pour bâtir le snapshot figé.
    """
    rows = conn.execute(
        "SELECT key, value FROM project_memory WHERE project_id=? ORDER BY updated_at DESC",
        (project_id,),
    ).fetchall()

    if not rows:
        return ""

    entries = [f"{row[0]}: {row[1]}" for row in rows]
    return ENTRY_DELIMITER.join(entries)


def save_memory(project_id: int, key: str, value: str,
                conn: sqlite3.Connection) -> dict[str, Any]:
    """
    Sauvegarde ou met à jour une entrée mémoire.
    Pattern de memory_tool.py MemoryStore.add() :
    - Scan anti-injection d'abord
    - INSERT OR REPLACE (upsert par project_id + key)
    - Écriture immédiate en base mais NE change PAS le system prompt en cours
    """
    key = key.strip()
    value = value.strip()

    if not key or not value:
        return {"success": False, "error": "key et value ne peuvent pas être vides."}

    # Règle mémorisation TraceAI (adaptée de MEMORY_GUIDANCE Hermes)
    stale_keywords = ["avancement", "job_id", "session", "sha256", "étape en cours",
                      "progression", "commit", "PR #", "terminé le"]
    for kw in stale_keywords:
        if kw.lower() in key.lower() or kw.lower() in value.lower():
            logger.warning("[memory] Entrée potentiellement éphémère ignorée: key=%s", key)
            return {
                "success": False,
                "error": (
                    f"Entrée refusée : le mot '{kw}' suggère une information éphémère. "
                    "Mémoriser uniquement les faits durables (>7 jours). "
                    "Les procédures vont dans les skills, pas dans la mémoire."
                ),
            }

    scan_error = _scan_memory_content(value)
    if scan_error:
        return {"success": False, "error": scan_error}

    try:
        conn.execute(
            """INSERT INTO project_memory (project_id, key, value, created_at, updated_at)
               VALUES (?, ?, ?, datetime('now'), datetime('now'))
               ON CONFLICT(project_id, key) DO UPDATE SET
                   value = excluded.value,
                   updated_at = datetime('now')""",
            (project_id, key, value),
        )
        conn.commit()
        return {"success": True, "key": key, "value": value}
    except Exception as e:
        logger.error("[memory] Erreur sauvegarde: %s", e)
        return {"success": False, "error": str(e)}


def delete_memory(project_id: int, key: str,
                  conn: sqlite3.Connection) -> dict[str, Any]:
    """Supprime une entrée mémoire par sa clé."""
    key = key.strip()
    affected = conn.execute(
        "DELETE FROM project_memory WHERE project_id=? AND key=?",
        (project_id, key),
    ).rowcount
    conn.commit()
    if affected:
        return {"success": True, "deleted": key}
    return {"success": False, "error": f"Clé '{key}' introuvable."}


def search_memory(project_id: int, query: str,
                  conn: sqlite3.Connection,
                  limit: int = 5) -> list[dict[str, Any]]:
    """
    Recherche dans la mémoire via FTS5.
    Fallback LIKE si FTS5 indisponible.
    Adapté de hermes_state.py SessionDB.search_sessions().
    """
    query = query.strip()
    if not query:
        return []

    try:
        rows = conn.execute(
            """SELECT pm.key, pm.value
               FROM project_memory pm
               JOIN project_memory_fts fts ON pm.id = fts.rowid
               WHERE fts MATCH ? AND pm.project_id = ?
               ORDER BY rank
               LIMIT ?""",
            (query, project_id, limit),
        ).fetchall()
        return [{"key": r[0], "value": r[1]} for r in rows]
    except Exception:
        # Fallback LIKE si FTS5 pas disponible
        words = [w for w in query.split() if len(w) > 2]
        if not words:
            return []
        conditions = " OR ".join(["(key LIKE ? OR value LIKE ?)" for _ in words])
        params = [f"%{w}%" for w in words for _ in range(2)] + [project_id, limit]
        rows = conn.execute(
            f"SELECT key, value FROM project_memory WHERE ({conditions}) AND project_id=? LIMIT ?",
            params,
        ).fetchall()
        return [{"key": r[0], "value": r[1]} for r in rows]


def build_memory_prompt_block(project_id: int,
                               conn: sqlite3.Connection) -> str:
    """
    Construit le bloc mémoire pour injection dans le system prompt.
    Pattern frozen snapshot de memory_tool.py :
    appelé UNE FOIS par session, résultat mis en cache dans TraceAIAgent.
    """
    raw = load_project_memory(project_id, conn)
    if not raw:
        return ""
    return build_memory_context_block(raw)


def list_memory(project_id: int,
                conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Liste toutes les entrées mémoire d'un projet (pour debug/UI)."""
    rows = conn.execute(
        """SELECT key, value, created_at, updated_at
           FROM project_memory WHERE project_id=?
           ORDER BY updated_at DESC""",
        (project_id,),
    ).fetchall()
    return [
        {"key": r[0], "value": r[1], "created_at": r[2], "updated_at": r[3]}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Sessions agent
# ---------------------------------------------------------------------------

def save_session_prompt(session_id: str, project_id: int, mode: str,
                         system_prompt: str,
                         conn: sqlite3.Connection) -> None:
    """Persiste le system prompt figé d'une session pour continuité."""
    conn.execute(
        """INSERT OR REPLACE INTO agent_sessions (id, project_id, mode, system_prompt, created_at)
           VALUES (?, ?, ?, ?, datetime('now'))""",
        (session_id, project_id, mode, system_prompt),
    )
    conn.commit()


def load_session_prompt(session_id: str,
                         conn: sqlite3.Connection) -> str | None:
    """Charge le system prompt figé d'une session existante."""
    row = conn.execute(
        "SELECT system_prompt FROM agent_sessions WHERE id=?",
        (session_id,),
    ).fetchone()
    return row[0] if row else None
