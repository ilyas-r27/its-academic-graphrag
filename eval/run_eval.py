"""Compare retrieval modes on the test questions.

Usage:
    python -m eval.run_eval                         # all modes, all questions
    python -m eval.run_eval --modes vector hybrid --no-answer   # retrieval only (no LLM cost)

Metric (automatic): hit@k = at least one pasal_acuan appears in the retrieved pasal.
Answer quality is graded by hand: open the CSV and fill the "nilai" column (0 / 0.5 / 1).
Questions whose pasal_acuan still contains "TODO" are skipped.
"""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from kg.retrieve import answer, hybrid_search, vector_search

HERE = Path(__file__).parent


def load_questions() -> list[dict]:
    qs = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [q for q in qs if "TODO" not in q["pasal_acuan"]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modes", nargs="+", default=["vector", "hybrid", "cypher"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--doc", default=None)
    ap.add_argument("--no-answer", action="store_true", help="skip LLM answers, retrieval metrics only")
    args = ap.parse_args()

    questions = load_questions()
    if not questions:
        print("Belum ada pertanyaan dengan pasal_acuan terisi di eval/questions.jsonl")
        return

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M%S}.csv"
    summary: dict[str, list[int]] = {m: [] for m in args.modes}

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "kategori", "mode", "hit", "pasal_diambil", "pasal_acuan", "jawaban", "cypher", "error", "nilai"])
        for q in questions:
            for mode in args.modes:
                if args.no_answer and mode != "cypher":
                    search = hybrid_search if mode == "hybrid" else vector_search
                    res = {"items": search(q["pertanyaan"], args.k, args.doc), "answer": ""}
                elif args.no_answer:
                    continue
                else:
                    res = answer(q["pertanyaan"], mode=mode, k=args.k, doc=args.doc)
                got = [i["nomor"] for i in res.get("items", [])]
                hit = int(any(p in got for p in q["pasal_acuan"])) if mode != "cypher" else ""
                if hit != "":
                    summary[mode].append(hit)
                w.writerow([q["id"], q["kategori"], mode, hit, " ".join(got), " ".join(q["pasal_acuan"]),
                            res.get("answer", ""), res.get("cypher", ""), res.get("error", ""), ""])
                print(f"{q['id']} {mode:7s} hit={hit}")

    for mode, hits in summary.items():
        if hits:
            print(f"{mode:7s} hit@{args.k} = {sum(hits)}/{len(hits)} ({sum(hits) / len(hits):.0%})")
    print(f"Hasil: {out}  (isi kolom 'nilai' secara manual)")


if __name__ == "__main__":
    main()
