# Ontology (Protégé)

Simpan file ontology di sini, misalnya `peraturan-akademik.owl`.

Yang perlu dibuat (mengikuti 9 langkah ontology engineering):

1. Scope: peraturan akademik program sarjana ITS
2. Class: Dokumen, Bab, Pasal, Ayat, Konsep, lalu subclass Konsep (mis. StatusMahasiswa > CutiAkademik, Penilaian > IndeksPrestasi)
3. Object property: bagianDari (transitive), merujukKe, mengatur, menggantikan, beserta domain dan range
4. Data property: nomor, isi, judul, tahun
5. Restriction, contoh: `Pasal ⊑ ∃bagianDari.Bab`, `Ayat ⊑ ∃bagianDari.Pasal`
6. Disjoint: Dokumen, Bab, Pasal, Ayat, Konsep saling disjoint
7. Individuals: beberapa pasal contoh untuk menguji reasoner
8. Jalankan reasoner (HermiT) dan pastikan ontology konsisten
9. Skema Neo4j di `docs/schema.md` harus sesuai dengan ontology ini
