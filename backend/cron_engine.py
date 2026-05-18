"""
Cron Engine — TraceAI Phase B.

Adapté de Hermes Agent cron/jobs.py + cron/scheduler.py (MIT).

Jobs stockés en SQLite (table cron_jobs) — adapté pour l'archi TraceAI.
Scheduler : thread daemon qui tick toutes les 60 secondes.
Sécurité : scan anti-injection sur les prompts (adapté de cronjob_tools.py).

Différences vs Hermes :
  - Stockage SQLite (pas JSON file)
  - Pas de croniter — schedules simples : interval_minutes ou cron_expr basique
  - Jobs scopés par project_id (multi-projet)
  - Exécution via TraceAIAgent.process() (pas AIAgent)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "traceai.db"
CRON_OUTPUT_DIR = Path(__file__).parent / "cron_output"

# Intervalle du tick scheduler (secondes)
TICK_INTERVAL = 60

# ---------------------------------------------------------------------------
# Anti-injection — adapté de Hermes _scan_cron_prompt (critical patterns only)
# ---------------------------------------------------------------------------

_CRON_THREAT_PATTERNS = [
    (r'ignore\s+(?:\w+\s+)*(?:previous|all|above|prior)\s+(?:\w+\s+)*instructions', "prompt_injection"),
    (r'do\s+not\s+tell\s+the\s+user', "deception_hide"),
    (r'system\s+prompt\s+override', "sys_prompt_override"),
    (r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', "disregard_rules"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass)', "read_secrets"),
    (r'rm\s+-rf\s+/', "destructive_rm"),
    (r'curl\s+[^\n]*\$\{?\w*(?:KEY|TOKEN|SECRET|PASSWORD|API)\w*\}?', "exfil_curl"),
]

_CRON_INVISIBLE_CHARS = {'​', '‌', '‍', '⁠', '﻿'}


def _scan_cron_prompt(prompt: str) -> str:
    """Scanne le prompt d'un job cron pour injections critiques.
    Retourne un message d'erreur si bloqué, chaîne vide si OK.
    Adapté de Hermes cronjob_tools._scan_cron_prompt().
    """
    for char in _CRON_INVISIBLE_CHARS:
        if char in prompt:
            return f"Bloqué : caractère invisible U+{ord(char):04X} détecté."
    for pattern, pid in _CRON_THREAT_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return f"Bloqué : pattern '{pid}' détecté dans le prompt."
    return ""


# ---------------------------------------------------------------------------
# Parse schedule — intervals simples + expressions cron basiques
# ---------------------------------------------------------------------------

def parse_schedule(schedule_str: str) -> dict:
    """
    Parse une expression de schedule en dict normalisé.

    Formats supportés :
      "every 30 minutes"   → {type: interval, minutes: 30}
      "every 2 hours"      → {type: interval, minutes: 120}
      "every day"          → {type: interval, minutes: 1440}
      "every night"        → {type: daily_at, hour: 2, minute: 0}
      "daily at 02:00"     → {type: daily_at, hour: 2, minute: 0}
      "0 2 * * *"          → {type: cron, expr: "0 2 * * *"}
    """
    s = schedule_str.strip().lower()

    # "every N minutes/hours"
    m = re.match(r'every\s+(\d+)\s+(minute|minutes|hour|hours)', s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        minutes = n if 'minute' in unit else n * 60
        return {"type": "interval", "minutes": minutes, "display": schedule_str}

    # "every day" / "every night"
    if s in ("every day", "every night", "nightly", "daily"):
        hour = 2 if "night" in s or s == "nightly" else 0
        return {"type": "daily_at", "hour": hour, "minute": 0, "display": schedule_str}

    # "daily at HH:MM"
    m = re.match(r'daily\s+at\s+(\d{1,2}):(\d{2})', s)
    if m:
        return {"type": "daily_at", "hour": int(m.group(1)),
                "minute": int(m.group(2)), "display": schedule_str}

    # "weekly" / "every week"
    if s in ("weekly", "every week"):
        return {"type": "interval", "minutes": 7 * 1440, "display": schedule_str}

    # Expression cron basique "MIN HOUR * * *"
    parts = s.split()
    if len(parts) == 5 and all(re.match(r'[\d\*/,-]+', p) for p in parts):
        return {"type": "cron", "expr": schedule_str, "display": schedule_str}

    raise ValueError(
        f"Format de schedule non reconnu : '{schedule_str}'. "
        "Utilisez : 'every 30 minutes', 'every 2 hours', 'every night', "
        "'daily at 02:00', ou une expression cron '0 2 * * *'."
    )


def _next_run_from_schedule(schedule: dict, from_dt: datetime | None = None) -> datetime:
    """Calcule la prochaine exécution à partir du schedule parsé."""
    now = from_dt or datetime.utcnow()

    if schedule["type"] == "interval":
        return now + timedelta(minutes=schedule["minutes"])

    if schedule["type"] == "daily_at":
        candidate = now.replace(
            hour=schedule["hour"], minute=schedule["minute"],
            second=0, microsecond=0,
        )
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if schedule["type"] == "cron":
        # Fallback : interval 24h si pas de croniter
        try:
            from croniter import croniter
            it = croniter(schedule["expr"], now)
            return it.get_next(datetime)
        except ImportError:
            return now + timedelta(hours=24)

    return now + timedelta(hours=1)


# ---------------------------------------------------------------------------
# Table SQL
# ---------------------------------------------------------------------------

CRON_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cron_jobs (
    id          TEXT PRIMARY KEY,
    project_id  INTEGER NOT NULL,
    name        TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'alerte',
    prompt      TEXT NOT NULL,
    schedule    TEXT NOT NULL,
    next_run_at TEXT,
    last_run_at TEXT,
    last_output TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_cron_table() -> None:
    conn = _get_conn()
    conn.executescript(CRON_TABLE_SQL)
    conn.close()


# ---------------------------------------------------------------------------
# CRUD Jobs
# ---------------------------------------------------------------------------

def create_job(project_id: int, name: str, mode: str,
               prompt: str, schedule_str: str) -> dict:
    """
    Crée un job cron.
    Adapté de Hermes cron/jobs.py create_job().
    """
    # Scan anti-injection
    err = _scan_cron_prompt(prompt)
    if err:
        raise ValueError(err)

    if mode not in ("chat", "ingestion", "alerte"):
        raise ValueError(f"Mode invalide : '{mode}'. Utiliser chat, ingestion ou alerte.")

    schedule = parse_schedule(schedule_str)
    next_run = _next_run_from_schedule(schedule)

    job_id = str(uuid.uuid4())[:8]
    conn = _get_conn()
    conn.execute(
        """INSERT INTO cron_jobs (id, project_id, name, mode, prompt, schedule,
           next_run_at, enabled, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))""",
        (job_id, project_id, name, mode, prompt,
         json.dumps(schedule), next_run.isoformat()),
    )
    conn.commit()
    conn.close()
    logger.info("[cron] Job créé : %s (%s, %s)", name, mode, schedule_str)
    return get_job(job_id)


def get_job(job_id: str) -> dict:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM cron_jobs WHERE id=?", (job_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise KeyError(f"Job '{job_id}' introuvable.")
    return _row_to_dict(row)


def list_jobs(project_id: int | None = None) -> list[dict]:
    conn = _get_conn()
    if project_id is not None:
        rows = conn.execute(
            "SELECT * FROM cron_jobs WHERE project_id=? ORDER BY next_run_at",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM cron_jobs ORDER BY project_id, next_run_at"
        ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def delete_job(job_id: str) -> None:
    conn = _get_conn()
    affected = conn.execute(
        "DELETE FROM cron_jobs WHERE id=?", (job_id,)
    ).rowcount
    conn.commit()
    conn.close()
    if not affected:
        raise KeyError(f"Job '{job_id}' introuvable.")


def pause_job(job_id: str) -> dict:
    conn = _get_conn()
    conn.execute("UPDATE cron_jobs SET enabled=0 WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    return get_job(job_id)


def resume_job(job_id: str) -> dict:
    conn = _get_conn()
    row = conn.execute(
        "SELECT schedule FROM cron_jobs WHERE id=?", (job_id,)
    ).fetchone()
    if not row:
        raise KeyError(f"Job '{job_id}' introuvable.")
    schedule = json.loads(row[0])
    next_run = _next_run_from_schedule(schedule)
    conn.execute(
        "UPDATE cron_jobs SET enabled=1, next_run_at=? WHERE id=?",
        (next_run.isoformat(), job_id),
    )
    conn.commit()
    conn.close()
    return get_job(job_id)


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["schedule"] = json.loads(d["schedule"])
    except Exception:
        pass
    return d


# ---------------------------------------------------------------------------
# Exécution d'un job
# ---------------------------------------------------------------------------

def run_job(job: dict) -> str:
    """
    Exécute un job cron via TraceAIAgent.
    Adapté de Hermes cron/scheduler.py run_job().
    Retourne la réponse (output).
    """
    from agent_core import TraceAIAgent

    project_id = job["project_id"]
    mode = job.get("mode", "alerte")
    prompt = job.get("prompt", "")

    logger.info("[cron] Exécution job '%s' (projet %d, mode %s)", job["name"], project_id, mode)

    try:
        agent = TraceAIAgent(project_id, DB_PATH)
        result = agent.process(task=prompt, mode=mode, history=[], session_id=None)
        output = result.get("answer", "")
    except Exception as e:
        output = f"[Erreur d'exécution] {e}"
        logger.error("[cron] Job '%s' échoué: %s", job["name"], e)

    # Sauvegarder l'output
    CRON_OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = CRON_OUTPUT_DIR / f"{job['id']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    output_file.write_text(
        f"# Job : {job['name']}\n\n"
        f"**Exécuté** : {datetime.utcnow().isoformat()}\n"
        f"**Mode** : {mode}\n\n"
        f"## Résultat\n\n{output}",
        encoding="utf-8",
    )

    # Mettre à jour last_run_at + next_run_at
    schedule = job.get("schedule", {})
    if isinstance(schedule, str):
        schedule = json.loads(schedule)
    next_run = _next_run_from_schedule(schedule)

    conn = _get_conn()
    conn.execute(
        """UPDATE cron_jobs SET last_run_at=datetime('now'), next_run_at=?, last_output=?
           WHERE id=?""",
        (next_run.isoformat(), output[:500], job["id"]),
    )
    conn.commit()
    conn.close()

    logger.info("[cron] Job '%s' terminé. Prochain run : %s", job["name"], next_run.isoformat())
    return output


# ---------------------------------------------------------------------------
# Trigger manuel
# ---------------------------------------------------------------------------

def trigger_job(job_id: str) -> dict:
    """Exécute un job immédiatement (hors schedule)."""
    job = get_job(job_id)
    if not job.get("enabled"):
        raise ValueError(f"Job '{job_id}' est désactivé. Réactivez-le d'abord.")
    output = run_job(job)
    return {"job_id": job_id, "output": output[:500], "executed_at": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Scheduler — tick toutes les 60 secondes
# ---------------------------------------------------------------------------

class CronScheduler:
    """
    Scheduler de jobs cron.
    Adapté de Hermes cron/scheduler.py.

    Tick toutes les TICK_INTERVAL secondes.
    Lance les jobs dus dans des threads séparés.
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Démarre le scheduler en background."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="traceai-cron-scheduler",
        )
        self._thread.start()
        logger.info("[cron] Scheduler démarré (tick toutes les %ds)", TICK_INTERVAL)

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.error("[cron] Erreur tick: %s", e)
            self._stop_event.wait(TICK_INTERVAL)

    def tick(self) -> list[str]:
        """
        Vérifie les jobs dus et les exécute.
        Retourne les IDs des jobs lancés.
        Adapté de Hermes cron/scheduler.py tick().
        """
        now_str = datetime.utcnow().isoformat()
        conn = _get_conn()
        due_rows = conn.execute(
            """SELECT * FROM cron_jobs
               WHERE enabled=1 AND (next_run_at IS NULL OR next_run_at <= ?)
               ORDER BY next_run_at""",
            (now_str,),
        ).fetchall()
        conn.close()

        launched = []
        for row in due_rows:
            job = _row_to_dict(row)
            thread = threading.Thread(
                target=self._run_job_safe,
                args=(job,),
                daemon=True,
                name=f"traceai-cron-{job['id']}",
            )
            thread.start()
            launched.append(job["id"])

        if launched:
            logger.info("[cron] Tick : %d job(s) lancé(s)", len(launched))
        return launched

    def _run_job_safe(self, job: dict) -> None:
        try:
            run_job(job)
        except Exception as e:
            logger.error("[cron] Job '%s' échoué: %s", job.get("name"), e)


# Instance globale du scheduler (démarrée au startup FastAPI)
_scheduler: CronScheduler | None = None


def get_scheduler() -> CronScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler()
    return _scheduler


def startup() -> None:
    """À appeler au startup FastAPI. Initialise la table + démarre le scheduler."""
    init_cron_table()
    get_scheduler().start()
