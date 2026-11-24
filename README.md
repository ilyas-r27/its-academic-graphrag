# GraphRAG Peraturan Akademik ITS

Final project RSBP (Rekayasa Sistem Berbasis Pengetahuan). Sistem tanya jawab peraturan akademik ITS berbasis knowledge graph Neo4j, dengan LLM sebagai antarmuka bahasa dan rule engine untuk aturan yang pasti.

## Arsitektur

```
Tahap 1, indexing (sekali di awal)
  PDF peraturan -> parse_pdf (Bab/Pasal/Ayat + rujukan) -> load_graph (Neo4j)
               -> extract_concepts (LLM, direview manual) -> embed (vector index)

Tahap 2, query (tiap pertanyaan)
  Pertanyaan -> retrieval (vector | hybrid | cypher) -> konteks pasal -> LLM -> jawaban + sumber pasal
  Pertanyaan aturan pasti (mis. batas SKS) -> rules/ (Z3)
```

Pemetaan ke materi RSBP:

| Aktivitas KE | Di project ini |
|---|---|
| Knowledge acquisition | Parsing PDF + ekstraksi konsep |
| Knowledge validation | Review manual konsep + `eval/` |
| Knowledge representation | Ontology (`ontology/`) + graph Neo4j (`docs/schema.md`) |
| Inferencing | Graph traversal (`kg/retrieve.py`) + rule Z3 (`rules/`) |
| Explanation and justification | Jawaban menyebut pasal sumber + visual subgraph (frontend) |

## Struktur folder

```
kg/            pipeline Python (parse, load, embed, retrieve, CLI)
kg/cypher/     schema Neo4j (constraint, index)
rules/         rule-based reasoning (Z3)
eval/          pertanyaan uji + script evaluasi
data/raw/      PDF peraturan (sumber)
data/processed JSON hasil parsing + konsep yang sudah direview
ontology/      file Protégé (.owl)
docs/          skema graph dan catatan desain
frontend/      Next.js (belakangan)
```

## Setup

Butuh: Python 3.11+, Docker (untuk Neo4j), API key LLM.

```bash
git clone <url-repo> && cd rsbp-graphrag
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # lalu isi password Neo4j dan API key
docker compose up -d        # Neo4j Browser: http://localhost:7474
```

Unduh PDF peraturan ke `data/raw/`, misalnya:
- `data/raw/PR33-2025.pdf`: Peraturan Rektor No. 33 Tahun 2025 tentang Peraturan Akademik
- `data/raw/PR18-2023.pdf`: Peraturan Rektor No. 18 Tahun 2023 (pembanding)

## Menjalankan pipeline

```bash
# 1. parse PDF -> data/processed/PR33-2025.json (cek hasilnya dengan membuka PDF!)
python -m kg.parse_pdf data/raw/PR33-2025.pdf --doc-id PR33-2025 --tahun 2025 \
    --judul "Peraturan Rektor ITS No. 33 Tahun 2025 tentang Peraturan Akademik"

# 2. muat ke Neo4j
python -m kg.load_graph data/processed/PR33-2025.json

# 3. draft konsep via LLM, REVIEW MANUAL file _konsep.json, lalu muat
python -m kg.extract_concepts data/processed/PR33-2025.json --limit 5
python -m kg.extract_concepts data/processed/PR33-2025.json
python -m kg.load_graph data/processed/PR33-2025.json --konsep data/processed/PR33-2025_konsep.json

# 4. embedding + vector index
python -m kg.embed

# 5. tanya
python -m kg.ask "Berapa lama maksimal cuti akademik?"
python -m kg.ask "..." --mode vector --show-context

# 6. evaluasi
python -m eval.run_eval --no-answer      # retrieval saja, tanpa biaya LLM
python -m eval.run_eval

# rule engine
python -m rules.sks_rules 3.2
```

## Workflow Git

- `main` selalu dalam kondisi bisa jalan. Jangan push langsung ke `main`.
- Satu fitur satu branch: `feat/parser`, `feat/retrieval`, `fix/parser-ayat`, `docs/laporan`.
- Buka Pull Request, partner review, baru merge.
- Commit kecil dan jelas: `feat: split ayat in parse_pdf`, `fix: skip external pasal refs`.
- Selalu `git pull` sebelum mulai kerja.
- `.env` tidak boleh di-commit. File di `data/processed/` boleh di-commit supaya partner tidak perlu menjalankan ulang LLM.
- Hindari mengedit file yang sama di waktu yang sama. Lihat pembagian kerja di bawah.

## Pembagian kerja (usulan)

| | Orang A: Knowledge | Orang B: Retrieval & App |
|---|---|---|
| Fokus | Data, ontology, graph | Retrieval, LLM, evaluasi, web |
| File utama | `kg/parse_pdf.py`, `kg/load_graph.py`, `kg/extract_concepts.py`, `ontology/`, `rules/` | `kg/retrieve.py`, `kg/llm.py`, `kg/ask.py`, `eval/`, `frontend/` |
| Bersama | Membuat 30 sampai 50 pertanyaan uji di `eval/questions.jsonl` | |

## Roadmap

- [ ] **Minggu 1, Knowledge**: parse PDF 2025, cek manual hasilnya, muat ke Neo4j, rancang ontology di Protégé
- [ ] **Minggu 1, Retrieval**: setup `.env`, embedding, mode `vector` dan `hybrid` jalan di CLI
- [ ] **Minggu 2**: ekstraksi + review konsep, mode `cypher`, rule Z3 dengan angka dari pasal asli, mulai tulis pertanyaan uji
- [ ] **Minggu 3**: evaluasi (vector vs hybrid vs cypher), error analysis, versi 2023 + relasi `MENGGANTIKAN`
- [ ] **Minggu 4**: FastAPI + Next.js (chat + visual subgraph), laporan, slide demo

## Kerja dengan Claude Code

`CLAUDE.md` di root berisi konteks project dan otomatis dibaca Claude Code. Contoh perintah awal:

- "Jalankan parse_pdf ke data/raw/PR33-2025.pdf dan bandingkan 5 pasal acak dengan PDF-nya"
- "Tambahkan endpoint FastAPI /ask yang memanggil kg.retrieve.answer"
- "Buat 10 pertanyaan uji dari Bab tentang evaluasi studi, lengkap dengan pasal_acuan"

Kalau skema graph berubah, minta Claude Code ikut memperbarui `docs/schema.md`, `GRAPH_SCHEMA` di `kg/retrieve.py`, dan `CLAUDE.md`.
