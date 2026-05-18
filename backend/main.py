import asyncio
import hashlib
import os
import json
import shutil
import sqlite3
import zipfile as _zipfile
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "")
LLM_MODEL    = os.getenv("LLM_MODEL", "mistral-large-latest")

LLM_API_URL = (
    "https://api.openai.com/v1/chat/completions"
    if LLM_PROVIDER == "openai"
    else "https://api.mistral.ai/v1/chat/completions"
)

UPLOADS_DIR   = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
PHASE2_DIR    = Path(__file__).parent / "uploads_phase2"
PHASE2_DIR.mkdir(exist_ok=True)
CHROMA_DIR    = Path(__file__).parent / "chroma_data"

DB_PATH = Path(__file__).parent / "traceai.db"

# Limite de parallélisme : max 3 appels Mistral simultanés
_SEM = asyncio.Semaphore(3)

# ---------------------------------------------------------------------------
# Prompts agent
# ---------------------------------------------------------------------------

PROMPT_TOC = """Tu es un expert en analyse de manuels techniques industriels.

Voici les premières pages d'un manuel technique (table des matières + introduction).

Ta mission : identifier TOUTES les sections qui contiennent des PROCÉDURES CONCRÈTES à réaliser par un technicien. Sois exhaustif, n'en oublie aucune.

Inclure OBLIGATOIREMENT (si présent) :
- Préparation à l'utilisation / Inspection initiale / Déballage
- Installation / Mise en place / Raccordement
- Mise en service / Démarrage / Procédure de départ
- Arrêt / Procédure d'arrêt / Shutdown
- Opération / Utilisation / Réglages opérateurs
- Maintenance préventive / Entretien périodique
- Vérification huile / Vidange / Lubrification
- Remplacement filtres / Courroies / Consommables
- Réglages techniques (pression, débit, tension courroie…)
- Tests / Vérifications opérationnelles

Exclure UNIQUEMENT :
- Règles de sécurité générales (listes "ne pas faire X")
- Introductions, descriptions de composants, nomenclature
- Garanties, informations légales, contacts, index
- Guides de dépannage théoriques (tableaux problème/cause/solution)

Retourne un JSON :
{
  "sections": [
    { "name": "Nom de la section", "page_start": 21, "page_end": 24 }
  ]
}

IMPORTANT : inclure les numéros de page exacts tels qu'ils apparaissent dans la table des matières.
Réponds UNIQUEMENT avec le JSON. Si aucune section n'est identifiable, retourne { "sections": [] }
"""

PROMPT_EXTRACT = """Tu es un expert en maintenance industrielle.

Voici le texte extrait des pages {page_start} à {page_end} d'un manuel technique.

Ta mission : extraire TOUTES les étapes concrètes et actionnables que le technicien doit réaliser dans cette section.

Retourne un JSON :
{{
  "steps": [
    {{
      "number": 1,
      "title": "Titre court de l'étape (max 80 caractères)",
      "description": "Ce que le technicien doit faire concrètement, avec les valeurs et références exactes du manuel",
      "category": "mécanique",
      "is_critical": false,
      "requires_witness": false,
      "page": 22
    }}
  ]
}}

Règles :
- category : "sécurité", "préparation", "mécanique", "électrique", "hydraulique", "pneumatique", "test", "vérification", "nettoyage", "documentation"
- is_critical = true si risque de blessure grave ou dommage machine irréversible
- requires_witness = true si double signature requise (mise sous tension HT, test haute pression, etc.)
- page = numéro de page PDF source (cherche "--- PAGE X ---" dans le texte)
- N'inclure QUE les actions concrètes (pas les règles "ne pas faire", pas les descriptions théoriques)
- Si la section ne contient aucune étape actionnable, retourne {{ "steps": [] }}
- Réponds UNIQUEMENT avec le JSON, rien d'autre
"""

# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            pdf_filename     TEXT,
            total_steps      INTEGER DEFAULT 0,
            completed_steps  INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS steps (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id       INTEGER REFERENCES projects(id),
            step_number      INTEGER NOT NULL,
            title            TEXT NOT NULL,
            description      TEXT,
            category         TEXT,
            is_critical      INTEGER DEFAULT 0,
            requires_witness INTEGER DEFAULT 0,
            page_ref         INTEGER,
            status           TEXT DEFAULT 'pending',
            technician_name  TEXT,
            witness_name     TEXT,
            note             TEXT,
            validated_at     TEXT
        );

        -- Phase 2 tables --

        CREATE TABLE IF NOT EXISTS documents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id    INTEGER REFERENCES projects(id),
            filename      TEXT NOT NULL,
            file_type     TEXT NOT NULL,
            file_path     TEXT,
            source_url    TEXT,
            file_hash     TEXT,
            page_count    INTEGER,
            is_scanned    INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'pending',
            error_message TEXT,
            metadata_json TEXT,
            machine_ref   TEXT,
            doc_type      TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id   INTEGER REFERENCES documents(id),
            project_id    INTEGER REFERENCES projects(id),
            chunk_index   INTEGER,
            content       TEXT NOT NULL,
            summary       TEXT,
            category      TEXT,
            page_ref      INTEGER,
            section_ref   TEXT,
            machine_ref   TEXT,
            keywords_json TEXT,
            embedding_id  TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wiki_pages (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id        INTEGER REFERENCES projects(id),
            page_type         TEXT NOT NULL,
            page_name         TEXT NOT NULL,
            title             TEXT NOT NULL,
            content_md        TEXT NOT NULL,
            sources_json      TEXT,
            contradictions_json TEXT,
            gaps_json         TEXT,
            last_compiled_at  TEXT,
            created_at        TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS batch_jobs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      INTEGER REFERENCES projects(id),
            total_files     INTEGER,
            processed_files INTEGER DEFAULT 0,
            error_files     INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'running',
            agents_json     TEXT DEFAULT '{}',
            logs_json       TEXT DEFAULT '[]',
            started_at      TEXT DEFAULT (datetime('now')),
            completed_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id),
            title      TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER REFERENCES conversations(id),
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            sources_json    TEXT,
            confidence      REAL,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id   INTEGER REFERENCES projects(id),
            machine_ref  TEXT,
            alert_type   TEXT,
            title        TEXT,
            description  TEXT,
            message      TEXT NOT NULL,
            severity     TEXT DEFAULT 'info',
            is_dismissed INTEGER DEFAULT 0,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        -- Phase B — Mémoire agent (projet) + sessions
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

        CREATE TABLE IF NOT EXISTS agent_sessions (
            id         TEXT PRIMARY KEY,
            project_id INTEGER NOT NULL,
            mode       TEXT NOT NULL,
            system_prompt TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="TraceAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.on_event("startup")
def startup():
    init_db()
    # Migrations colonnes manquantes (DB existante)
    conn = get_db()
    for migration in [
        "ALTER TABLE batch_jobs ADD COLUMN logs_json TEXT DEFAULT '[]'",
        "ALTER TABLE alerts ADD COLUMN title TEXT",
        "ALTER TABLE alerts ADD COLUMN description TEXT",
    ]:
        try:
            conn.execute(migration)
            conn.commit()
        except Exception:
            pass  # colonne déjà existante

    # Phase B — FTS5 mémoire (CREATE VIRTUAL TABLE ne supporte pas IF NOT EXISTS sur SQLite < 3.35)
    try:
        conn.executescript("""
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
        """)
        conn.commit()
    except Exception:
        pass  # FTS5 déjà configuré ou non disponible
    conn.close()


# ---------------------------------------------------------------------------
# Helpers DB
# ---------------------------------------------------------------------------

def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def recalc_completed(conn: sqlite3.Connection, project_id: int):
    count = conn.execute(
        "SELECT COUNT(*) FROM steps WHERE project_id = ? AND status != 'pending'",
        (project_id,)
    ).fetchone()[0]
    conn.execute(
        "UPDATE projects SET completed_steps = ? WHERE id = ?",
        (count, project_id)
    )


# ---------------------------------------------------------------------------
# Agent — helpers LLM
# ---------------------------------------------------------------------------

def extract_pages_text(doc: fitz.Document, page_start: int, page_end: int) -> str:
    """Extrait le texte des pages [page_start, page_end] (numérotation 1-based)."""
    parts = []
    for i in range(page_start - 1, min(page_end, len(doc))):
        text = doc[i].get_text().strip()
        if text:
            parts.append(f"--- PAGE {i + 1} ---\n{text}")
    return "\n\n".join(parts)


async def llm_call(client: httpx.AsyncClient, messages: list[dict]) -> dict:
    """Appel LLM avec sémaphore (limite le parallélisme)."""
    async with _SEM:
        response = await client.post(
            LLM_API_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model":           LLM_MODEL,
                "messages":        messages,
                "response_format": {"type": "json_object"},
            },
            timeout=90.0,
        )
        response.raise_for_status()
        raw = response.json()
        return json.loads(raw["choices"][0]["message"]["content"])


# ---------------------------------------------------------------------------
# Agent — Passe 1 : analyse de la TOC → bornes du document utile
# ---------------------------------------------------------------------------

async def agent_toc_analysis(client: httpx.AsyncClient, doc: fitz.Document) -> dict:
    """
    Lit la TOC pour trouver la première et la dernière page utile du document.
    Retourne { first_useful_page, last_useful_page } pour cadrer le chunking.
    """
    toc_text = extract_pages_text(doc, 1, 6)
    prompt = """Tu es un expert en manuels techniques industriels.

Voici les premières pages d'un manuel (table des matières + intro).

Identifie :
1. La PREMIÈRE page qui contient des procédures concrètes pour technicien (installation, opération, maintenance, réglages). Exclure safety générale, intro, descriptions.
2. La DERNIÈRE page utile (dernière section avec procédures). Exclure troubleshooting théorique, garantie, index.

Retourne UNIQUEMENT ce JSON :
{ "first_page": 21, "last_page": 44 }"""

    try:
        payload = await llm_call(client, [
            {"role": "system", "content": prompt},
            {"role": "user",   "content": toc_text},
        ])
        first = int(payload.get("first_page", 6))
        last  = int(payload.get("last_page", len(doc)))
        # Sécurité : bornes valides
        first = max(4, min(first, len(doc)))
        last  = max(first, min(last, len(doc)))
        return {"first_page": first, "last_page": last}
    except Exception:
        return {"first_page": 6, "last_page": len(doc)}


# ---------------------------------------------------------------------------
# Agent — Passe 2 : extraction par chunk (parallèle)
# ---------------------------------------------------------------------------


async def _extract_chunk(
    client: httpx.AsyncClient,
    doc: fitz.Document,
    chunk: dict,
) -> list[dict]:
    """Appel LLM pour extraire les étapes d'un chunk de pages."""
    page_start = chunk["page_start"]
    page_end   = chunk["page_end"]
    text = extract_pages_text(doc, page_start, page_end)
    if not text.strip():
        return []

    prompt = PROMPT_EXTRACT.format(page_start=page_start, page_end=page_end)
    try:
        payload = await llm_call(client, [
            {"role": "system", "content": prompt},
            {"role": "user",   "content": text},
        ])
        return payload.get("steps", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Agent — Passe 3 : fusion et renumérotation
# ---------------------------------------------------------------------------

def merge_and_renumber(all_steps: list[dict]) -> list[dict]:
    """
    Déduplique par similarité de titre (80 chars) et trie par page source.
    """
    seen: set[str] = set()
    unique: list[dict] = []
    for s in all_steps:
        # Clé de déduplication : titre normalisé sur 80 chars
        key = "".join(s.get("title", "").lower().split())[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(s)

    # Trier : page source d'abord, puis numéro d'étape original
    unique.sort(key=lambda s: (s.get("page") or 0, s.get("number") or 0))

    for i, s in enumerate(unique, 1):
        s["number"] = i

    return unique


# ---------------------------------------------------------------------------
# Agent — Pipeline principal
# ---------------------------------------------------------------------------

async def run_extraction_agent(doc: fitz.Document) -> list[dict]:
    """
    Pipeline 2 passes :
    1. TOC → bornes utiles du document (first_page, last_page)
    2. Chunking de first_page à last_page (8 pages/chunk) → extraction parallèle
    3. Fusion + déduplications + renumérotation

    Le LLM filtre naturellement les pages non-actionnables (safety générale,
    descriptions, tableaux de dépannage) et retourne steps:[] pour celles-ci.
    """
    async with httpx.AsyncClient() as client:

        # Passe 1 : bornes utiles via TOC
        bounds = await agent_toc_analysis(client, doc)
        first  = bounds["first_page"]
        last   = bounds["last_page"]

        # Générer les chunks entre first et last
        chunks: list[dict] = []
        p = first
        while p <= last:
            e = min(p + 7, last)   # chunks de 8 pages
            chunks.append({"name": f"Pages {p}–{e}", "page_start": p, "page_end": e})
            p = e + 1

        # Passe 2 : extraction parallèle
        tasks = [_extract_chunk(client, doc, c) for c in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_steps: list[dict] = []
        for r in results:
            if isinstance(r, list):
                all_steps.extend(r)

    # Passe 3 : fusion
    return merge_and_renumber(all_steps)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 Mo


@app.post("/api/upload")
async def upload_pdf(name: str = Form(...), file: UploadFile = File(...)):
    """Crée un projet, lance l'agent d'extraction, insère les étapes en base."""

    if not LLM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="LLM_API_KEY non configurée. Renseignez le fichier .env."
        )

    # Validation type MIME et extension
    allowed_types = {"application/pdf", "application/x-pdf"}
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    filename_lower = (file.filename or "").lower()
    if content_type not in allowed_types and not filename_lower.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    # Validation taille (lecture en mémoire avec limite)
    content = await file.read(MAX_PDF_SIZE + 1)
    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50 Mo).")

    # Validation signature PDF (%PDF-)
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Le fichier n'est pas un PDF valide.")

    # Sanitiser le nom du projet (longueur max)
    name = name.strip()[:200]
    if not name:
        raise HTTPException(status_code=400, detail="Le nom du projet est requis.")

    # 1. Créer le projet en base
    conn = get_db()
    # Stocker uniquement le nom de base du fichier, sans chemin
    safe_filename = Path(file.filename or "document.pdf").name[:255]
    cursor = conn.execute(
        "INSERT INTO projects (name, pdf_filename) VALUES (?, ?)",
        (name, safe_filename)
    )
    project_id = cursor.lastrowid
    conn.commit()

    # 2. Sauvegarder le PDF
    pdf_path = UPLOADS_DIR / f"{project_id}.pdf"
    pdf_path.write_bytes(content)

    # 3. Ouvrir le PDF
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Impossible de lire le PDF : {e}")

    # 4. Lancer l'agent d'extraction (3 passes)
    try:
        steps_data = await run_extraction_agent(doc)
    except httpx.HTTPStatusError:
        conn.close()
        raise HTTPException(status_code=502, detail="Erreur API LLM. Vérifiez votre clé dans .env.")
    except httpx.RequestError:
        conn.close()
        raise HTTPException(status_code=502, detail="Impossible de joindre l'API LLM.")
    except Exception:
        conn.close()
        raise HTTPException(status_code=500, detail="Erreur lors de l'extraction des étapes.")

    # 5. Insérer les steps en base
    inserted = []
    for s in steps_data:
        cursor = conn.execute(
            """INSERT INTO steps
               (project_id, step_number, title, description, category,
                is_critical, requires_witness, page_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                s.get("number", 0),
                s.get("title", ""),
                s.get("description", ""),
                s.get("category", ""),
                1 if s.get("is_critical") else 0,
                1 if s.get("requires_witness") else 0,
                s.get("page"),
            ),
        )
        inserted.append({
            "id":               cursor.lastrowid,
            "step_number":      s.get("number", 0),
            "title":            s.get("title", ""),
            "description":      s.get("description", ""),
            "category":         s.get("category", ""),
            "is_critical":      bool(s.get("is_critical")),
            "requires_witness": bool(s.get("requires_witness")),
            "page_ref":         s.get("page"),
            "status":           "pending",
        })

    conn.execute(
        "UPDATE projects SET total_steps = ? WHERE id = ?",
        (len(inserted), project_id)
    )
    conn.commit()
    conn.close()

    return {
        "project_id":  project_id,
        "name":        name,
        "total_steps": len(inserted),
        "steps":       inserted,
    }


@app.get("/api/projects")
def list_projects():
    """Retourne tous les projets avec leurs stats."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/api/projects/{project_id}/steps")
def get_steps(project_id: int):
    """Retourne toutes les steps d'un projet triées par numéro."""
    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    rows = conn.execute(
        "SELECT * FROM steps WHERE project_id = ? ORDER BY step_number",
        (project_id,)
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = row_to_dict(r)
        d["is_critical"]      = bool(d["is_critical"])
        d["requires_witness"] = bool(d["requires_witness"])
        result.append(d)
    return result


class ValidateBody(BaseModel):
    technician_name: str
    status: str           # "done" | "issue" | "skipped" | "active"
    note: str | None = None
    witness_name: str | None = None


class ChatBody(BaseModel):
    message: str
    step_context: str | None = None   # titre + description de l'étape active


@app.post("/api/steps/{step_id}/validate")
def validate_step(step_id: int, body: ValidateBody):
    """Valide ou signale un problème sur une étape."""
    conn = get_db()
    step = conn.execute("SELECT * FROM steps WHERE id = ?", (step_id,)).fetchone()
    if not step:
        conn.close()
        raise HTTPException(status_code=404, detail="Étape introuvable.")

    if body.status not in ("done", "issue", "skipped", "active"):
        conn.close()
        raise HTTPException(status_code=400, detail="Statut invalide.")

    if step["is_critical"] and body.status == "skipped":
        conn.close()
        raise HTTPException(status_code=400, detail="Impossible de passer une étape critique.")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """UPDATE steps SET status=?, technician_name=?, witness_name=?, note=?, validated_at=?
           WHERE id=?""",
        (body.status, body.technician_name, body.witness_name, body.note, now, step_id),
    )
    recalc_completed(conn, step["project_id"])
    conn.commit()

    updated = conn.execute("SELECT * FROM steps WHERE id = ?", (step_id,)).fetchone()
    conn.close()
    d = row_to_dict(updated)
    d["is_critical"]      = bool(d["is_critical"])
    d["requires_witness"] = bool(d["requires_witness"])
    return d


@app.get("/api/projects/{project_id}/timeline")
def get_timeline(project_id: int):
    """Retourne les steps validées triées par validated_at."""
    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    rows = conn.execute(
        """SELECT step_number, title, status, technician_name,
                  witness_name, note, validated_at
           FROM steps
           WHERE project_id = ? AND status != 'pending'
           ORDER BY validated_at ASC""",
        (project_id,)
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    """Supprime un projet, ses étapes et son PDF."""
    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    conn.execute("DELETE FROM steps WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    pdf = UPLOADS_DIR / f"{project_id}.pdf"
    if pdf.exists():
        pdf.unlink()
    return {"ok": True}


CHAT_SYSTEM_PROMPT = """Tu es l'assistant technique TraceAI. Tu aides les techniciens à comprendre et appliquer ce manuel industriel.

Voici le texte extrait du manuel (les numéros de pages sont indiqués entre --- PAGE X ---) :

{pdf_text}

{step_context_block}

Règles :
- Réponds en français, de façon précise et pratique
- Cite TOUJOURS les pages sources avec le format [p.X]
- Pour chaque valeur technique (couple, pression, température, référence), cite la page exacte
- Si une information n'est pas dans le manuel, dis-le clairement sans inventer
- Sois concis : 3 à 6 phrases, ou une liste courte si la question le demande

Retourne UNIQUEMENT ce JSON :
{{
  "answer": "Réponse complète avec citations [p.X]",
  "sources": [
    {{"page": 23, "label": "Description courte de la section source"}}
  ]
}}"""


@app.post("/api/projects/{project_id}/chat")
async def chat_with_manual(project_id: int, body: ChatBody):
    """Répond à une question sur le manuel du projet en citant les pages sources."""
    if not LLM_API_KEY:
        raise HTTPException(status_code=500, detail="LLM_API_KEY non configurée.")

    pdf_path = UPLOADS_DIR / f"{project_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF introuvable.")

    # Extraire le texte complet (limité à 18 000 chars)
    doc = fitz.open(str(pdf_path))
    parts = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            parts.append(f"--- PAGE {i + 1} ---\n{text}")
    full_text = "\n\n".join(parts)
    if len(full_text) > 18000:
        full_text = full_text[:18000]

    step_context_block = ""
    if body.step_context:
        step_context_block = f"Contexte : le technicien travaille actuellement sur — {body.step_context}"

    system = CHAT_SYSTEM_PROMPT.format(
        pdf_text=full_text,
        step_context_block=step_context_block,
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                LLM_API_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={
                    "model":    LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": body.message},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            raw = response.json()
            payload = json.loads(raw["choices"][0]["message"]["content"])
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Erreur API LLM. Vérifiez votre clé dans .env.")
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur lors de la réponse du chat.")

    return {
        "answer":  payload.get("answer", ""),
        "sources": payload.get("sources", []),
    }


@app.get("/api/projects/{project_id}/pdf/{page}")
def get_pdf_page(project_id: int, page: int):
    """Retourne une page du PDF en PNG (DPI 150)."""
    pdf_path = UPLOADS_DIR / f"{project_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF introuvable.")
    try:
        doc = fitz.open(str(pdf_path))
        if page < 1 or page > len(doc):
            raise HTTPException(status_code=400, detail="Numéro de page invalide.")
        pix = doc[page - 1].get_pixmap(dpi=150)
        return Response(content=pix.tobytes("png"), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur rendu PDF : {e}")


# ===========================================================================
# Phase 2 — Pipeline background + endpoints
# ===========================================================================

import logging
_log = logging.getLogger("traceai.phase2")


def _run_pipeline(project_id: int, job_id: int, urls: list[str]):
    """
    Pipeline synchrone (exécuté dans un thread par FastAPI BackgroundTasks).
    Enchaîne les 10 agents et met à jour batch_jobs en continu.
    """
    from agents import arborescence, tri, parser, chunker
    from agents import enrichisseur, indexeur, compilateur, qualite
    from agents import repondeur, alertes

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        proj_dir = PHASE2_DIR / str(project_id)
        file_paths = list(proj_dir.glob("**/*"))
        file_paths = [p for p in file_paths if p.is_file()]

        _log.info(f"[pipeline] projet {project_id} — {len(file_paths)} fichiers")

        # Agent 1
        machines = arborescence.run(project_id, job_id, file_paths, conn)

        # Agent 2
        unique_files = tri.run(project_id, job_id, file_paths, conn)

        # Agent 3
        parsed_docs = parser.run(project_id, job_id, unique_files, conn, urls=urls)

        # Agent 4
        chunks = chunker.run(project_id, job_id, parsed_docs, conn)

        # Agent 5 — désactivé (trop lent, 1 appel LLM/chunk)
        # enrichisseur.run(project_id, job_id, chunks, conn)

        # Agent 6
        indexeur.run(project_id, job_id, chunks, conn, chroma_dir=CHROMA_DIR)

        # Agent 7
        wiki_pages = compilateur.run(project_id, job_id, chunks, conn)

        # Agent 8
        qualite.run(project_id, job_id, wiki_pages, conn)

        # Agent 9
        repondeur.init(project_id, job_id, conn)

        # Agent 10
        alertes.run(project_id, job_id, wiki_pages, conn)

        conn.execute(
            "UPDATE batch_jobs SET status='done', completed_at=datetime('now') WHERE id=?",
            (job_id,),
        )
        conn.commit()
        _log.info(f"[pipeline] projet {project_id} — terminé")

    except Exception as e:
        _log.error(f"[pipeline] Erreur projet {project_id}: {e}", exc_info=True)
        conn.execute(
            "UPDATE batch_jobs SET status='error', completed_at=datetime('now') WHERE id=?",
            (job_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Phase 2 — Ingest
# ---------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/ingest")
async def ingest_documents(
    project_id: int,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(default=[]),
    urls: str = Form(default=""),  # JSON array ou lignes séparées
):
    """Reçoit des fichiers/ZIP/URLs, crée un batch_job et lance le pipeline."""
    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    # ── Nettoyage complet avant chaque nouveau batch ──────────────────────────
    # Supprimer les anciens fichiers du dossier projet
    proj_dir = PHASE2_DIR / str(project_id)
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Supprimer les anciennes données de ce projet en base
    conn.execute("DELETE FROM chunks     WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM documents  WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM wiki_pages WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM alerts     WHERE project_id=?", (project_id,))
    conn.commit()
    # ─────────────────────────────────────────────────────────────────────────

    # Sauvegarder et extraire les fichiers uploadés
    MAX_FILE = 500 * 1024 * 1024  # 500 Mo

    for upload in files:
        content = await upload.read(MAX_FILE + 1)
        if len(content) > MAX_FILE:
            continue
        safe_name = Path(upload.filename or "file").name[:255]
        dest = proj_dir / safe_name
        dest.write_bytes(content)

        if dest.suffix.lower() == ".zip":
            try:
                with _zipfile.ZipFile(dest) as zf:
                    zf.extractall(proj_dir)
                dest.unlink()
            except Exception:
                pass  # garder le zip si extraction échoue

    # Parser les URLs
    url_list: list[str] = []
    if urls.strip():
        try:
            url_list = json.loads(urls)
        except Exception:
            url_list = [u.strip() for u in urls.splitlines() if u.strip()]

    # Lister exactement les fichiers uploadés maintenant
    all_files = [p for p in proj_dir.rglob("*") if p.is_file()]
    total = len(all_files) + len(url_list)

    # Insérer les documents en base
    for p in all_files:
        file_type = p.suffix.lstrip(".").lower() or "unknown"
        conn.execute(
            """INSERT INTO documents
               (project_id, filename, file_type, file_path, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (project_id, p.name, file_type, str(p)),
        )
    conn.commit()

    # Créer le batch_job
    cursor = conn.execute(
        "INSERT INTO batch_jobs (project_id, total_files, status, agents_json, logs_json) VALUES (?, ?, 'running', '{}', '[]')",
        (project_id, total),
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Lancer le pipeline en background
    background_tasks.add_task(_run_pipeline, project_id, job_id, url_list)

    return {"job_id": job_id, "total_files": total, "status": "running"}


# ---------------------------------------------------------------------------
# Phase 2 — Job status
# ---------------------------------------------------------------------------

@app.patch("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: int):
    """Annule un batch en cours — le pipeline s'arrête à la prochaine vérification."""
    conn = get_db()
    row = conn.execute("SELECT status FROM batch_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Job introuvable.")
    if row[0] not in ("running",):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Job déjà {row[0]}.")
    conn.execute(
        "UPDATE batch_jobs SET status='cancelled', completed_at=datetime('now') WHERE id=?",
        (job_id,),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "job_id": job_id}


@app.get("/api/jobs/{job_id}/status")
def get_job_status(job_id: int):
    """Retourne l'état du batch + compteurs par agent + logs temps réel."""
    conn = get_db()
    row = conn.execute("SELECT * FROM batch_jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job introuvable.")
    d = row_to_dict(row)
    d["agents"] = json.loads(d.get("agents_json") or "{}")
    d["logs"]   = json.loads(d.get("logs_json")   or "[]")
    return d


# ---------------------------------------------------------------------------
# Phase 2 — Documents
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/documents")
def list_documents(project_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    conn = get_db()
    row = conn.execute("SELECT file_path FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Document introuvable.")
    conn.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    if row[0]:
        p = Path(row[0])
        if p.exists():
            p.unlink()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Phase 2 — Wiki
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/wiki")
def get_wiki_index(project_id: int):
    """Retourne l'index du wiki + liste des pages."""
    conn = get_db()
    pages = conn.execute(
        "SELECT id, page_type, page_name, title, last_compiled_at FROM wiki_pages WHERE project_id=? ORDER BY page_type, page_name",
        (project_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(p) for p in pages]


@app.get("/api/wiki/{wiki_id}")
def get_wiki_page(wiki_id: int):
    """Retourne le contenu complet d'une page wiki."""
    conn = get_db()
    row = conn.execute("SELECT * FROM wiki_pages WHERE id=?", (wiki_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Page wiki introuvable.")
    d = row_to_dict(row)
    d["contradictions"] = json.loads(d.get("contradictions_json") or "[]")
    d["gaps"] = json.loads(d.get("gaps_json") or "[]")
    return d


# ---------------------------------------------------------------------------
# Phase 2 — Chat wiki (RAG hybride)
# ---------------------------------------------------------------------------

class WikiChatBody(BaseModel):
    message: str
    conversation_id: int | None = None


@app.post("/api/projects/{project_id}/wiki-chat")
def wiki_chat(project_id: int, body: WikiChatBody):
    """Répond en utilisant le wiki (RAG hybride wiki + chroma)."""
    from agents import repondeur

    conn = get_db()

    # Gérer la conversation
    conv_id = body.conversation_id
    if not conv_id:
        cursor = conn.execute(
            "INSERT INTO conversations (project_id, title) VALUES (?, ?)",
            (project_id, body.message[:80]),
        )
        conv_id = cursor.lastrowid
        conn.commit()

    # Sauvegarder le message utilisateur
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
        (conv_id, body.message),
    )
    conn.commit()

    # Répondre
    chroma = CHROMA_DIR if CHROMA_DIR.exists() else None
    result = repondeur.answer(project_id, body.message, conn, chroma_dir=chroma)

    # Sauvegarder la réponse
    conn.execute(
        """INSERT INTO messages (conversation_id, role, content, sources_json, confidence)
           VALUES (?, 'assistant', ?, ?, ?)""",
        (
            conv_id,
            result["answer"],
            json.dumps(result["sources"], ensure_ascii=False),
            result["confidence"],
        ),
    )
    conn.commit()
    conn.close()

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result["confidence"],
        "conversation_id": conv_id,
    }


# ---------------------------------------------------------------------------
# Phase 2 — Conversations
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/conversations")
def list_conversations(project_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM conversations WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/api/conversations/{conv_id}/messages")
def get_messages(conv_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
        (conv_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = row_to_dict(r)
        d["sources"] = json.loads(d.get("sources_json") or "[]")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Phase 2 — Alertes
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/alerts")
def get_alerts(project_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE project_id=? AND is_dismissed=0 ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.patch("/api/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: int):
    conn = get_db()
    if not conn.execute("SELECT id FROM alerts WHERE id=?", (alert_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Alerte introuvable.")
    conn.execute("UPDATE alerts SET is_dismissed=1 WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Phase B — Agent autonome (Hermes-inspired)
# ---------------------------------------------------------------------------

class AgentChatBody(BaseModel):
    message: str
    mode: str = "chat"
    history: list = []
    session_id: str | None = None


@app.post("/api/projects/{project_id}/agent-chat")
def agent_chat(project_id: int, body: AgentChatBody):
    """
    Chat via l'agent autonome TraceAI (Phase B).
    Distinct de /wiki-chat qui reste sur le pipeline RAG legacy.
    mode : "chat" (défaut) | "alerte"
    """
    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    conn.close()

    from agent_core import TraceAIAgent
    agent = TraceAIAgent(project_id, DB_PATH)
    result = agent.process(
        task=body.message,
        mode=body.mode if body.mode in ("chat", "alerte", "ingestion") else "chat",
        history=body.history or [],
        session_id=body.session_id,
    )
    return {
        "answer": result["answer"],
        "iterations": result["iterations"],
        "mode": result["mode"],
        "needs_clarification": result.get("needs_clarification", False),
        "question": result.get("question", ""),
    }


@app.get("/api/projects/{project_id}/memory")
def get_project_memory(project_id: int):
    """Liste la mémoire persistante du projet (pour debug/UI)."""
    from memory_engine import list_memory
    conn = get_db()
    entries = list_memory(project_id, conn)
    conn.close()
    return entries


@app.get("/api/projects/{project_id}/skills")
def get_project_skills(project_id: int):
    """Liste les skills disponibles pour ce projet."""
    from skills_engine import list_skills
    return list_skills(project_id)


@app.get("/api/projects/{project_id}/wiki-lint")
def wiki_lint(project_id: int):
    """Rapport d'intégrité du Machine Wiki (checks LLM complets)."""
    from wiki_engine import lint_wiki
    return lint_wiki(project_id)


@app.get("/api/projects/{project_id}/wiki-health")
def wiki_health(project_id: int):
    """Health check structurel — zéro LLM, rapide. À lancer à chaque session."""
    from wiki_engine import health_check
    return health_check(project_id)


@app.get("/api/projects/{project_id}/wiki-overview")
def wiki_overview(project_id: int):
    """Retourne la synthèse vivante overview.md."""
    from wiki_engine import get_overview
    return {"content": get_overview(project_id)}


class WikiIngestBody(BaseModel):
    filename: str
    doc_type: str = "unknown"


@app.post("/api/projects/{project_id}/wiki-ingest")
def wiki_ingest(project_id: int, body: WikiIngestBody):
    """
    Ingestion LLM one-call d'un document dans le Machine Wiki.
    Génère source_page + machine_pages + entity_pages + concept_pages en 1 appel Mistral.
    """
    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    conn.close()

    from pathlib import Path as _Path
    from wiki_engine import ingest_document_llm

    uploads = _Path(__file__).parent / "uploads"
    phase2 = _Path(__file__).parent / "uploads_phase2"

    filepath = phase2 / str(project_id) / body.filename
    if not filepath.exists():
        filepath = uploads / body.filename
    if not filepath.exists():
        filepath = uploads / f"{project_id}.pdf"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {body.filename}")

    result = ingest_document_llm(project_id, filepath, body.doc_type)
    return result


class BuildGraphBody(BaseModel):
    infer: bool = True


@app.post("/api/projects/{project_id}/build-graph")
def build_project_graph(project_id: int, body: BuildGraphBody):
    """
    Construit le knowledge graph du wiki (Pass 1 EXTRACTED + Pass 2 INFERRED).
    Pass 2 utilise mistral-small — peut prendre quelques minutes.
    """
    from graph_engine import build_graph
    graph = build_graph(project_id, infer=body.infer)
    return {
        "total_nodes": graph["meta"]["total_nodes"],
        "total_edges": graph["meta"]["total_edges"],
        "extracted_edges": graph["meta"]["extracted_edges"],
        "inferred_edges": graph["meta"]["inferred_edges"],
    }


@app.get("/api/projects/{project_id}/graph")
def get_graph(project_id: int):
    """Retourne graph.json (nodes + edges)."""
    from graph_engine import load_graph
    graph = load_graph(project_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graphe non construit. Lancer POST /build-graph d'abord.")
    return graph


@app.get("/api/projects/{project_id}/graph.html")
def get_graph_html(project_id: int):
    """Sert la visualisation vis.js interactive du graphe."""
    from graph_engine import _graph_dir, generate_graph_html, load_graph
    from fastapi.responses import HTMLResponse
    html_path = _graph_dir(project_id) / "graph.html"
    if not html_path.exists():
        graph = load_graph(project_id)
        if not graph:
            raise HTTPException(status_code=404, detail="Graphe non construit.")
        generate_graph_html(project_id, graph)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/api/projects/{project_id}/wiki-heal")
def wiki_heal(project_id: int):
    """
    Auto-génère les pages d'entités manquantes (mentionnées 3+ fois sans page propre).
    Utilise mistral-small.
    """
    from graph_engine import heal_missing_entities, find_missing_entities
    missing = find_missing_entities(project_id)
    created = heal_missing_entities(project_id)
    return {
        "missing_found": len(missing),
        "pages_created": created,
    }


@app.get("/api/projects/{project_id}/graph-lint")
def graph_lint_report(project_id: int):
    """Rapport lint graph-aware : hub stubs, nœuds isolés, low-degree."""
    from graph_engine import graph_lint
    return graph_lint(project_id)
