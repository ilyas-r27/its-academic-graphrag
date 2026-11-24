"""CLI for asking questions.

Usage:
    python -m kg.ask "Berapa lama maksimal cuti akademik?"
    python -m kg.ask "..." --mode vector --show-context
    python -m kg.ask                      # interactive mode
"""
import argparse

from kg.retrieve import answer


def run(q: str, args) -> None:
    res = answer(q, mode=args.mode, k=args.k, doc=args.doc)
    if res.get("cypher"):
        print(f"\n[Cypher]\n{res['cypher']}")
    if res.get("error"):
        print(f"[Error] {res['error']}")
    print(f"\n{res['answer']}\n")
    if res.get("items"):
        src = ", ".join(f"Pasal {i['nomor']} ({i['sumber']})" for i in res["items"])
        print(f"Sumber: {src}")
    if args.show_context:
        print(f"\n--- konteks ---\n{res['context']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="?")
    ap.add_argument("--mode", choices=["hybrid", "vector", "cypher"], default="hybrid")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--doc", default=None, help="limit to one document id, e.g. PR33-2025")
    ap.add_argument("--show-context", action="store_true")
    args = ap.parse_args()

    if args.question:
        run(args.question, args)
        return
    print("Ketik pertanyaan (kosongkan untuk keluar).")
    while True:
        q = input("\n> ").strip()
        if not q:
            break
        run(q, args)


if __name__ == "__main__":
    main()
