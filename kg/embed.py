"""Compute embeddings for every Pasal and create the vector index.

Usage:
    python -m kg.embed            # only pasal without an embedding
    python -m kg.embed --all      # recompute everything (after changing EMBED_MODEL)
"""
import argparse

from kg.config import VECTOR_INDEX, get_driver
from kg.embeddings import embed_texts

BATCH = 32


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    where = "" if args.all else "WHERE p.embedding IS NULL"
    with get_driver() as driver, driver.session() as s:
        rows = s.run(
            f"""MATCH (p:Pasal)-[:BAGIAN_DARI]->(b:Bab) {where}
                RETURN p.id AS id, p.nomor AS nomor, p.isi AS isi, b.judul AS bab"""
        ).data()
        if not rows:
            print("Semua pasal sudah punya embedding.")
            return

        dim = None
        for i in range(0, len(rows), BATCH):
            batch = rows[i: i + BATCH]
            texts = [f"Pasal {r['nomor']} ({r['bab']}): {r['isi']}" for r in batch]
            vecs = embed_texts(texts, kind="passage")
            dim = len(vecs[0])
            s.run(
                "UNWIND $rows AS r MATCH (p:Pasal {id: r.id}) SET p.embedding = r.vec",
                rows=[{"id": r["id"], "vec": v} for r, v in zip(batch, vecs)],
            )
            print(f"{min(i + BATCH, len(rows))}/{len(rows)}")

        s.run(
            f"""CREATE VECTOR INDEX {VECTOR_INDEX} IF NOT EXISTS
                FOR (p:Pasal) ON p.embedding
                OPTIONS {{indexConfig: {{`vector.dimensions`: {int(dim)},
                                         `vector.similarity_function`: 'cosine'}}}}"""
        )
        print(f"Vector index '{VECTOR_INDEX}' siap (dim={dim}).")


if __name__ == "__main__":
    main()
