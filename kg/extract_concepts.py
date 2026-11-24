"""Use the LLM to propose which Konsep each Pasal regulates. Output is a DRAFT for manual review.

Usage:
    python -m kg.extract_concepts data/processed/PR33-2025.json --limit 5   # try a few first
    python -m kg.extract_concepts data/processed/PR33-2025.json

Writes data/processed/<doc-id>_konsep.json  ({pasal_id: [konsep, ...]}).
Review and fix that file by hand, then load it with kg.load_graph --konsep.
Concepts listed in data/konsep_seed.txt (one per line) are preferred, so names stay consistent.
"""
import argparse
import json
from pathlib import Path

from kg.config import ROOT
from kg.llm import chat_json

SEED_FILE = ROOT / "data" / "konsep_seed.txt"

SYSTEM = (
    "Kamu membantu membangun knowledge graph peraturan akademik. "
    "Jawab hanya dengan JSON yang valid."
)

PROMPT = """Daftar konsep yang sudah ada (pakai nama yang sama persis jika cocok):
{seed}

Teks Pasal {nomor} (Bab: {bab}):
\"\"\"{isi}\"\"\"

Tentukan 1 sampai 4 konsep akademik utama yang DIATUR oleh pasal ini.
Gunakan frasa benda singkat dalam Bahasa Indonesia, Title Case (contoh: "Cuti Akademik", "Beban Studi").
Buat konsep baru hanya jika tidak ada yang cocok di daftar.
Format: {{"konsep": ["...", "..."]}}"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_file", type=Path)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    doc_id = data["dokumen"]["id"]
    out = args.json_file.with_name(f"{doc_id}_konsep.json")
    result: dict[str, list[str]] = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}

    seed = [l.strip() for l in SEED_FILE.read_text(encoding="utf-8").splitlines() if l.strip()] if SEED_FILE.exists() else []
    known = list(dict.fromkeys(seed + [k for ks in result.values() for k in ks]))

    todo = [p for p in data["pasal"] if p["id"] not in result and p["isi"]]
    if args.limit:
        todo = todo[: args.limit]

    for i, p in enumerate(todo, 1):
        prompt = PROMPT.format(
            seed="\n".join(f"- {k}" for k in known) or "(belum ada)",
            nomor=p["nomor"],
            bab=p["bab_judul"],
            isi=p["isi"][:4000],
        )
        try:
            konsep = [k.strip() for k in chat_json(prompt, SYSTEM).get("konsep", []) if k.strip()]
        except Exception as e:  # keep going, the file is resumable
            print(f"[{p['id']}] gagal: {e}")
            continue
        result[p["id"]] = konsep
        known.extend(k for k in konsep if k not in known)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{i}/{len(todo)} Pasal {p['nomor']}: {konsep}")

    print(f"Selesai. {len(result)} pasal, {len(known)} konsep unik -> {out}")
    print("Review file ini secara manual sebelum dimuat ke Neo4j.")


if __name__ == "__main__":
    main()
