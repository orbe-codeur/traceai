"""
Agent 3 — Parser
Gère tous les formats : PDF texte, PDF scanné (OCR), DOCX, XLSX, images, URLs.
"""
import io
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import httpx

from .utils import update_agent, update_batch_files, append_log

logger = logging.getLogger(__name__)

# Seuil : si moins de 100 chars/page → PDF scanné
SCAN_THRESHOLD = 100
# Seuil : si ratio image > 50% de la surface → page schéma (vision)
IMAGE_RATIO_THRESHOLD = 0.5


def _parse_pdf(path: Path, project_id: int, doc_id: int, conn: sqlite3.Connection) -> str:
    """Extrait le texte d'un PDF. Bascule sur OCR si scanné."""
    try:
        doc = fitz.open(str(path))
    except Exception as e:
        logger.error(f"[parser] Impossible d'ouvrir {path.name}: {e}")
        return ""

    parts = []
    total_chars = 0
    total_pages = len(doc)

    for i, page in enumerate(doc):
        text = page.get_text().strip()
        total_chars += len(text)
        parts.append(f"--- PAGE {i + 1} ---\n{text}" if text else f"--- PAGE {i + 1} ---")

    avg_chars = total_chars / max(total_pages, 1)

    if avg_chars < SCAN_THRESHOLD:
        # PDF scanné : tenter Surya OCR, puis Tesseract, puis skip
        logger.info(f"[parser] {path.name} scanné (avg {avg_chars:.0f} chars/p) → OCR")
        conn.execute(
            "UPDATE documents SET is_scanned=1 WHERE id=?", (doc_id,)
        )
        conn.commit()
        ocr_text = _ocr_pdf(path, doc)
        if ocr_text:
            return ocr_text

    return "\n\n".join(parts)


def _ocr_pdf(path: Path, doc: fitz.Document) -> str:
    """OCR d'un PDF scanné via Surya (fallback : texte vide + avertissement)."""
    try:
        from surya.ocr import run_ocr
        from surya.model.detection.model import load_model as load_det
        from surya.model.recognition.model import load_model as load_rec
        from surya.model.detection.processor import load_processor as load_det_proc
        from surya.model.recognition.processor import load_processor as load_rec_proc

        det_model, det_proc = load_det(), load_det_proc()
        rec_model, rec_proc = load_rec(), load_rec_proc()

        images = [page.get_pixmap(dpi=150).tobytes("png") for page in doc]
        langs = [["fr", "en"]] * len(images)
        results = run_ocr(images, langs, det_model, det_proc, rec_model, rec_proc)
        parts = []
        for i, r in enumerate(results):
            text = " ".join(line.text for block in r.text_lines for line in [block])
            parts.append(f"--- PAGE {i + 1} ---\n{text}")
        return "\n\n".join(parts)
    except ImportError:
        logger.warning("[parser] Surya OCR non installé — PDF scanné ignoré")
        return ""
    except Exception as e:
        logger.warning(f"[parser] OCR échoué: {e}")
        return ""


def _parse_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text.strip())
        return "\n\n".join(parts)
    except ImportError:
        logger.warning("[parser] python-docx non installé")
        return ""
    except Exception as e:
        logger.error(f"[parser] DOCX {path.name}: {e}")
        return ""


def _parse_xlsx(path: Path) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=True)
        parts = []
        for sheet in wb.worksheets:
            parts.append(f"[Feuille: {sheet.title}]")
            headers: Optional[list] = None
            for row in sheet.iter_rows(values_only=True):
                values = [str(v) if v is not None else "" for v in row]
                if not any(values):
                    continue
                if headers is None:
                    headers = values
                    parts.append(" | ".join(headers))
                else:
                    parts.append(" | ".join(values))
        return "\n".join(parts)
    except ImportError:
        logger.warning("[parser] openpyxl non installé")
        return ""
    except Exception as e:
        logger.error(f"[parser] XLSX {path.name}: {e}")
        return ""


def _parse_html_file(path: Path) -> str:
    """Extrait le texte d'un fichier HTML local."""
    try:
        from bs4 import BeautifulSoup
        html = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "svg"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if l.strip()]
        return "\n".join(lines)[:120_000]
    except ImportError:
        logger.warning("[parser] beautifulsoup4 non installé")
        return ""
    except Exception as e:
        logger.error(f"[parser] HTML {path.name}: {e}")
        return ""


def _parse_url(url: str) -> str:
    try:
        from bs4 import BeautifulSoup
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "TraceAI/2.0"})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Supprimer scripts, styles, nav
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Nettoyer lignes vides multiples
        lines = [l for l in text.splitlines() if l.strip()]
        return "\n".join(lines)[:20000]
    except ImportError:
        logger.warning("[parser] beautifulsoup4 non installé")
        return ""
    except Exception as e:
        logger.error(f"[parser] URL {url}: {e}")
        return ""


def run(
    project_id: int,
    job_id: int,
    file_paths: list[Path],
    conn: sqlite3.Connection,
    urls: list[str] | None = None,
) -> list[dict]:
    """
    Parse tous les fichiers et URLs.
    Retourne une liste de {doc_id, filename, content, page_count}.
    Met à jour le statut des documents en base.
    """
    update_agent(conn, job_id, "parse", "running", "")
    append_log(conn, job_id, "info", "parse", f"Démarrage · {len(file_paths)} fichiers + {len(urls or [])} URLs")

    parsed: list[dict] = []
    errors = 0
    processed = 0

    MAX_CHARS_PER_DOC = 120_000  # ~30K tokens max par document → max ~30 chunks

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
            "SELECT id, page_count FROM documents WHERE project_id=? AND filename=?",
            (project_id, path.name),
        ).fetchone()
        doc_id = row[0] if row else None

        try:
            if ext == ".pdf":
                content = _parse_pdf(path, project_id, doc_id, conn)
                try:
                    doc = fitz.open(str(path))
                    page_count = len(doc)
                except Exception:
                    page_count = 0
            elif ext in (".docx", ".doc"):
                content = _parse_docx(path)
                page_count = 0
            elif ext in (".xlsx", ".xls"):
                content = _parse_xlsx(path)
                page_count = 0
            elif ext in (".html", ".htm"):
                content = _parse_html_file(path)
                page_count = 0
            elif ext in (".txt", ".md", ".rst", ".csv"):
                content = path.read_text(encoding="utf-8", errors="ignore")[:120_000]
                page_count = 0
            elif ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp"):
                content = f"[Image: {path.name}]"
                page_count = 1
            else:
                append_log(conn, job_id, "warn", "parse",
                           f"{path.name} — format {ext} non supporté (ignoré)")
                content = ""
                page_count = 0

            conn.execute(
                "UPDATE documents SET status='parsed', page_count=? WHERE id=?",
                (page_count, doc_id),
            )
            conn.commit()

            if content:
                # Limiter la taille pour éviter trop de chunks
                if len(content) > MAX_CHARS_PER_DOC:
                    append_log(conn, job_id, "warn", "parse",
                               f"{path.name} tronqué {len(content)//1000}K→{MAX_CHARS_PER_DOC//1000}K chars (doc trop long)")
                    content = content[:MAX_CHARS_PER_DOC]

                parsed.append({
                    "doc_id": doc_id,
                    "filename": path.name,
                    "content": content,
                    "page_count": page_count,
                    "source_url": None,
                })
                processed += 1
                append_log(conn, job_id, "ok", "parse",
                           f"✓ {path.name} — {page_count} pages · {len(content)//1000}K chars")
            else:
                errors += 1
                append_log(conn, job_id, "warn", "parse", f"{path.name} — contenu vide")
        except Exception as e:
            logger.error(f"[parser] {path.name}: {e}")
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

        content = _parse_url(url)
        if content:
            conn.execute(
                "UPDATE documents SET status='parsed' WHERE id=?", (doc_id,)
            )
            parsed.append({
                "doc_id": doc_id,
                "filename": url,
                "content": content,
                "page_count": 0,
                "source_url": url,
            })
            processed += 1
        else:
            errors += 1
            if doc_id:
                conn.execute(
                    "UPDATE documents SET status='error' WHERE id=?", (doc_id,)
                )
        conn.commit()
        update_batch_files(conn, job_id, processed, errors)

    counter = f"{len(parsed)} docs · {errors} erreur{'s' if errors != 1 else ''}"
    update_agent(conn, job_id, "parse", "done", counter)
    append_log(conn, job_id, "ok", "parse", f"Parser ✓ — {counter}")
    return parsed
