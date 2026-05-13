import asyncio
import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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

UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

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
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.on_event("startup")
def startup():
    init_db()


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
