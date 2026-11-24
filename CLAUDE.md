# CLAUDE.md

Context for Claude Code. Read this before changing anything.

## Project

Final project for RSBP (Knowledge-Based System Engineering) at ITS. A question answering system over ITS academic regulations (Peraturan Akademik) using a Neo4j knowledge graph (GraphRAG), plus a Z3 rule engine for deterministic rules. Two students work on it through GitHub.

The grading focus is knowledge engineering: knowledge acquisition, validation, representation (ontology + graph), inferencing, and explanation. The LLM is a language interface, never the source of truth.

## Commands

All Python scripts run as modules from the repo root:

```bash
docker compose up -d                                   # Neo4j on :7474 / :7687
python -m kg.parse_pdf data/raw/X.pdf --doc-id X        # -> data/processed/X.json
python -m kg.load_graph data/processed/X.json [--konsep ...] [--menggantikan OLD_ID]
python -m kg.extract_concepts data/processed/X.json [--limit N]
python -m kg.embed [--all]
python -m kg.ask "question" [--mode hybrid|vector|cypher] [--show-context]
python -m eval.run_eval [--modes ...] [--no-answer]
python -m rules.sks_rules 3.2
```

## Layout

- `kg/config.py`: all settings from `.env`. Do not read env vars anywhere else.
- `kg/llm.py`: the ONLY place that calls the LLM (OpenAI-compatible client). Use `chat` / `chat_json`.
- `kg/embeddings.py`: the ONLY place that computes embeddings.
- `kg/retrieve.py`: retrieval modes and `answer()`. The CLI, eval and future API must all go through `answer()`.
- `kg/cypher/schema.cypher`: constraints and indexes, applied by `load_graph`.
- `docs/schema.md`: human-readable graph schema.

## Graph schema

```
(:Dokumen {id, judul, tahun, file})
(:Bab {id, nomor, judul, dokumen})-[:BAGIAN_DARI]->(:Dokumen)
(:Pasal {id, nomor, isi, dokumen, bab, bagian, bagian_judul, embedding})-[:BAGIAN_DARI]->(:Bab)
(:Ayat {id, nomor, isi})-[:BAGIAN_DARI]->(:Pasal)
(:Pasal)-[:MERUJUK_KE]->(:Pasal)
(:Pasal)-[:MENGATUR]->(:Konsep {nama})
(:Dokumen)-[:MENGGANTIKAN]->(:Dokumen)
```

IDs: `PR33-2025:P12`, `PR33-2025:P12:A2`, `PR33-2025:BAB-III`.

If the schema changes, update all three: `docs/schema.md`, `GRAPH_SCHEMA` in `kg/retrieve.py`, and this file.

## Rules

- Never commit `.env` or API keys.
- Graph writes use `MERGE` so loaders are idempotent.
- Text2Cypher output must stay read-only (`WRITE_PATTERN` guard + `execute_read`).
- Answers must cite pasal numbers and must not use knowledge outside the retrieved context.
- LLM-extracted concepts are drafts. They are reviewed by hand before loading.
- Numbers in `rules/` must come from a cited pasal of the actual regulation, not from memory.
- Code and identifiers in English, user-facing text and docs in Bahasa Indonesia.
- Keep functions small; no new dependencies without a reason in the PR description.
