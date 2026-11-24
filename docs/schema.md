# Skema Knowledge Graph

## Node

| Label | Properti | Contoh id |
|---|---|---|
| `Dokumen` | id, judul, tahun, file | `PR33-2025` |
| `Bab` | id, nomor, judul, dokumen | `PR33-2025:BAB-III` |
| `Pasal` | id, nomor, isi, dokumen, bab, bagian, bagian_judul, embedding | `PR33-2025:P12` |
| `Ayat` | id, nomor, isi | `PR33-2025:P12:A2` |
| `Konsep` | nama | `Cuti Akademik` |

## Relasi

| Relasi | Dari | Ke | Sumber | Tipe relasi (materi semantic network) |
|---|---|---|---|---|
| `BAGIAN_DARI` | Ayat / Pasal / Bab | Pasal / Bab / Dokumen | parser | Part-whole (transitive) |
| `MERUJUK_KE` | Pasal | Pasal | regex "Pasal N" di teks | Associative, bisa diperlakukan transitive saat traversal |
| `MENGATUR` | Pasal | Konsep | LLM + review manual | Functional |
| `MENGGANTIKAN` | Dokumen | Dokumen | manual (`--menggantikan`) | Temporal |

## Index

- Constraint unik pada id tiap label dan `Konsep.nama`
- Full-text: `konsep_fulltext` (Konsep.nama), `pasal_fulltext` (Pasal.isi)
- Vector: `pasal_embedding` (Pasal.embedding, cosine), dibuat oleh `kg.embed`

## Rencana pengembangan

- `(:Konsep)-[:IS_A]->(:Konsep)` untuk hierarki konsep (inheritance), mengikuti ontology di `ontology/`
- Relasi antar versi pasal (`(:Pasal)-[:MENGUBAH]->(:Pasal)`) untuk fitur "apa yang berubah dari 2023 ke 2025"
