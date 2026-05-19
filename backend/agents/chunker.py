"""
Agent 4 — Chunker
Lit les fichiers .md produits par le parser et découpe en chunks.

Règles :
  # / ## / ### → frontière de section (nouveau chunk)
  Tableau markdown (lignes |) → chunk atomique (jamais découpé)
  Section longue (> MAX_CHARS) → découpe sur saut de paragraphe avec overlap
  Section courte → 1 chunk direct
"""
import logging
import re
import sqlite3
from pathlib import Path

from .utils import update_agent, append_log

logger = logging.getLogger(__name__)

MAX_CHARS = 6000    # ~1000 tokens — limite haute par chunk
OVERLAP   = 300     # ~50 tokens — overlap entre chunks longs


# ---------------------------------------------------------------------------
# MarkdownChunker
# ---------------------------------------------------------------------------

def _is_table_line(line: str) -> bool:
    return line.startswith("|")


def _extract_page_from_header(title: str) -> int | None:
    """Extrait le numéro de page depuis les commentaires Docling <!-- page=N -->."""
    m = re.search(r"<!--\s*page[=:]\s*(\d+)", title)
    return int(m.group(1)) if m else None


def chunk_markdown(md_text: str) -> list[dict]:
    """
    Découpe un document markdown en chunks structurés.
    Retourne [{title, content, level, page_ref, is_table, section_path}].
    """
    chunks: list[dict] = []
    lines = md_text.splitlines()

    current: dict = {"title": "", "level": 0, "lines": [], "page_ref": 0}
    section_stack: list[str] = []   # pile des titres pour section_path
    in_table = False
    table_lines: list[str] = []
    table_title = ""
    table_page = 0

    def flush_current():
        nonlocal current
        content = "\n".join(current["lines"]).strip()
        if not content:
            return
        title = current["title"]
        level = current["level"]
        page = current["page_ref"]

        # Section_path = breadcrumb jusqu'au titre courant
        path_parts = section_stack[:level] + ([title] if title else [])
        section_path = " > ".join(p for p in path_parts if p)

        # Découper si trop long
        if len(content) <= MAX_CHARS:
            chunks.append({
                "title":        title,
                "content":      content,
                "level":        level,
                "page_ref":     page,
                "is_table":     False,
                "section_path": section_path,
            })
        else:
            # Découpe sur double saut de ligne (paragraphes)
            paragraphs = re.split(r"\n\n+", content)
            buf = ""
            for para in paragraphs:
                if len(buf) + len(para) > MAX_CHARS and buf:
                    chunks.append({
                        "title":        title,
                        "content":      buf.strip(),
                        "level":        level,
                        "page_ref":     page,
                        "is_table":     False,
                        "section_path": section_path,
                    })
                    # Overlap : garder les derniers OVERLAP chars
                    buf = buf[-OVERLAP:] + "\n\n" + para
                else:
                    buf = (buf + "\n\n" + para).strip() if buf else para
            if buf.strip():
                chunks.append({
                    "title":        title,
                    "content":      buf.strip(),
                    "level":        level,
                    "page_ref":     page,
                    "is_table":     False,
                    "section_path": section_path,
                })
        current = {"title": "", "level": 0, "lines": [], "page_ref": page}

    def flush_table():
        nonlocal table_lines, in_table
        if not table_lines:
            return
        content = "\n".join(table_lines).strip()
        if content:
            level = current["level"]
            path_parts = section_stack[:level] + ([table_title] if table_title else [])
            section_path = " > ".join(p for p in path_parts if p)
            chunks.append({
                "title":        table_title or current["title"],
                "content":      content,
                "level":        level,
                "page_ref":     table_page or current["page_ref"],
                "is_table":     True,
                "section_path": section_path,
            })
        table_lines = []
        in_table = False

    for line in lines:
        stripped = line.rstrip()

        # Tableau : accumuler jusqu'à la fin du bloc
        if _is_table_line(stripped):
            if not in_table:
                # Début de tableau — flush le texte courant d'abord
                flush_current()
                in_table = True
                table_title = current["title"]
                table_page = current["page_ref"]
            table_lines.append(stripped)
            continue

        if in_table and not _is_table_line(stripped) and stripped != "":
            # Fin de tableau (ligne non-table non-vide)
            flush_table()

        if in_table and stripped == "":
            # Ligne vide pendant un tableau — peut être entre blocs, attendre
            table_lines.append(stripped)
            continue

        # Titre markdown #, ##, ###
        m = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if m:
            flush_current()
            level = len(m.group(1))
            title = m.group(2).strip()
            page = _extract_page_from_header(title) or current["page_ref"]

            # Mettre à jour la pile de sections
            while len(section_stack) >= level:
                section_stack.pop() if section_stack else None
            section_stack.append(title)

            current = {"title": title, "level": level, "lines": [], "page_ref": page}
            continue

        # Ligne normale
        current["lines"].append(stripped)

    # Flush final
    flush_table()
    flush_current()

    return chunks


# ---------------------------------------------------------------------------
# Agent run()
# ---------------------------------------------------------------------------

def run(
    project_id: int,
    job_id: int,
    parsed_docs: list[dict],
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Découpe tous les documents en chunks via MarkdownChunker.
    Lit le .md sur disque si disponible, sinon utilise le content brut.
    Insère en base et retourne la liste des chunks.
    """
    update_agent(conn, job_id, "chunk", "running", "")
    logger.info("[chunker] %d documents à découper", len(parsed_docs))

    all_chunks: list[dict] = []
    chunk_index = 0

    for doc in parsed_docs:
        doc_id   = doc["doc_id"]
        md_path  = doc.get("md_path")
        content  = doc.get("content", "")

        if not content and not md_path:
            continue

        conn.execute(
            "UPDATE documents SET status='chunking' WHERE id=?", (doc_id,)
        )
        conn.commit()

        # Lire le .md sur disque si disponible (plus fiable que le content en mémoire)
        if md_path and Path(md_path).exists():
            md_text = Path(md_path).read_text(encoding="utf-8")
            source = f"md:{Path(md_path).name}"
        else:
            md_text = content
            source = "content"

        blocks = chunk_markdown(md_text)
        logger.info("[chunker] %s — %s → %d blocs", doc.get("filename", "?"), source, len(blocks))

        # Récupérer machine_ref depuis la DB
        machine_ref_row = conn.execute(
            "SELECT machine_ref FROM documents WHERE id=?", (doc_id,)
        ).fetchone()
        machine_ref = machine_ref_row[0] if machine_ref_row else ""

        for block in blocks:
            cursor = conn.execute(
                """INSERT INTO chunks
                   (document_id, project_id, chunk_index, content,
                    page_ref, section_ref, machine_ref)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    doc_id,
                    project_id,
                    chunk_index,
                    block["content"],
                    block.get("page_ref"),
                    (block.get("section_path") or block.get("title", ""))[:255],
                    machine_ref,
                ),
            )
            all_chunks.append({
                "id":          cursor.lastrowid,
                "doc_id":      doc_id,
                "chunk_index": chunk_index,
                "content":     block["content"],
                "page_ref":    block.get("page_ref"),
                "section_ref": block.get("section_path") or block.get("title", ""),
                "machine_ref": machine_ref,
                "filename":    doc.get("filename", ""),
                "is_table":    block.get("is_table", False),
            })
            chunk_index += 1

        conn.execute("UPDATE documents SET status='chunked' WHERE id=?", (doc_id,))

    conn.commit()

    avg_len = int(sum(len(c["content"]) for c in all_chunks) / max(len(all_chunks), 1))
    avg_tok = avg_len // 4
    counter = f"{len(all_chunks)} chunks · ~{avg_tok} tokens moy."
    update_agent(conn, job_id, "chunk", "done", counter)
    logger.info("[chunker] %s", counter)
    return all_chunks
