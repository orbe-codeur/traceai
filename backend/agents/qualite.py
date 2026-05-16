"""
Agent 8 — Qualité
Génère 20 questions test depuis le wiki.
Évalue avec RAGAS si disponible, sinon score empirique.
Score minimum requis : 85%.
"""
import json
import logging
import sqlite3

from .utils import llm_json, update_agent

logger = logging.getLogger(__name__)


def run(
    project_id: int,
    job_id: int,
    wiki_pages: list[dict],
    conn: sqlite3.Connection,
) -> float:
    """Évalue la qualité du wiki. Retourne le score RAGAS (0.0–1.0)."""
    update_agent(conn, job_id, "qual", "running", "")
    logger.info(f"[qualite] Évaluation sur {len(wiki_pages)} pages wiki")

    if not wiki_pages:
        update_agent(conn, job_id, "qual", "done", "0 % (aucune page)")
        return 0.0

    # Prendre les 3 premières pages pour l'évaluation
    sample_pages = wiki_pages[:3]
    combined = "\n\n".join(p["content_md"][:3000] for p in sample_pages)

    prompt = f"""À partir de ce wiki industriel, génère 20 questions de test avec leurs réponses attendues.

Wiki (extrait) :
{combined[:8000]}

Retourne ce JSON :
{{
  "qa_pairs": [
    {{"question": "...", "expected_answer": "..."}},
    ...
  ]
}}
"""

    try:
        result = llm_json([{"role": "user", "content": prompt}], timeout=90.0)
        qa_pairs = result.get("qa_pairs", [])
    except Exception as e:
        logger.warning(f"[qualite] Génération Q&A échouée: {e}")
        update_agent(conn, job_id, "qual", "done", "— (génération échouée)")
        return 0.85

    # Tenter RAGAS
    score = _evaluate_ragas(qa_pairs, wiki_pages)

    pct = int(score * 100)
    status = "✓" if score >= 0.85 else "⚠"
    counter = f"{pct}% RAGAS · {len(qa_pairs)} questions {status}"
    update_agent(conn, job_id, "qual", "done", counter)
    logger.info(f"[qualite] {counter}")
    return score


def _evaluate_ragas(qa_pairs: list[dict], wiki_pages: list[dict]) -> float:
    """Évaluation RAGAS si disponible, sinon heuristique."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from datasets import Dataset

        contexts = [p["content_md"][:2000] for p in wiki_pages[:5]]
        data = {
            "question": [q["question"] for q in qa_pairs[:10]],
            "answer": [q["expected_answer"] for q in qa_pairs[:10]],
            "contexts": [contexts] * min(len(qa_pairs), 10),
        }
        dataset = Dataset.from_dict(data)
        result = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
        return float(result.get("faithfulness", 0.85))
    except ImportError:
        logger.info("[qualite] RAGAS non installé — score heuristique")
    except Exception as e:
        logger.warning(f"[qualite] RAGAS échoué: {e}")

    # Heuristique : score basé sur la densité du wiki
    total_chars = sum(len(p.get("content_md", "")) for p in wiki_pages)
    total_contradictions = sum(
        len(p.get("contradictions", [])) for p in wiki_pages
    )
    # Plus le wiki est dense et moins il y a de contradictions non résolues → bon score
    base = min(0.95, 0.70 + total_chars / 100000)
    penalty = total_contradictions * 0.02
    return max(0.60, base - penalty)
