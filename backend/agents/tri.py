"""
Agent 2 — Tri & Dédoublonnage
Hash SHA256 chaque fichier. Élimine les doublons.
Classe en catégories : manuels, rapports, procédures, photos, catalogues, autre.
"""
import hashlib
import logging
import sqlite3
from pathlib import Path

from .utils import update_agent, append_log

logger = logging.getLogger(__name__)

CATEGORIES_BY_EXT = {
    ".pdf":  "manuel",
    ".docx": "rapport",
    ".doc":  "rapport",
    ".xlsx": "données",
    ".xls":  "données",
    ".jpg":  "photo",
    ".jpeg": "photo",
    ".png":  "photo",
    ".dwg":  "plan",
    ".dxf":  "plan",
    ".url":  "url",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def run(
    project_id: int,
    job_id: int,
    file_paths: list[Path],
    conn: sqlite3.Connection,
) -> list[Path]:
    """
    Dédoublonne et classe les fichiers.
    Vérifie les doublons dans le batch courant ET dans les runs précédents (via DB).
    Retourne uniquement les fichiers vraiment nouveaux.
    """
    update_agent(conn, job_id, "tri", "running", "")
    append_log(conn, job_id, "info", "tri", f"Hash SHA-256 · {len(file_paths)} fichiers")

    # Charger les hashes déjà traités pour ce projet (runs précédents)
    already_done: set[str] = {
        row[0]
        for row in conn.execute(
            "SELECT file_hash FROM documents WHERE project_id=? AND file_hash IS NOT NULL AND status='chunked'",
            (project_id,),
        ).fetchall()
    }

    seen_hashes: dict[str, Path] = {}
    unique: list[Path] = []
    duplicates = 0

    for path in file_paths:
        try:
            h = _sha256(path)
        except Exception:
            unique.append(path)
            continue

        if h in already_done:
            # Déjà traité dans un run précédent — ignorer silencieusement
            duplicates += 1
            logger.info(f"[tri] Déjà indexé (run précédent) : {path.name}")
            continue

        if h in seen_hashes:
            # Doublon dans le batch courant
            duplicates += 1
            logger.info(f"[tri] Doublon batch : {path.name} == {seen_hashes[h].name}")
            conn.execute(
                "UPDATE documents SET status='duplicate' WHERE project_id=? AND filename=?",
                (project_id, path.name),
            )
        else:
            seen_hashes[h] = path
            unique.append(path)
            cat = CATEGORIES_BY_EXT.get(path.suffix.lower(), "autre")
            conn.execute(
                "UPDATE documents SET file_hash=?, doc_type=? WHERE project_id=? AND filename=?",
                (h, cat, project_id, path.name),
            )

    conn.commit()
    counter = f"{len(unique)} nouveau{'x' if len(unique) > 1 else ''} · {duplicates} déjà indexé{'s' if duplicates > 1 else ''}"
    update_agent(conn, job_id, "tri", "done", counter)
    append_log(conn, job_id, "ok", "tri", f"Tri ✓ — {counter}")
    return unique
