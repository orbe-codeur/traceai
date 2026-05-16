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
    """Dédoublonne et classe les fichiers. Retourne la liste unique."""
    update_agent(conn, job_id, "tri", "running", "")
    append_log(conn, job_id, "info", "tri", f"Hash SHA-256 · {len(file_paths)} fichiers")

    seen_hashes: dict[str, Path] = {}
    unique: list[Path] = []
    duplicates = 0

    for path in file_paths:
        try:
            h = _sha256(path)
        except Exception:
            unique.append(path)
            continue

        if h in seen_hashes:
            duplicates += 1
            logger.info(f"[tri] Doublon : {path.name} == {seen_hashes[h].name}")
            # Marquer le document comme doublon
            conn.execute(
                "UPDATE documents SET status='duplicate' WHERE project_id=? AND filename=?",
                (project_id, path.name),
            )
        else:
            seen_hashes[h] = path
            unique.append(path)
            # Stocker le hash et la catégorie
            cat = CATEGORIES_BY_EXT.get(path.suffix.lower(), "autre")
            conn.execute(
                "UPDATE documents SET file_hash=?, doc_type=? WHERE project_id=? AND filename=?",
                (h, cat, project_id, path.name),
            )

    conn.commit()
    counter = f"{len(unique)} uniques · {duplicates} doublon{'s' if duplicates != 1 else ''} retiré{'s' if duplicates != 1 else ''}"
    update_agent(conn, job_id, "tri", "done", counter)
    append_log(conn, job_id, "ok", "tri", f"Tri ✓ — {counter}")
    return unique
