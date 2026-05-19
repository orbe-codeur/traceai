"""
Réindexation forcée d'un projet dans ChromaDB.
Supprime l'ancienne collection et réembedde tous les chunks depuis SQLite (texte complet).

Usage :
  python reindex.py --project-id 7
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Charger le .env depuis la racine du projet
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

CHROMA_DIR = Path(__file__).parent / "chroma_data"
DB_PATH    = Path(__file__).parent / "traceai.db"
BATCH_SIZE = 32


def p(*args):
    print(*args, flush=True)


def reindex(project_id: int):
    conn = sqlite3.connect(str(DB_PATH))

    # 1. Charger tous les chunks depuis SQLite (texte complet)
    rows = conn.execute(
        """SELECT id, content, page_ref, machine_ref, document_id
           FROM chunks WHERE project_id=?
           ORDER BY chunk_index""",
        (project_id,),
    ).fetchall()

    if not rows:
        p(f"Aucun chunk trouvé pour le projet {project_id}.")
        return

    p(f"Projet {project_id} — {len(rows)} chunks à réindexer")
    avg_len = sum(len(r[1]) for r in rows) // len(rows)
    max_len = max(len(r[1]) for r in rows)
    p(f"  Longueur moy={avg_len} chars | max={max_len} chars")

    # 2. Supprimer l'ancienne collection ChromaDB
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection_name = f"project_{project_id}"
        try:
            client.delete_collection(collection_name)
            p(f"  Collection '{collection_name}' supprimée")
        except Exception:
            p(f"  Collection '{collection_name}' inexistante (OK)")
        collection = client.get_or_create_collection(collection_name)
        p(f"  Nouvelle collection créée")
    except ImportError:
        p("ERREUR : chromadb non installé")
        return

    # 3. Réembedder par lots
    from agents.utils import embed_texts

    indexed = 0
    errors  = 0

    # Récupérer les filenames depuis documents
    doc_filenames = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT id, filename FROM documents WHERE project_id=?", (project_id,)
        ).fetchall()
    }

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        # Pas de troncature — texte complet (Mistral Embed = 8192 tokens)
        texts     = [r[1][:30000] for r in batch]
        ids       = [str(r[0]) for r in batch]
        metadatas = [
            {
                "doc_id":   str(r[4]),
                "page":     str(r[2] or ""),
                "machine":  r[3] or "",
                "filename": doc_filenames.get(r[4], ""),
            }
            for r in batch
        ]

        try:
            embeddings = embed_texts(texts)
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )
            for r in batch:
                conn.execute(
                    "UPDATE chunks SET embedding_id=? WHERE id=?",
                    (str(r[0]), r[0]),
                )
            conn.commit()
            indexed += len(batch)
            p(f"  [{indexed}/{len(rows)}] batch {i//BATCH_SIZE + 1} OK")
        except Exception as e:
            p(f"  ERREUR batch {i//BATCH_SIZE + 1}: {e}")
            errors += 1

    p(f"\nRéindexation terminée : {indexed} chunks · {errors} erreurs")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", type=int, required=True)
    args = parser.parse_args()
    reindex(args.project_id)
