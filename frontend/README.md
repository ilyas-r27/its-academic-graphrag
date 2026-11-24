# Frontend (dikerjakan belakangan)

Rencana: Next.js memanggil backend FastAPI (`POST /ask` yang memakai `kg.retrieve.answer`).

Fitur:
- Chat tanya jawab dengan pilihan mode (vector / hybrid / cypher)
- Jawaban + daftar pasal sumber yang bisa diklik untuk melihat isinya
- Visual subgraph pasal yang dipakai (react-force-graph atau neovis.js), untuk aspek explanation and justification

Inisialisasi nanti di branch `feat/frontend`: pindahkan README ini ke `docs/frontend.md`, hapus folder ini, lalu jalankan `npx create-next-app@latest frontend` dari root repo.
