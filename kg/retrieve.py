"""Retrieval strategies + answer generation.

Modes:
    vector  : top-k pasal by embedding similarity (baseline, "RAG biasa")
    hybrid  : vector search, then expand through the graph (MERUJUK_KE + shared Konsep)
    cypher  : LLM writes a read-only Cypher query (Text2Cypher)
"""
import re

from kg import llm
from kg.config import VECTOR_INDEX, get_driver
from kg.embeddings import embed_texts

Q_VECTOR = f"""
CALL db.index.vector.queryNodes('{VECTOR_INDEX}', $fetch, $vec) YIELD node AS p, score
WHERE $doc IS NULL OR p.dokumen = $doc
RETURN p.id AS id, p.nomor AS nomor, p.dokumen AS dokumen, p.isi AS isi, score
ORDER BY score DESC LIMIT $k
"""

Q_EXPAND = """
UNWIND $ids AS pid
MATCH (p:Pasal {id: pid})
OPTIONAL MATCH (p)-[:MERUJUK_KE]->(ref:Pasal)
WITH p, collect(DISTINCT ref)[..$max_ref] AS refs
OPTIONAL MATCH (p)-[:MENGATUR]->(:Konsep)<-[:MENGATUR]-(t:Pasal)
WHERE t <> p AND t.dokumen = p.dokumen
WITH p, refs, collect(DISTINCT t)[..$max_related] AS related
RETURN p.id AS seed,
       [r IN refs | r {.id, .nomor, .dokumen, .isi}] AS rujukan,
       [t IN related | t {.id, .nomor, .dokumen, .isi}] AS terkait
"""

GRAPH_SCHEMA = """Nodes:
  (:Dokumen {id, judul, tahun})
  (:Bab {id, nomor, judul, dokumen})
  (:Pasal {id, nomor, isi, dokumen, bab, bagian, bagian_judul})
  (:Ayat {id, nomor, isi})
  (:Konsep {nama})
Relationships:
  (:Bab)-[:BAGIAN_DARI]->(:Dokumen)
  (:Pasal)-[:BAGIAN_DARI]->(:Bab)
  (:Ayat)-[:BAGIAN_DARI]->(:Pasal)
  (:Pasal)-[:MERUJUK_KE]->(:Pasal)
  (:Pasal)-[:MENGATUR]->(:Konsep)
  (:Dokumen)-[:MENGGANTIKAN]->(:Dokumen)
Notes: Pasal.nomor is a string like "12" or "12A". Konsep.nama is Title Case Indonesian."""

WRITE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|LOAD\s+CSV)\b|\bCALL\s+(dbms|apoc|db\.create)",
    re.IGNORECASE,
)

ANSWER_SYSTEM = (
    "Kamu asisten tanya jawab peraturan akademik ITS. Jawab HANYA berdasarkan konteks yang diberikan. "
    "Sebutkan nomor pasal sumber untuk setiap klaim, contoh: (Pasal 12 ayat (2)). "
    "Jika jawabannya tidak ada di konteks, katakan bahwa informasinya tidak ditemukan di peraturan. "
    "Jangan menambah informasi dari luar konteks."
)


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        if it["id"] not in seen:
            seen.add(it["id"])
            out.append(it)
    return out


def vector_search(question: str, k: int = 5, doc: str | None = None) -> list[dict]:
    vec = embed_texts([question], kind="query")[0]
    with get_driver() as driver, driver.session() as s:
        rows = s.run(Q_VECTOR, vec=vec, k=k, fetch=k * 4, doc=doc).data()
    return [{**r, "sumber": "vector"} for r in rows]


def hybrid_search(
    question: str, k: int = 5, doc: str | None = None, max_ref: int = 3, max_related: int = 2
) -> list[dict]:
    seeds = vector_search(question, k, doc)
    if not seeds:
        return []
    with get_driver() as driver, driver.session() as s:
        rows = s.run(
            Q_EXPAND, ids=[x["id"] for x in seeds], max_ref=max_ref, max_related=max_related
        ).data()
    extra = []
    for r in rows:
        extra += [{**x, "sumber": "rujukan", "dari": r["seed"]} for x in r["rujukan"]]
        extra += [{**x, "sumber": "konsep", "dari": r["seed"]} for x in r["terkait"]]
    return _dedupe(seeds + extra)


def text2cypher(question: str) -> dict:
    prompt = (
        f"Graph schema:\n{GRAPH_SCHEMA}\n\n"
        f"Write ONE read-only Cypher query that answers: {question}\n"
        "Return pasal text (isi) and nomor when relevant. Output only the query, no explanation."
    )
    cypher = llm.chat(prompt).strip()
    cypher = re.sub(r"^```(?:cypher)?\s*|\s*```$", "", cypher, flags=re.IGNORECASE).strip()
    if WRITE_PATTERN.search(cypher):
        return {"cypher": cypher, "rows": [], "error": "Query ditolak: bukan read-only"}
    try:
        with get_driver() as driver, driver.session() as s:
            rows = s.execute_read(lambda tx: tx.run(cypher).data())
        return {"cypher": cypher, "rows": rows[:25], "error": None}
    except Exception as e:
        return {"cypher": cypher, "rows": [], "error": str(e)}


def build_context(items: list[dict], max_chars: int = 12000) -> str:
    parts, total = [], 0
    for it in items:
        block = f"[{it.get('dokumen', '')} Pasal {it['nomor']}]\n{it['isi']}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)


def answer(question: str, mode: str = "hybrid", k: int = 5, doc: str | None = None) -> dict:
    """Returns {answer, items, context, cypher?, error?} so the CLI, API and eval share one path."""
    result: dict = {"mode": mode}
    if mode == "cypher":
        out = text2cypher(question)
        result.update(cypher=out["cypher"], error=out["error"], items=[])
        context = str(out["rows"]) if out["rows"] else ""
    else:
        items = hybrid_search(question, k, doc) if mode == "hybrid" else vector_search(question, k, doc)
        result["items"] = items
        context = build_context(items)

    result["context"] = context
    if not context:
        result["answer"] = "Informasi tidak ditemukan di knowledge graph."
        return result
    result["answer"] = llm.chat(
        f"Konteks:\n{context}\n\nPertanyaan: {question}", system=ANSWER_SYSTEM
    )
    return result
