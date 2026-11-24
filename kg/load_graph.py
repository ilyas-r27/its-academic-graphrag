"""Load parsed JSON (and optionally reviewed concepts) into Neo4j.

Usage:
    python -m kg.load_graph data/processed/PR33-2025.json
    python -m kg.load_graph data/processed/PR33-2025.json --menggantikan PR18-2023
    python -m kg.load_graph data/processed/PR33-2025.json --konsep data/processed/PR33-2025_konsep.json

Safe to re-run: everything uses MERGE.
"""
import argparse
import json
from pathlib import Path

from kg.config import get_driver

SCHEMA_FILE = Path(__file__).parent / "cypher" / "schema.cypher"

Q_DOKUMEN = """
MERGE (d:Dokumen {id: $doc.id})
SET d.judul = $doc.judul, d.tahun = $doc.tahun, d.file = $doc.file
"""

Q_PASAL = """
MATCH (d:Dokumen {id: $doc_id})
UNWIND $rows AS p
MERGE (b:Bab {id: $doc_id + ':BAB-' + p.bab})
SET b.nomor = p.bab, b.judul = p.bab_judul, b.dokumen = $doc_id
MERGE (b)-[:BAGIAN_DARI]->(d)
MERGE (x:Pasal {id: p.id})
SET x.nomor = p.nomor, x.isi = p.isi, x.dokumen = $doc_id,
    x.bab = p.bab, x.bagian = p.bagian, x.bagian_judul = p.bagian_judul
MERGE (x)-[:BAGIAN_DARI]->(b)
"""

Q_AYAT = """
UNWIND $rows AS a
MATCH (p:Pasal {id: a.pasal_id})
MERGE (y:Ayat {id: a.id})
SET y.nomor = a.nomor, y.isi = a.isi
MERGE (y)-[:BAGIAN_DARI]->(p)
"""

Q_RUJUKAN = """
UNWIND $rows AS r
MATCH (a:Pasal {id: r.src}), (b:Pasal {id: r.dst})
MERGE (a)-[:MERUJUK_KE]->(b)
"""

Q_MENGGANTIKAN = """
MATCH (new:Dokumen {id: $new}), (old:Dokumen {id: $old})
MERGE (new)-[:MENGGANTIKAN]->(old)
"""

Q_KONSEP = """
UNWIND $rows AS r
MATCH (p:Pasal {id: r.pasal_id})
MERGE (k:Konsep {nama: r.konsep})
MERGE (p)-[:MENGATUR]->(k)
"""


def apply_schema(session) -> None:
    for stmt in SCHEMA_FILE.read_text().split(";"):
        if stmt.strip():
            session.run(stmt)


def load(path: Path, menggantikan: str | None, konsep_path: Path | None) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    doc = data["dokumen"]
    pasal = data["pasal"]
    ayat_rows = [{**a, "pasal_id": p["id"]} for p in pasal for a in p["ayat"]]
    ref_rows = [
        {"src": p["id"], "dst": f"{doc['id']}:P{r}"} for p in pasal for r in p["rujukan"]
    ]

    with get_driver() as driver, driver.session() as s:
        apply_schema(s)
        s.run(Q_DOKUMEN, doc=doc)
        s.run(Q_PASAL, doc_id=doc["id"], rows=pasal)
        s.run(Q_AYAT, rows=ayat_rows)
        s.run(Q_RUJUKAN, rows=ref_rows)
        if menggantikan:
            s.run(Q_MENGGANTIKAN, new=doc["id"], old=menggantikan)
        if konsep_path:
            mapping = json.loads(konsep_path.read_text(encoding="utf-8"))
            rows = [
                {"pasal_id": pid, "konsep": k.strip()}
                for pid, ks in mapping.items()
                for k in ks
                if k.strip()
            ]
            s.run(Q_KONSEP, rows=rows)
            print(f"{len(rows)} relasi MENGATUR dimuat")

    print(f"{doc['id']}: {len(pasal)} pasal, {len(ayat_rows)} ayat, {len(ref_rows)} rujukan dimuat")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_file", type=Path)
    ap.add_argument("--menggantikan", help="doc id of the older regulation this one replaces")
    ap.add_argument("--konsep", type=Path, help="reviewed concept mapping JSON")
    args = ap.parse_args()
    load(args.json_file, args.menggantikan, args.konsep)


if __name__ == "__main__":
    main()
