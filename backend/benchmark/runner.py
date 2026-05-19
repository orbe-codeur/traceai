"""
Benchmark RAG — mesure la qualité de retrieval avant/après chaque changement.

Usage :
  python -u benchmark/runner.py --project-id 1
  python -u benchmark/runner.py --project-id 1 --output results/baseline.json
  python -u benchmark/runner.py --compare results/baseline.json results/docling.json

Métrique : keyword recall — la réponse contient-elle les mots-clés attendus ?
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def p(*args, **kwargs):
    """Print avec flush forcé."""
    print(*args, **kwargs, flush=True)


def load_test_set(path=None):
    fp = Path(path or Path(__file__).parent / "test_set.json")
    with open(fp) as f:
        return json.load(f)


def query_rag(project_id, question):
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
        return {"answer": data.get("answer", ""), "iterations": data.get("iterations", 0), "error": None}
    except Exception as e:
        return {"answer": "", "iterations": 0, "error": str(e)}


def score_answer(answer, expected_keywords):
    answer_lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    missing = [kw for kw in expected_keywords if kw.lower() not in answer_lower]
    recall = len(found) / len(expected_keywords) if expected_keywords else 0
    return {"recall": recall, "found": found, "missing": missing, "passed": recall >= 0.5}


def run_benchmark(project_id, test_set, verbose=True):
    questions = test_set["questions"]
    results = []

    p(f"\n{'='*60}")
    p(f"Benchmark RAG — projet {project_id}")
    p(f"Démarrage : {datetime.now().strftime('%H:%M:%S')}")
    p(f"{len(questions)} questions\n")

    for i, q in enumerate(questions):
        if verbose:
            p(f"[{i+1:02d}/{len(questions)}] {q['id']} — {q['question'][:60]}...")

        t0 = time.time()
        result = query_rag(project_id, q["question"])
        elapsed = time.time() - t0

        if result["error"]:
            score = {"recall": 0, "found": [], "missing": q["expected_keywords"], "passed": False}
            if verbose:
                p(f"         ❌ ERREUR : {result['error']}")
        else:
            score = score_answer(result["answer"], q["expected_keywords"])
            status = "✅" if score["passed"] else "❌"
            if verbose:
                kw = f"trouvé {len(score['found'])}/{len(q['expected_keywords'])} keywords"
                p(f"         {status} {kw} ({elapsed:.1f}s)")
                if not score["passed"]:
                    p(f"         manquants : {score['missing']}")

        results.append({
            "id": q["id"], "type": q["type"], "difficulty": q["difficulty"],
            "question": q["question"], "answer": result["answer"][:300],
            "score": score, "elapsed": round(elapsed, 2),
            "iterations": result["iterations"], "error": result["error"],
        })
        time.sleep(1.5)

    passed = sum(1 for r in results if r["score"]["passed"])
    total = len(results)
    avg_recall = sum(r["score"]["recall"] for r in results) / total

    by_type = defaultdict(list)
    by_diff = defaultdict(list)
    for r in results:
        by_type[r["type"]].append(r["score"]["passed"])
        by_diff[r["difficulty"]].append(r["score"]["passed"])

    summary = {
        "timestamp": datetime.now().isoformat(),
        "project_id": project_id,
        "total": total, "passed": passed, "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1),
        "avg_recall": round(avg_recall * 100, 1),
        "by_type": {t: f"{sum(v)}/{len(v)} ({100*sum(v)//len(v)}%)" for t, v in by_type.items()},
        "by_difficulty": {d: f"{sum(v)}/{len(v)} ({100*sum(v)//len(v)}%)" for d, v in by_diff.items()},
        "avg_latency_s": round(sum(r["elapsed"] for r in results) / total, 1),
    }

    p(f"\n{'='*60}")
    p(f"RÉSULTATS FINAUX")
    p(f"  Score global : {passed}/{total} ({summary['pass_rate']}%)")
    p(f"  Recall moyen : {summary['avg_recall']}%")
    p(f"  Latence moy. : {summary['avg_latency_s']}s")
    p(f"\n  Par type :")
    for t, s in summary["by_type"].items():
        p(f"    {t:25} {s}")
    p(f"\n  Par difficulté :")
    for d, s in summary["by_difficulty"].items():
        p(f"    {d:25} {s}")
    p(f"{'='*60}\n")

    return {"summary": summary, "results": results}


def compare_runs(path_a, path_b):
    with open(path_a) as f: a = json.load(f)
    with open(path_b) as f: b = json.load(f)
    sa, sb = a["summary"], b["summary"]
    delta_pass = sb["pass_rate"] - sa["pass_rate"]
    delta_recall = sb["avg_recall"] - sa["avg_recall"]

    p(f"\n{'='*60}")
    p(f"COMPARAISON")
    p(f"  A : {path_a}")
    p(f"  B : {path_b}")
    p(f"\n  Pass rate : {sa['pass_rate']}% → {sb['pass_rate']}%  (Δ {delta_pass:+.1f}%)")
    p(f"  Recall    : {sa['avg_recall']}% → {sb['avg_recall']}%  (Δ {delta_recall:+.1f}%)")

    if delta_pass > 10:   verdict = "✅ MERGER — amélioration significative"
    elif delta_pass > 0:  verdict = "⚠️  INVESTIGUER — amélioration marginale"
    elif delta_pass == 0: verdict = "➡️  NEUTRE — aucun changement"
    else:                 verdict = "❌ NE PAS MERGER — régression"
    p(f"\n  Verdict : {verdict}")

    a_by_id = {r["id"]: r for r in a["results"]}
    b_by_id = {r["id"]: r for r in b["results"]}
    improvements = [qid for qid in a_by_id if qid in b_by_id
                    and not a_by_id[qid]["score"]["passed"] and b_by_id[qid]["score"]["passed"]]
    regressions  = [qid for qid in a_by_id if qid in b_by_id
                    and a_by_id[qid]["score"]["passed"] and not b_by_id[qid]["score"]["passed"]]

    if improvements: p(f"\n  Améliorées ({len(improvements)}) : {', '.join(improvements)}")
    if regressions:  p(f"  Régressées ({len(regressions)}) : {', '.join(regressions)}")
    p(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", type=int, default=1)
    parser.add_argument("--test-set", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--compare", type=str, nargs=2, metavar=("A", "B"))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.compare:
        compare_runs(args.compare[0], args.compare[1])
        sys.exit(0)

    test_set = load_test_set(args.test_set)
    data = run_benchmark(args.project_id, test_set, verbose=not args.quiet)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        p(f"Résultats sauvegardés → {args.output}")
