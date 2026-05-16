"""
Agent 6 — Indexeur
Génère des embeddings BGE-M3 et les stocke dans ChromaDB.
Dégradation gracieuse si sentence-transformers ou chromadb n'est pas installé.
"""
import logging
import sqlite3
from pathlib import Path

from .utils import update_agent

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


def _get_embedding_model():
    """Charge BGE-M3, retourne None si non disponible."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("BAAI/bge-m3")
    except ImportError:
        logger.warning("[indexeur] sentence-transformers non installé — embeddings ignorés")
        return None
    except Exception as e:
        logger.warning(f"[indexeur] Modèle embedding échoué: {e}")
        return None


def run(
    project_id: int,
    job_id: int,
    chunks: list[dict],
    conn: sqlite3.Connection,
    chroma_dir: Path | None = None,
) -> bool:
    """
    Indexe les chunks dans ChromaDB avec embeddings BGE-M3.
    Retourne True si l'indexation a eu lieu, False si dégradée.
    """
    update_agent(conn, job_id, "index", "running", "")
    logger.info(f"[indexeur] {len(chunks)} chunks à indexer")

    if not chroma_dir:
        update_agent(conn, job_id, "index", "done", f"{len(chunks)} chunks (texte seul)")
        return False

    collection = _get_chroma_collection(chroma_dir, project_id)
    model = _get_embedding_model()

    if not collection or not model:
        # Mode dégradé : pas d'embeddings, la recherche se fera en texte seul
        update_agent(conn, job_id, "index", "done", f"{len(chunks)} chunks (texte seul)")
        return False

    # Indexer par lots de 32
    batch_size = 32
    indexed = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["content"][:2000] for c in batch]
        ids = [str(c["id"]) for c in batch]
        metadatas = [
            {
                "doc_id": str(c.get("doc_id", "")),
                "page": str(c.get("page_ref", "")),
                "machine": c.get("machine_ref", "") or "",
                "category": c.get("category", "") or "",
                "filename": c.get("filename", "") or "",
            }
            for c in batch
        ]

        try:
            embeddings = model.encode(texts, show_progress_bar=False).tolist()
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )
            # Stocker l'embedding_id
            for chunk in batch:
                conn.execute(
                    "UPDATE chunks SET embedding_id=? WHERE id=?",
                    (str(chunk["id"]), chunk["id"]),
                )
            conn.commit()
            indexed += len(batch)
        except Exception as e:
            logger.error(f"[indexeur] Batch {i}: {e}")

    counter = f"{indexed} embeddings BGE-M3 → ChromaDB"
    update_agent(conn, job_id, "index", "done", counter)
    logger.info(f"[indexeur] {counter}")
    return True
