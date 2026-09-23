# Court Decision RAG: Structure-Aware Chunking

Fondasi penelitian skripsi untuk membandingkan **fixed-size chunking** dan
**structure-aware chunking** pada question answering dokumen putusan pengadilan
Indonesia. Milestone pertama repository ini sengaja dibatasi pada pipeline:

```text
PDF -> extraction -> cleaning -> structure detection -> chunking
```

Komponen embedding, vector database, retrieval, generation, dan evaluasi akan
ditambahkan pada milestone berikutnya agar setiap tahap tetap transparan dan
mudah diuji.

## Desain data

Setiap tahap menulis artefak baru dan tidak menimpa artefak tahap sebelumnya:

- `data/extracted/pages.jsonl`: satu record per halaman, berisi teks mentah.
- `data/processed/pages.jsonl`: record halaman yang telah ditambah `clean_text`.
- `data/processed/sections.jsonl`: section hasil deteksi pada teks dokumen.
- `data/chunks/fixed_size/chunks.jsonl`: chunk baseline.
- `data/chunks/structure_aware/chunks.jsonl`: chunk berbasis section.

Posisi karakter pada section dan chunk mengacu pada gabungan `clean_text` per
dokumen, dengan dua newline sebagai pemisah halaman. Semua identifier dibuat
deterministik agar eksperimen dapat direproduksi.

## Struktur repository

```text
configs/          konfigurasi umum dan varian eksperimen
data/             artefak data per tahap (dataset besar diabaikan Git)
experiments/      catatan dan hasil eksperimen
notebooks/        eksplorasi data dan analisis hasil, bukan logic pipeline
scripts/          entry point CLI berurutan
src/              implementasi modular pipeline
tests/            unit test
vector_db/        index lokal per metode (diabaikan Git)
```

## Instalasi

Python 3.10 atau lebih baru direkomendasikan.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` memasang project dalam mode editable. Karena itu script dapat
dijalankan dari root repository tanpa mengubah `sys.path` atau `PYTHONPATH`.

## Menjalankan pipeline awal

1. Letakkan PDF di `data/raw/court_decisions/`.
2. Jalankan tahap secara berurutan:

```powershell
python scripts/01_extract_pdf.py --config configs/default.yaml
python scripts/02_preprocess.py --config configs/default.yaml
python scripts/03_chunk.py --config configs/baseline.yaml
python scripts/03_chunk.py --config configs/structure_aware.yaml
```

Gunakan `--help` pada setiap script untuk melihat opsi override. Log ringkas
menampilkan jumlah dokumen, halaman, section, atau chunk yang diproses.

Untuk menjalankan test:

```powershell
python -m pytest
```

## Perbandingan metode chunking

`FixedSizeChunker` menggabungkan teks bersih seluruh halaman dokumen, lalu
membuat window berdasarkan jumlah kata dengan overlap tetap. Metode ini tidak
mengetahui batas semantik dokumen dan menjadi baseline.

`StructureAwareChunker` menerima hasil `StructureDetector`, menjaga chunk tetap
berada di dalam section yang terdeteksi, kemudian hanya membagi section yang
lebih panjang daripada batas konfigurasi. Teks yang tidak dapat dikenali diberi
label `unknown`, bukan dibuang. Kedua metode memakai interface `BaseChunker` dan
parameter ukuran/overlap yang sebanding.

Deteksi struktur saat ini berbasis pola heading yang eksplisit dan merupakan
skeleton yang fungsional. Pengembangan berikutnya perlu mengukur coverage pola
pada sampel putusan nyata, memperluas variasi heading, serta menambahkan golden
dataset anotasi section sebelum masuk ke embedding dan retrieval.

