"""Parse a regulation PDF into structured JSON: Bab > Bagian > Pasal > Ayat.

Usage:
    python -m kg.parse_pdf data/raw/peraturan-akademik-2025.pdf --doc-id PR33-2025 \
        --judul "Peraturan Rektor ITS No. 33 Tahun 2025 tentang Peraturan Akademik" --tahun 2025

Output: data/processed/<doc-id>.json

Always spot-check the output against the PDF. PDF text extraction is never perfect.
"""
import argparse
import json
import re
from pathlib import Path

from kg.config import DATA_PROCESSED

RE_BAB = re.compile(r"^BAB\s+([IVXLC]+)\s*$")
RE_BAGIAN = re.compile(r"^Bagian\s+(Ke\w+)\s*$", re.IGNORECASE)
RE_PARAGRAF = re.compile(r"^Paragraf\s+\d+\s*$", re.IGNORECASE)
RE_PASAL = re.compile(r"^Pasal\s+(\d+)([A-Z]?)\s*$")
RE_AYAT = re.compile(r"^\((\d+)\)\s*")
RE_LIST_ITEM = re.compile(r"^([a-z]|\d{1,2})\.\s")
RE_REF = re.compile(r"Pasal\s+(\d+[A-Z]?)(?:\s+sampai\s+dengan\s+Pasal\s+(\d+[A-Z]?))?")
# A "Pasal N" followed by the name of another regulation is an external reference.
RE_EXTERNAL = re.compile(
    r"^\s*(ayat\s*\(\d+\)\s*)?(huruf\s+\w\s*)?(Undang|Peraturan\s+(Pemerintah|Presiden|Menteri|Majelis|Senat))",
    re.IGNORECASE,
)
NOISE = [
    re.compile(r"^-\s*\d+\s*-$"),          # page numbers like "- 3 -"
    re.compile(r"^\d+\s*$"),               # bare page numbers
    re.compile(r"^SALINAN$", re.IGNORECASE),
]
STOP_MARKERS = ("Ditetapkan di", "Salinan sesuai dengan aslinya")


def extract_lines(pdf_path: Path) -> list[str]:
    import pymupdf

    lines = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            for raw in page.get_text("text").splitlines():
                s = " ".join(raw.split())
                if s and not any(r.match(s) for r in NOISE):
                    lines.append(s)
    return lines


def _is_title_line(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and s.upper() == s


def _to_paragraphs(lines: list[str]) -> list[str]:
    """Re-join wrapped lines. A new paragraph starts at an ayat '(n)' or a list item 'a.' / '1.'."""
    paras: list[str] = []
    for s in lines:
        if not paras or RE_AYAT.match(s) or RE_LIST_ITEM.match(s):
            paras.append(s)
        else:
            paras[-1] += " " + s
    return paras


def _split_ayat(paras: list[str]) -> list[dict]:
    ayat: list[dict] = []
    for p in paras:
        m = RE_AYAT.match(p)
        if m:
            ayat.append({"nomor": m.group(1), "isi": p[m.end():].strip()})
        elif ayat:
            ayat[-1]["isi"] += "\n" + p
    return ayat


def _num_key(nomor: str) -> tuple[int, str]:
    m = re.match(r"(\d+)([A-Z]?)", nomor)
    return int(m.group(1)), m.group(2)


def find_references(text: str, own: str) -> list[str]:
    refs: list[str] = []
    for m in RE_REF.finditer(text):
        if RE_EXTERNAL.match(text[m.end(): m.end() + 60]):
            continue
        start, end = m.group(1), m.group(2)
        if end:
            a, b = _num_key(start)[0], _num_key(end)[0]
            nums = [str(n) for n in range(a, b + 1)] if 0 < b - a <= 30 else [start, end]
        else:
            nums = [start]
        for n in nums:
            if n != own and n not in refs:
                refs.append(n)
    return refs


def parse(lines: list[str], doc_id: str) -> list[dict]:
    pasal_list: list[dict] = []
    cur = None
    bab, bab_judul = "0", ""
    bagian, bagian_judul = None, None
    state = None  # "bab_title" | "bagian_title" | "paragraf_title" | None
    started = False
    last_num = 0

    for s in lines:
        if s.startswith(STOP_MARKERS):
            break

        m = RE_BAB.match(s)
        if m:
            started = True
            bab, bab_judul = m.group(1), ""
            bagian = bagian_judul = None
            state = "bab_title"
            continue
        if not started:
            continue  # skip preamble (Menimbang, Mengingat, Memutuskan)

        m = RE_PASAL.match(s)
        if m:
            num, suffix = int(m.group(1)), m.group(2)
            # Accept as a heading only if numbering is sequential. A wrapped inline
            # reference like "...dalam\nPasal 12\nayat (1)" would break the sequence.
            if (suffix and num == last_num) or (not suffix and last_num < num <= last_num + 2):
                nomor = f"{num}{suffix}"
                cur = {
                    "id": f"{doc_id}:P{nomor}",
                    "dokumen": doc_id,
                    "nomor": nomor,
                    "bab": bab,
                    "bab_judul": bab_judul,
                    "bagian": bagian,
                    "bagian_judul": bagian_judul,
                    "_lines": [],
                }
                pasal_list.append(cur)
                last_num = num
                state = None
                continue

        if state == "bab_title" and _is_title_line(s):
            bab_judul = f"{bab_judul} {s}".strip()
            continue
        if state == "bagian_title":
            bagian_judul = s
            state = None
            continue
        if state == "paragraf_title":
            state = None
            continue
        state = None

        m = RE_BAGIAN.match(s)
        if m:
            bagian, bagian_judul = m.group(1), None
            state = "bagian_title"
            continue
        if RE_PARAGRAF.match(s):
            state = "paragraf_title"
            continue

        if cur is not None:
            cur["_lines"].append(s)

    for p in pasal_list:
        paras = _to_paragraphs(p.pop("_lines"))
        p["isi"] = "\n".join(paras)
        p["ayat"] = [
            {"id": f"{p['id']}:A{a['nomor']}", **a} for a in _split_ayat(paras)
        ]
        p["rujukan"] = find_references(p["isi"], p["nomor"])

    known = {p["nomor"] for p in pasal_list}
    for p in pasal_list:
        p["rujukan"] = [r for r in p["rujukan"] if r in known]
    return pasal_list


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--doc-id", required=True, help="Short id, e.g. PR33-2025")
    ap.add_argument("--judul", default="")
    ap.add_argument("--tahun", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    pasal = parse(extract_lines(args.pdf), args.doc_id)
    out = args.out or DATA_PROCESSED / f"{args.doc_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dokumen": {"id": args.doc_id, "judul": args.judul, "tahun": args.tahun, "file": args.pdf.name},
        "pasal": pasal,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    n_ayat = sum(len(p["ayat"]) for p in pasal)
    n_ref = sum(len(p["rujukan"]) for p in pasal)
    babs = sorted({p["bab"] for p in pasal}, key=lambda b: len(b))
    print(f"{len(pasal)} pasal, {n_ayat} ayat, {n_ref} rujukan antar pasal, {len(babs)} bab -> {out}")
    empty = [p["nomor"] for p in pasal if not p["isi"]]
    if empty:
        print(f"WARNING: pasal tanpa isi: {empty} (cek PDF)")


if __name__ == "__main__":
    main()
