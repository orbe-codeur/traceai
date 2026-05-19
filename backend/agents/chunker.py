"""
Agent 4 — Chunker adaptatif
Stratégie de découpe choisie selon le doc_type du classificateur.

Stratégies disponibles :
  markdown_sections — H1/H2/H3 → frontières de section, tables atomiques
  paragraphs        — découpe sur \n\n
  rows              — groupes de N lignes (CSV/tableau)
  steps             — items numérotés (1. / 2. / étape N)

Paramètres par doc_type (calibrés pour Mistral Embed 8192 tokens = ~32 000 chars) :
  La taille optimale d'embedding est ~1 000-1 500 tokens (4 000-6 000 chars).
  Les tableaux techniques (datasheets) bénéficient de chunks plus larges pour
  préserver la cohérence sémantique des specs.
"""
import logging
import re
import sqlite3
from pathlib import Path

from .utils import update_agent, append_log

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paramètres par stratégie
# Calibrés pour Mistral embed (8192 tok max) — taille optimale ~1 000-1 500 tok
# ---------------------------------------------------------------------------
STRATEGIES: dict[str, dict] = {
    "manual_constructor": {
        "method":   "markdown_sections",
        "max_chars": 6000,   # ~1 500 tokens — granularité fine pour les procédures
        "overlap":   400,
    },
    "technical_datasheet": {
        "method":   "markdown_sections",
        "max_chars": 8000,   # ~2 000 tokens — specs denses, cohérence préservée
        "overlap":   500,
    },
    "intervention_report": {
        "method":   "paragraphs",
        "max_chars": 3200,   # ~800 tokens — rapports courts par nature
        "overlap":   200,
    },
    "parts_inventory": {
        "method":        "rows",
        "max_chars":     2000,   # ~500 tokens — précision ligne par ligne
        "overlap":       0,
        "rows_per_chunk": 20,
    },
    "procedure_checklist": {
        "method":   "steps",
        "max_chars": 1600,   # ~400 tokens — chaque étape = unité sémantique
        "overlap":   150,
    },
    "unknown": {
        "method":   "paragraphs",
        "max_chars": 4000,   # ~1 000 tokens — générique
        "overlap":   250,
    },
}

# Limite dure Mistral Embed (8192 tokens × 4 chars/token)
EMBED_MAX_CHARS = 30000


# ---------------------------------------------------------------------------
# Helpers partagés
# ---------------------------------------------------------------------------

def _is_table_line(line: str) -> bool:
    return line.startswith("|")


def _extract_page_from_header(title: str) -> int | None:
    m = re.search(r"<!--\s*page[=:]\s*(\d+)", title)
    return int(m.group(1)) if m else None


def _split_with_overlap(text: str, max_chars: int, overlap: int) -> list[str]:
    """Découpe un texte long en morceaux avec overlap sur les paragraphes."""
    paragraphs = re.split(r"\n\n+", text)
    result = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) > max_chars and buf:
            result.append(buf.strip())
            buf = buf[-overlap:] + "\n\n" + para if overlap else para
        else:
            buf = (buf + "\n\n" + para).strip() if buf else para
    if buf.strip():
        result.append(buf.strip())
    return result


# ---------------------------------------------------------------------------
# Stratégie 1 : markdown_sections (actuelle, enrichie)
# ---------------------------------------------------------------------------

def chunk_markdown(md_text: str, max_chars: int, overlap: int) -> list[dict]:
    """
    Découpe un document markdown en chunks structurés.
    Retourne [{title, content, level, page_ref, is_table, section_path, chunk_method}].
    """
    chunks: list[dict] = []
    lines = md_text.splitlines()

    current: dict = {"title": "", "level": 0, "lines": [], "page_ref": 0}
    section_stack: list[str] = []
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
        page  = current["page_ref"]
        path_parts  = section_stack[:level] + ([title] if title else [])
        section_path = " > ".join(p for p in path_parts if p)

        if len(content) <= max_chars:
            chunks.append({
                "title": title, "content": content, "level": level,
                "page_ref": page, "is_table": False,
                "section_path": section_path, "chunk_method": "markdown_sections",
            })
        else:
            for part in _split_with_overlap(content, max_chars, overlap):
                chunks.append({
                    "title": title, "content": part, "level": level,
                    "page_ref": page, "is_table": False,
                    "section_path": section_path, "chunk_method": "markdown_sections",
                })
        current = {"title": "", "level": 0, "lines": [], "page_ref": page}

    def flush_table():
        nonlocal table_lines, in_table
        if not table_lines:
            return
        content = "\n".join(table_lines).strip()
        if content:
            level = current["level"]
            path_parts   = section_stack[:level] + ([table_title] if table_title else [])
            section_path = " > ".join(p for p in path_parts if p)
            chunks.append({
                "title": table_title or current["title"],
                "content": content, "level": level,
                "page_ref": table_page or current["page_ref"],
                "is_table": True,
                "section_path": section_path, "chunk_method": "markdown_sections",
            })
        table_lines.clear()
        in_table = False

    for line in lines:
        stripped = line.rstrip()

        if _is_table_line(stripped):
            if not in_table:
                flush_current()
                in_table   = True
                table_title = current["title"]
                table_page  = current["page_ref"]
            table_lines.append(stripped)
            continue

        if in_table and not _is_table_line(stripped) and stripped != "":
            flush_table()

        if in_table and stripped == "":
            table_lines.append(stripped)
            continue

        m = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if m:
            flush_current()
            level = len(m.group(1))
            title = m.group(2).strip()
            page  = _extract_page_from_header(title) or current["page_ref"]
            while len(section_stack) >= level:
                section_stack.pop() if section_stack else None
            section_stack.append(title)
            current = {"title": title, "level": level, "lines": [], "page_ref": page}
            continue

        current["lines"].append(stripped)

    flush_table()
    flush_current()
    return chunks


# ---------------------------------------------------------------------------
# Stratégie 2 : paragraphs
# ---------------------------------------------------------------------------

def chunk_paragraphs(text: str, max_chars: int, overlap: int) -> list[dict]:
    parts = _split_with_overlap(text, max_chars, overlap)
    return [
        {"title": "", "content": p, "level": 0, "page_ref": 0,
         "is_table": False, "section_path": "", "chunk_method": "paragraphs"}
        for p in parts if p.strip()
    ]


# ---------------------------------------------------------------------------
# Stratégie 3 : rows (CSV / inventaire)
# ---------------------------------------------------------------------------

def chunk_rows(text: str, max_chars: int, rows_per_chunk: int = 20) -> list[dict]:
    """
    Groupe les lignes de tableau (CSV ou markdown table) par paquets.
    Conserve l'en-tête dans chaque chunk pour le contexte.
    """
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return []

    # Détecter la ligne d'en-tête (première ligne non-séparateur)
    header = ""
    data_lines = []
    for l in lines:
        if re.match(r"^[\|\-\s,;]+$", l):
            continue  # ligne séparateur markdown
        if not header:
            header = l
        else:
            data_lines.append(l)

    chunks = []
    for i in range(0, len(data_lines), rows_per_chunk):
        batch = data_lines[i : i + rows_per_chunk]
        content = (header + "\n" + "\n".join(batch))[:max_chars]
        chunks.append({
            "title": f"Lignes {i+1}–{i+len(batch)}",
            "content": content, "level": 0, "page_ref": 0,
            "is_table": True, "section_path": "", "chunk_method": "rows",
        })
    return chunks


# ---------------------------------------------------------------------------
# Stratégie 4 : steps (procédures numérotées)
# ---------------------------------------------------------------------------

def chunk_steps(text: str, max_chars: int, overlap: int) -> list[dict]:
    """
    Découpe sur les items numérotés (1. / Step 1 / Étape 1).
    Regroupe les petits steps pour ne pas créer de micro-chunks.
    """
    step_re = re.compile(r"^(\d+[\.\)]\s+|[Ss]tep\s+\d+|[Éé]tape\s+\d+)", re.MULTILINE)
    parts   = step_re.split(text)
    # split() garde les délimiteurs → pairs (delim, content)
    merged = []
    i = 0
    buf = ""
    while i < len(parts):
        piece = parts[i]
        if step_re.match(piece):
            num   = piece
            body  = parts[i + 1] if i + 1 < len(parts) else ""
            step  = (num + body).strip()
            if len(buf) + len(step) > max_chars and buf:
                merged.append(buf.strip())
                buf = buf[-overlap:] + "\n\n" + step if overlap else step
            else:
                buf = (buf + "\n\n" + step).strip() if buf else step
            i += 2
        else:
            buf = (buf + "\n\n" + piece).strip() if buf else piece.strip()
            i += 1
    if buf.strip():
        merged.append(buf.strip())

    # Si pas de steps trouvés → fallback paragraphes
    if not merged:
        return chunk_paragraphs(text, max_chars, overlap)

    return [
        {"title": "", "content": p, "level": 0, "page_ref": 0,
         "is_table": False, "section_path": "", "chunk_method": "steps"}
        for p in merged
    ]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def chunk_document(text: str, doc_type: str) -> list[dict]:
    """Choisit la stratégie adaptée au doc_type et découpe le texte."""
    strategy = STRATEGIES.get(doc_type, STRATEGIES["unknown"])
    method    = strategy["method"]
    max_chars = min(strategy["max_chars"], EMBED_MAX_CHARS)
    overlap   = strategy.get("overlap", 0)

    if method == "markdown_sections":
        return chunk_markdown(text, max_chars, overlap)
    elif method == "rows":
        return chunk_rows(text, max_chars, strategy.get("rows_per_chunk", 20))
    elif method == "steps":
        return chunk_steps(text, max_chars, overlap)
    else:  # paragraphs + unknown
        return chunk_paragraphs(text, max_chars, overlap)


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
    Découpe tous les documents en chunks via la stratégie adaptée au doc_type.
    Lit le .md sur disque si disponible, sinon utilise le content brut.
    Insère en base et retourne la liste des chunks.
    """
    update_agent(conn, job_id, "chunk", "running", "")
    logger.info("[chunker] %d documents à découper", len(parsed_docs))

    all_chunks: list[dict] = []
    chunk_index = 0

    for doc in parsed_docs:
        doc_id      = doc["doc_id"]
        md_path     = doc.get("md_path")
        content     = doc.get("content", "")
        doc_type    = doc.get("doc_type") or "unknown"
        machine_ref = doc.get("machine_ref") or ""
        manufacturer = doc.get("manufacturer", "")
        language    = doc.get("language", "fr")

        if not content and not md_path:
            continue

        conn.execute("UPDATE documents SET status='chunking' WHERE id=?", (doc_id,))
        conn.commit()

        # Lire le .md sur disque si disponible
        if md_path and Path(md_path).exists():
            md_text = Path(md_path).read_text(encoding="utf-8")
            source  = f"md:{Path(md_path).name}"
        else:
            md_text = content
            source  = "content"

        strategy = STRATEGIES.get(doc_type, STRATEGIES["unknown"])
        blocks   = chunk_document(md_text, doc_type)

        logger.info("[chunker] %s [%s] — %s → %d blocs (méthode: %s, max: %d)",
                    doc.get("filename", "?"), doc_type, source,
                    len(blocks), strategy["method"], strategy["max_chars"])

        # Récupérer machine_ref depuis la DB si pas fourni
        if not machine_ref:
            row = conn.execute(
                "SELECT machine_ref FROM documents WHERE id=?", (doc_id,)
            ).fetchone()
            machine_ref = (row[0] if row else "") or ""

        for block in blocks:
            # machine_ref : priorité au niveau chunk si le block a un titre de machine
            block_machine = block.get("machine_ref") or machine_ref

            cursor = conn.execute(
                """INSERT INTO chunks
                   (document_id, project_id, chunk_index, content,
                    page_ref, section_ref, machine_ref, category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    doc_id,
                    project_id,
                    chunk_index,
                    block["content"],
                    block.get("page_ref"),
                    (block.get("section_path") or block.get("title", ""))[:255],
                    block_machine,
                    doc_type,   # category = doc_type pour le filtrage
                ),
            )
            all_chunks.append({
                "id":           cursor.lastrowid,
                "doc_id":       doc_id,
                "chunk_index":  chunk_index,
                "content":      block["content"],
                "page_ref":     block.get("page_ref"),
                "section_ref":  block.get("section_path") or block.get("title", ""),
                "machine_ref":  block_machine,
                "filename":     doc.get("filename", ""),
                "is_table":     block.get("is_table", False),
                "chunk_method": block.get("chunk_method", strategy["method"]),
                "doc_type":     doc_type,
                "manufacturer": manufacturer,
                "language":     language,
            })
            chunk_index += 1

        conn.execute("UPDATE documents SET status='chunked' WHERE id=?", (doc_id,))

    conn.commit()

    avg_len = int(sum(len(c["content"]) for c in all_chunks) / max(len(all_chunks), 1))
    avg_tok = avg_len // 4
    counter = f"{len(all_chunks)} chunks · ~{avg_tok} tokens moy."
    update_agent(conn, job_id, "chunk", "done", counter)
    append_log(conn, job_id, "ok", "chunk", f"Chunker ✓ — {counter}")
    logger.info("[chunker] %s", counter)
    return all_chunks
