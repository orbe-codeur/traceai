"""
Agent 3 — Parser
Convertit tous les formats en fichiers .md sur disque.

Pipeline :
  PDF  → Docling → wiki/{project_id}/raw/{stem}.md
  DOCX → python-docx → texte markdown basique
  XLSX → pandas → markdown tabulaire
  URL  → BeautifulSoup → texte propre

Le chunker lit ensuite les .md pour découper.
"""
import logging
import sqlite3
from pathlib import Path

import httpx

from .utils import update_agent, update_batch_files, append_log

logger = logging.getLogger(__name__)

# Dossier des fichiers .md intermédiaires
WIKI_BASE = Path(__file__).parent.parent / "wiki"


def _md_output_path(project_id: int, filename: str) -> Path:
    out_dir = WIKI_BASE / str(project_id) / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(filename).stem.lower().replace(" ", "-")
    return out_dir / f"{stem}.md"


# ---------------------------------------------------------------------------
# PDF — Docling
# ---------------------------------------------------------------------------

def _parse_pdf(path: Path, project_id: int) -> tuple[str, Path | None]:
    """
    Convertit un PDF en markdown via Docling.
    Sauvegarde le .md dans wiki/{project_id}/raw/.
    Retourne (markdown_content, md_path).
    """
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        options = PdfPipelineOptions()
        options.do_ocr = False
        options.do_table_structure = True
        options.table_structure_options.do_cell_matching = True

        converter = DocumentConverter()
        result = converter.convert(str(path))
        doc = result.document

        # Export markdown structuré avec headers et tableaux
        md_text = doc.export_to_markdown()

        if not md_text or len(md_text) < 100:
            raise ValueError("Docling a produit un markdown vide")

        md_path = _md_output_path(project_id, path.name)
        md_path.write_text(md_text, encoding="utf-8")
        logger.info("[parser] %s → %s (%d chars)", path.name, md_path.name, len(md_text))
        return md_text, md_path

    except Exception as e:
        logger.warning("[parser] Docling échoué sur %s : %s — fallback PyMuPDF", path.name, e)
        return _parse_pdf_fallback(path, project_id)


def _parse_pdf_fallback(path: Path, project_id: int) -> tuple[str, Path | None]:
    """Fallback PyMuPDF si Docling échoue — extrait le texte brut."""
    try:
        import fitz
        doc = fitz.open(str(path))
        lines = []
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                lines.append(f"\n## Page {i + 1}\n\n{text}")
        md_text = "\n".join(lines)

        md_path = _md_output_path(project_id, path.name)
        md_path.write_text(md_text, encoding="utf-8")
        return md_text, md_path
    except Exception as e:
        logger.error("[parser] Fallback PyMuPDF échoué : %s", e)
        return "", None


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------

def _parse_docx(path: Path, project_id: int) -> tuple[str, Path | None]:
    try:
        from docx import Document
        doc = Document(str(path))
        lines = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            # Détecter les titres via le style
            style = para.style.name.lower()
            if "heading 1" in style:
                lines.append(f"# {text}")
            elif "heading 2" in style:
                lines.append(f"## {text}")
            elif "heading 3" in style:
                lines.append(f"### {text}")
            else:
                lines.append(text)

        md_text = "\n\n".join(lines)
        md_path = _md_output_path(project_id, path.name)
        md_path.write_text(md_text, encoding="utf-8")
        return md_text, md_path
    except ImportError:
        logger.warning("[parser] python-docx non installé")
        return "", None
    except Exception as e:
        logger.error("[parser] DOCX %s : %s", path.name, e)
        return "", None


# ---------------------------------------------------------------------------
# XLSX / CSV
# ---------------------------------------------------------------------------

def _parse_xlsx(path: Path, project_id: int) -> tuple[str, Path | None]:
    try:
        import pandas as pd
        sheets = pd.read_excel(str(path), sheet_name=None) if path.suffix in (".xlsx", ".xls") \
            else {"data": pd.read_csv(str(path))}

        lines = []
        for sheet_name, df in sheets.items():
            lines.append(f"# Feuille : {sheet_name}\n")
            lines.append(df.fillna("").to_markdown(index=False))
            lines.append("")

        md_text = "\n".join(lines)
        md_path = _md_output_path(project_id, path.name)
        md_path.write_text(md_text, encoding="utf-8")
        return md_text, md_path
    except Exception as e:
        logger.error("[parser] XLSX %s : %s", path.name, e)
        return "", None


# ---------------------------------------------------------------------------
# HTML / URL
# ---------------------------------------------------------------------------

def _parse_html(content: str, project_id: int, name: str) -> tuple[str, Path | None]:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        lines = [l for l in soup.get_text(separator="\n").splitlines() if l.strip()]
        md_text = "\n".join(lines)[:120_000]
        md_path = _md_output_path(project_id, name)
        md_path.write_text(md_text, encoding="utf-8")
        return md_text, md_path
    except Exception as e:
        logger.error("[parser] HTML %s : %s", name, e)
        return "", None


def _parse_url(url: str, project_id: int) -> tuple[str, Path | None]:
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "TraceAI/2.0"})
            resp.raise_for_status()
        stem = url.split("/")[-1][:50] or "page"
        return _parse_html(resp.text, project_id, stem + ".url")
    except Exception as e:
        logger.error("[parser] URL %s : %s", url, e)
        return "", None


# ---------------------------------------------------------------------------
# Agent run()
# ---------------------------------------------------------------------------

def run(
    project_id: int,
    job_id: int,
    file_paths: list[Path],
    conn: sqlite3.Connection,
    urls: list[str] | None = None,
) -> list[dict]:
    """
    Parse tous les fichiers → markdown sur disque.
    Retourne [{doc_id, filename, content, md_path, page_count}].
    """
    update_agent(conn, job_id, "parse", "running", "")
    append_log(conn, job_id, "info", "parse",
               f"Démarrage · {len(file_paths)} fichiers + {len(urls or [])} URLs")

    parsed: list[dict] = []
    errors = 0
    processed = 0

    for i, path in enumerate(file_paths):
        ext = path.suffix.lower()
        size_kb = path.stat().st_size // 1024
        append_log(conn, job_id, "info", "parse",
                   f"[{i+1}/{len(file_paths)}] {path.name} ({size_kb} Ko) — parsing…")

        conn.execute(
            "UPDATE documents SET status='parsing' WHERE project_id=? AND filename=?",
            (project_id, path.name),
        )
        conn.commit()

        row = conn.execute(
            "SELECT id FROM documents WHERE project_id=? AND filename=?",
            (project_id, path.name),
        ).fetchone()
        doc_id = row[0] if row else None

        try:
            md_path = None
            page_count = 0

            if ext == ".pdf":
                content, md_path = _parse_pdf(path, project_id)
                try:
                    import fitz
                    page_count = len(fitz.open(str(path)))
                except Exception:
                    pass

            elif ext in (".docx", ".doc"):
                content, md_path = _parse_docx(path, project_id)

            elif ext in (".xlsx", ".xls", ".csv"):
                content, md_path = _parse_xlsx(path, project_id)

            elif ext in (".html", ".htm"):
                raw = path.read_text(encoding="utf-8", errors="ignore")
                content, md_path = _parse_html(raw, project_id, path.name)

            elif ext in (".txt", ".md", ".rst"):
                content = path.read_text(encoding="utf-8", errors="ignore")[:120_000]
                md_path = _md_output_path(project_id, path.name)
                md_path.write_text(content, encoding="utf-8")

            else:
                append_log(conn, job_id, "warn", "parse",
                           f"{path.name} — format {ext} non supporté (ignoré)")
                content = ""

            conn.execute(
                "UPDATE documents SET status='parsed', page_count=? WHERE id=?",
                (page_count, doc_id),
            )
            conn.commit()

            if content:
                parsed.append({
                    "doc_id":     doc_id,
                    "filename":   path.name,
                    "content":    content,
                    "md_path":    md_path,
                    "page_count": page_count,
                    "source_url": None,
                })
                processed += 1
                chars_k = len(content) // 1000
                append_log(conn, job_id, "ok", "parse",
                           f"✓ {path.name} — {page_count}p · {chars_k}K chars"
                           f"{' → ' + md_path.name if md_path else ''}")
            else:
                errors += 1
                append_log(conn, job_id, "warn", "parse", f"{path.name} — contenu vide")

        except Exception as e:
            logger.error("[parser] %s : %s", path.name, e)
            append_log(conn, job_id, "err", "parse", f"{path.name} ERREUR : {str(e)[:100]}")
            errors += 1
            if doc_id:
                conn.execute(
                    "UPDATE documents SET status='error', error_message=? WHERE id=?",
                    (str(e)[:500], doc_id),
                )
                conn.commit()

        update_batch_files(conn, job_id, processed, errors)

    # URLs
    for url in (urls or []):
        conn.execute(
            """INSERT OR IGNORE INTO documents
               (project_id, filename, file_type, source_url, status)
               VALUES (?, ?, 'url', ?, 'parsing')""",
            (project_id, url[:255], url),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM documents WHERE project_id=? AND source_url=?",
            (project_id, url),
        ).fetchone()
        doc_id = row[0] if row else None

        content, md_path = _parse_url(url, project_id)
        if content:
            conn.execute("UPDATE documents SET status='parsed' WHERE id=?", (doc_id,))
            parsed.append({
                "doc_id": doc_id, "filename": url,
                "content": content, "md_path": md_path,
                "page_count": 0, "source_url": url,
            })
            processed += 1
        else:
            errors += 1
            if doc_id:
                conn.execute("UPDATE documents SET status='error' WHERE id=?", (doc_id,))
        conn.commit()
        update_batch_files(conn, job_id, processed, errors)

    counter = f"{len(parsed)} docs · {errors} erreur{'s' if errors != 1 else ''}"
    update_agent(conn, job_id, "parse", "done", counter)
    append_log(conn, job_id, "ok", "parse", f"Parser ✓ — {counter}")
    return parsed
