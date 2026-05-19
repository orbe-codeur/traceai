"""
Agent 6 — Indexeur
Génère des embeddings BGE-M3 et les stocke dans ChromaDB.
Dégradation gracieuse si sentence-transformers ou chromadb n'est pas installé.
"""
import logging
import sqlite3
from pathlib import Path

from .utils import update_agent, embed_texts

logger = logging.getLogger(__name__)


def _get_chroma_collection(chroma_dir: Path, project_id: int):
    """Retourne la collection ChromaDB pour ce projet, ou None si indisponible."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_dir))
        return client.get_or_create_collection(f"project_{project_id}")
    except ImportError:
        logger.warning("[indexeur] chromadb non installé — indexation vectorielle ignorée")
        return None
    except Exception as e:
        logger.warning(f"[indexeur] ChromaDB init échoué: {e}")
        return None


def run(
    project_id: int,
    job_id: int,
    chunks: list[dict],
    conn: sqlite3.Connection,
    chroma_dir: Path | None = None,
) -> bool:
    """
    Indexe les chunks dans ChromaDB avec embeddings Mistral.
    Retourne True si l'indexation a eu lieu, False si dégradée.
    """
    update_agent(conn, job_id, "index", "running", "")
    logger.info(f"[indexeur] {len(chunks)} chunks à indexer")

    if not chroma_dir:
        update_agent(conn, job_id, "index", "done", f"{len(chunks)} chunks (texte seul)")
        return False

    collection = _get_chroma_collection(chroma_dir, project_id)
    if not collection:
        update_agent(conn, job_id, "index", "done", f"{len(chunks)} chunks (texte seul)")
        return False

    # Indexer par lots de 32
    batch_size = 32
    indexed = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        # Mistral Embed supporte 8192 tokens (~32 000 chars) — pas de troncature artificielle
        texts = [c["content"][:30000] for c in batch]
        ids = [str(c["id"]) for c in batch]
        metadatas = [
            {
                "doc_id":       str(c.get("doc_id", "")),
                "page":         str(c.get("page_ref", "") or ""),
                "machine":      c.get("machine_ref", "") or "",
                "doc_type":     c.get("doc_type", "") or "",
                "manufacturer": c.get("manufacturer", "") or "",
                "language":     c.get("language", "") or "",
                "is_table":     str(c.get("is_table", False)),
                "chunk_method": c.get("chunk_method", "") or "",
                "section":      (c.get("section_ref", "") or "")[:200],
                "filename":     c.get("filename", "") or "",
            }
            for c in batch
        ]

        try:
            embeddings = embed_texts(texts)
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )
            for chunk in batch:
                conn.execute(
                    "UPDATE chunks SET embedding_id=? WHERE id=?",
                    (str(chunk["id"]), chunk["id"]),
                )
            conn.commit()
            indexed += len(batch)
        except Exception as e:
            logger.error(f"[indexeur] Batch {i}: {e}")

    counter = f"{indexed} embeddings Mistral → ChromaDB"
    update_agent(conn, job_id, "index", "done", counter)
    logger.info(f"[indexeur] {counter}")
    return True
