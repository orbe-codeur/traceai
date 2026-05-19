"""
Benchmark RAG — mesure la qualité de retrieval avant/après chaque changement.

Usage :
  python benchmark/runner.py --project-id 1
  python benchmark/runner.py --project-id 1 --output results/baseline.json
  python benchmark/runner.py --compare results/baseline.json results/docling.json

Métrique principale : keyword recall — la réponse contient-elle les mots-clés attendus ?
Simple, vérifiable manuellement, pas de LLM-as-judge.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_test_set(path: str = None) -> dict:
    p = Path(path or Path(__file__).parent / "test_set.json")
    with open(p) as f:
        return json.load(f)


def query_rag(project_id: int, question: str) -> dict:
    """
    Interroge le RAG actuel via l'agent-chat non-streaming.
    Retourne {answer, sources_pages}.
    """
    import httpx
    try:
        resp = httpx.post(
            f"http://localhost:8000/api/projects/{project_id}/agent-chat",
            json={"message": question, "mode": "chat",
                  "session_id": f"benchmark-{project_id}"},
            timeout=90.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "answer": data.get("answer", ""),
            "iterations": data.get("iterations", 0),
            "error": None,
        }
    except Exception as e:
        return {"answer": "", "iterations": 0, "error": str(e)}


def score_answer(answer: str, expected_keywords: list[str]) -> dict:
    """
    Vérifie que la réponse contient les mots-clés attendus.
    Score = fraction des keywords présents (case insensitive).
    """
    answer_lower = answer.lower()
    found = []
    missing = []
    for kw in expected_keywords:
        if kw.lower() in answer_lower:
            found.append(kw)
        else:
            missing.append(kw)

    recall = len(found) / len(expected_keywords) if expected_keywords else 0
    return {
        "recall": recall,
        "found": found,
        "missing": missing,
        "passed": recall >= 0.5,   # au moins 50% des keywords = réponse acceptable
    }


def run_benchmark(project_id: int, test_set: dict,
                  verbose: bool = True) -> dict:
    questions = test_set["questions"]
    results = []

    print(f"\n{'='*60}")
    print(f"Benchmark RAG — projet {project_id}")
    print(f"Démarrage : {datetime.now().strftime('%H:%M:%S')}")
    print(f"{len(questions)} questions\n")

    for i, q in enumerate(questions):
        if verbose:
            print(f"[{i+1:02d}/{len(questions)}] {q['id']} — {q['question'][:60]}...")

        t0 = time.time()
        result = query_rag(project_id, q["question"])
        elapsed = time.time() - t0

        if result["error"]:
            score = {"recall": 0, "found": [], "missing": q["expected_keywords"],
                     "passed": False}
            if verbose:
                print(f"         ❌ ERREUR : {result['error']}")
        else:
            score = score_answer(result["answer"], q["expected_keywords"])
            status = "✅" if score["passed"] else "❌"
            if verbose:
                kw_status = f"trouvé {len(score['found'])}/{len(q['expected_keywords'])} keywords"
                print(f"         {status} {kw_status} ({elapsed:.1f}s)")
                if not score["passed"] and verbose:
                    print(f"         manquants : {score['missing']}")

        results.append({
            "id": q["id"],
            "type": q["type"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "answer": result["answer"][:300],
            "score": score,
            "elapsed": round(elapsed, 2),
            "iterations": result["iterations"],
            "error": result["error"],
        })

        # Pause pour éviter le rate limiting
        time.sleep(1.5)

    # Agréger les résultats
    passed = sum(1 for r in results if r["score"]["passed"])
    total = len(results)
    overall_recall = sum(r["score"]["recall"] for r in results) / total

    by_type = {}
    by_difficulty = {}
    for r in results:
        t = r["type"]
        d = r["difficulty"]
        by_type.setdefault(t, []).append(r["score"]["passed"])
        by_difficulty.setdefault(d, []).append(r["score"]["passed"])

    summary = {
        "timestamp": datetime.now().isoformat(),
        "project_id": project_id,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1),
        "avg_recall": round(overall_recall * 100, 1),
        "by_type": {
            t: f"{sum(v)}/{len(v)} ({100*sum(v)//len(v)}%)"
            for t, v in by_type.items()
        },
        "by_difficulty": {
            d: f"{sum(v)}/{len(v)} ({100*sum(v)//len(v)}%)"
            for d, v in by_difficulty.items()
        },
        "avg_latency_s": round(sum(r["elapsed"] for r in results) / total, 1),
    }

    print(f"\n{'='*60}")
    print(f"RÉSULTATS FINAUX")
    print(f"  Score global : {passed}/{total} ({summary['pass_rate']}%)")
    print(f"  Recall moyen : {summary['avg_recall']}%")
    print(f"  Latence moy. : {summary['avg_latency_s']}s")
    print(f"\n  Par type :")
    for t, s in summary["by_type"].items():
        print(f"    {t:25} {s}")
    print(f"\n  Par difficulté :")
    for d, s in summary["by_difficulty"].items():
        print(f"    {d:25} {s}")
    print(f"{'='*60}\n")

    return {"summary": summary, "results": results}


def compare_runs(path_a: str, path_b: str) -> None:
    """Compare deux fichiers de résultats et affiche le delta."""
    with open(path_a) as f:
        a = json.load(f)
    with open(path_b) as f:
        b = json.load(f)

    sa = a["summary"]
    sb = b["summary"]

    delta_pass = sb["pass_rate"] - sa["pass_rate"]
    delta_recall = sb["avg_recall"] - sa["avg_recall"]

    print(f"\n{'='*60}")
    print(f"COMPARAISON")
    print(f"  A : {path_a}")
    print(f"  B : {path_b}")
    print(f"\n  Pass rate : {sa['pass_rate']}% → {sb['pass_rate']}%  "
          f"(Δ {delta_pass:+.1f}%)")
    print(f"  Recall    : {sa['avg_recall']}% → {sb['avg_recall']}%  "
          f"(Δ {delta_recall:+.1f}%)")

    if delta_pass > 10:
        verdict = "✅ MERGER — amélioration significative"
    elif delta_pass > 0:
        verdict = "⚠️  INVESTIGUER — amélioration marginale"
    elif delta_pass == 0:
        verdict = "➡️  NEUTRE — aucun changement"
    else:
        verdict = "❌ NE PAS MERGER — régression"

    print(f"\n  Verdict : {verdict}")

    # Questions qui ont changé de statut
    a_by_id = {r["id"]: r for r in a["results"]}
    b_by_id = {r["id"]: r for r in b["results"]}
    regressions = []
    improvements = []
    for qid in a_by_id:
        if qid not in b_by_id:
            continue
        was_pass = a_by_id[qid]["score"]["passed"]
        now_pass = b_by_id[qid]["score"]["passed"]
        if not was_pass and now_pass:
            improvements.append(qid)
        elif was_pass and not now_pass:
            regressions.append(qid)

    if improvements:
        print(f"\n  Améliorées ({len(improvements)}) : {', '.join(improvements)}")
    if regressions:
        print(f"  Régressées ({len(regressions)}) : {', '.join(regressions)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark RAG TraceAI")
    parser.add_argument("--project-id", type=int, default=1)
    parser.add_argument("--test-set", type=str, default=None,
                        help="Chemin vers le fichier test_set.json")
    parser.add_argument("--output", type=str, default=None,
                        help="Sauvegarder les résultats en JSON")
    parser.add_argument("--compare", type=str, nargs=2, metavar=("A", "B"),
                        help="Comparer deux fichiers de résultats")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.compare:
        compare_runs(args.compare[0], args.compare[1])
        sys.exit(0)

    test_set = load_test_set(args.test_set)
    run_data = run_benchmark(args.project_id, test_set, verbose=not args.quiet)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(run_data, f, ensure_ascii=False, indent=2)
        print(f"Résultats sauvegardés → {args.output}")
