"""
Agent 4 — Chunker
Découpe par sections/titres, PAS par taille fixe.
Taille cible 500-1000 tokens (~3000-6000 chars). Overlap 50 tokens (~300 chars).
Chaque chunk garde : content, page_ref, section_ref, titre.
"""
import logging
import re
import sqlite3

from .utils import update_agent

logger = logging.getLogger(__name__)

TARGET_CHARS = 4000   # ~650 tokens
MAX_CHARS    = 6000   # ~1000 tokens
OVERLAP      = 300    # ~50 tokens


def _detect_sections(text: str) -> list[dict]:
    """
    Détecte les titres de sections et retourne des blocs {title, content, page_ref}.
    Cherche d'abord les marqueurs --- PAGE X ---, puis les lignes en MAJUSCULES
    ou les patterns de titres (chiffres + point + texte).
    """
    # Diviser par pages
    page_pattern = re.compile(r"--- PAGE (\d+) ---")
    pages = page_pattern.split(text)

    blocks = []
    current_page = 0

    if len(pages) <= 1:
        # Pas de marqueurs de page → découpe par titres seuls
        blocks = _split_by_headings(text, 0)
    else:
        # pages[0] = texte avant la première page (souvent vide)
        # pages[1] = numéro de page, pages[2] = contenu, etc.
        for i in range(1, len(pages), 2):
            try:
                current_page = int(pages[i])
            except ValueError:
                pass
            content = pages[i + 1] if i + 1 < len(pages) else ""
            sub_blocks = _split_by_headings(content, current_page)
            blocks.extend(sub_blocks)

    return blocks


def _split_by_headings(text: str, page_ref: int) -> list[dict]:
    """Divise le texte en sections via heuristiques de titres."""
    # Patterns de titres : "1.2.3 Titre", "TITRE EN MAJUSCULES", "Titre :"
    heading_re = re.compile(
        r"^(?:"
        r"\d+(?:\.\d+)*\.?\s+[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][^\n]{2,60}"  # 1.2 Titre
        r"|[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ\s]{4,60}"      # TITRE MAJUSCULES
        r")",
        re.MULTILINE,
    )

    positions = [(m.start(), m.group()) for m in heading_re.finditer(text)]

    if not positions:
        return [{"title": "", "content": text.strip(), "page_ref": page_ref}]

    blocks = []
    for idx, (pos, title) in enumerate(positions):
        start = pos
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
        content = text[start:end].strip()
        if content:
            blocks.append({
                "title": title.strip()[:120],
                "content": content,
                "page_ref": page_ref,
            })
    return blocks


def _chunk_block(block: dict) -> list[dict]:
    """
    Découpe un bloc trop grand en chunks avec overlap.
    """
    text = block["content"]
    if len(text) <= MAX_CHARS:
        return [block]

    chunks = []
    start = 0
    while start < len(text):
        end = start + TARGET_CHARS
        # Couper sur un saut de ligne si possible
        if end < len(text):
            nl = text.rfind("\n", start + TARGET_CHARS // 2, end)
            if nl != -1:
                end = nl
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "title": block["title"],
                "content": chunk_text,
                "page_ref": block["page_ref"],
            })
        start = end - OVERLAP
        if start >= len(text):
            break

    return chunks


def run(
    project_id: int,
    job_id: int,
    parsed_docs: list[dict],
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Découpe tous les documents parsés en chunks.
    Insère en base (table chunks).
    Retourne la liste des chunks avec leurs IDs.
    """
    update_agent(conn, job_id, "chunk", "running", "")
    logger.info(f"[chunker] {len(parsed_docs)} documents à découper")

    all_chunks: list[dict] = []
    chunk_index = 0

    for doc in parsed_docs:
        doc_id = doc["doc_id"]
        content = doc["content"]
        if not content or not content.strip():
            continue

        conn.execute(
            "UPDATE documents SET status='chunking' WHERE id=?", (doc_id,)
        )
        conn.commit()

        blocks = _detect_sections(content)
        for block in blocks:
            for chunk in _chunk_block(block):
                cursor = conn.execute(
                    """INSERT INTO chunks
                       (document_id, project_id, chunk_index, content,
                        page_ref, section_ref, machine_ref)
                       VALUES (?, ?, ?, ?, ?, ?,
                           (SELECT machine_ref FROM documents WHERE id=?))""",
                    (
                        doc_id,
                        project_id,
                        chunk_index,
                        chunk["content"],
                        chunk.get("page_ref"),
                        chunk.get("title", "")[:255],
                        doc_id,
                    ),
                )
                all_chunks.append({
                    "id": cursor.lastrowid,
                    "doc_id": doc_id,
                    "chunk_index": chunk_index,
                    "content": chunk["content"],
                    "page_ref": chunk.get("page_ref"),
                    "section_ref": chunk.get("title", ""),
                    "filename": doc.get("filename", ""),
                })
                chunk_index += 1

        conn.execute(
            "UPDATE documents SET status='chunked' WHERE id=?", (doc_id,)
        )

    conn.commit()

    avg_len = int(sum(len(c["content"]) for c in all_chunks) / max(len(all_chunks), 1))
    avg_tokens = avg_len // 4
    counter = f"{len(all_chunks)} chunks · ~{avg_tokens} tokens moy."
    update_agent(conn, job_id, "chunk", "done", counter)
    logger.info(f"[chunker] {counter}")
    return all_chunks
