"""
Agent 9 — Répondeur
RAG hybride : cherche dans wiki_pages (texte) + ChromaDB (sémantique).
Re-rank. Génère une réponse avec citations [Document, Page].
"""
import json
import logging
import sqlite3

from .utils import llm_json, update_agent, embed_texts

logger = logging.getLogger(__name__)

REPONDEUR_SYSTEM = """Tu es l'assistant technique TraceAI. Tu aides les techniciens à trouver des informations précises dans la base de connaissances machine.

Voici les extraits de documentation les plus pertinents :

{context}

Règles :
- Réponds en français, de façon précise et pratique
- Cite TOUJOURS les sources avec le format [Fichier, p.X] ou [Machine Wiki]
- Pour chaque valeur technique (couple, pression, température, référence), cite la source exacte
- Si une information n'est pas dans les extraits, dis-le clairement sans inventer
- Sois concis : 3 à 6 phrases, ou une liste courte si la question le demande

Retourne ce JSON :
{{
  "answer": "Réponse avec citations",
  "sources": [
    {{"label": "Description de la source", "page": 12, "filename": "manuel.pdf"}}
  ],
  "confidence": 0.87
}}"""


def init(
    project_id: int,
    job_id: int,
    conn: sqlite3.Connection,
) -> None:
    """Initialisation de l'agent répondeur (vérifie que le wiki est prêt)."""
    update_agent(conn, job_id, "rep", "running", "")
    wiki_count = conn.execute(
        "SELECT COUNT(*) FROM wiki_pages WHERE project_id=? AND page_type='machine'",
        (project_id,),
    ).fetchone()[0]
    update_agent(conn, job_id, "rep", "done", f"API prête · {wiki_count} pages wiki")
    logger.info(f"[rep] Répondeur initialisé — {wiki_count} pages wiki")


def answer(
    project_id: int,
    question: str,
    conn: sqlite3.Connection,
    chroma_dir=None,
    conversation_id: int | None = None,
) -> dict:
    """
    Répond à une question en utilisant le RAG hybride.
    1. Cherche dans le wiki (SQLite full-text like)
    2. Si ChromaDB disponible, cherche aussi par sémantique
    3. Re-rank par pertinence
    4. Génère la réponse avec le LLM
    """
    # Étape 1 : recherche textuelle dans le wiki
    wiki_results = _search_wiki(project_id, question, conn, limit=5)

    # Étape 2 : recherche sémantique dans ChromaDB
    chroma_results = _search_chroma(project_id, question, chroma_dir, limit=5)

    # Étape 3 : fusion et déduplication
    all_results = _merge_results(wiki_results, chroma_results)

    # Étape 4 : construction du contexte
    context = _build_context(all_results)

    # Étape 5 : réponse LLM
    try:
        result = llm_json(
            [
                {
                    "role": "system",
                    "content": REPONDEUR_SYSTEM.format(context=context),
                },
                {"role": "user", "content": question},
            ],
            timeout=60.0,
        )
    except Exception as e:
        logger.error(f"[rep] LLM échoué: {e}")
        return {
            "answer": "Je ne peux pas répondre pour le moment. Veuillez réessayer.",
            "sources": [],
            "confidence": 0.0,
        }

    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.8),
    }


def _search_wiki(project_id: int, query: str, conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    """Recherche dans les pages wiki par mots-clés."""
    words = [w.strip() for w in query.split() if len(w.strip()) > 2]
    if not words:
        # Retourner les premières pages wiki
        rows = conn.execute(
            "SELECT title, content_md FROM wiki_pages WHERE project_id=? AND page_type='machine' LIMIT ?",
            (project_id, limit),
        ).fetchall()
        return [{"title": r[0], "content": r[1][:2000], "source": "wiki"} for r in rows]

    # Recherche LIKE sur les mots
    conditions = " OR ".join(["content_md LIKE ?" for _ in words])
    params = [f"%{w}%" for w in words] + [project_id, limit]
    rows = conn.execute(
        f"SELECT title, content_md FROM wiki_pages WHERE ({conditions}) AND project_id=? LIMIT ?",
        params,
    ).fetchall()
    return [{"title": r[0], "content": r[1][:2000], "source": "wiki"} for r in rows]


def _search_chroma(project_id: int, query: str, chroma_dir, limit: int = 5) -> list[dict]:
    """Recherche sémantique dans ChromaDB."""
    if not chroma_dir:
        return []
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.get_collection(f"project_{project_id}")
        embedding = embed_texts([query])[0]

        results = collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            include=["documents", "metadatas"],
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [
            {
                "content": doc,
                "title": meta.get("filename", ""),
                "page": meta.get("page"),
                "source": "chroma",
            }
            for doc, meta in zip(docs, metas)
        ]
    except Exception:
        return []


def _merge_results(wiki: list[dict], chroma: list[dict]) -> list[dict]:
    """Fusionne et déduplique les résultats."""
    seen = set()
    merged = []
    for r in wiki + chroma:
        key = r["content"][:100]
        if key not in seen:
            seen.add(key)
            merged.append(r)
    return merged[:8]


def _build_context(results: list[dict]) -> str:
    parts = []
    for r in results:
        title = r.get("title", "")
        page = r.get("page")
        src = f"[{title}" + (f", p.{page}" if page else "") + "]"
        parts.append(f"{src}\n{r['content'][:1500]}")
    return "\n\n---\n\n".join(parts) if parts else "Aucun document disponible."
