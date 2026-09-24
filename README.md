# Structure-Aware Chunking untuk RAG Dokumen Putusan Pengadilan

Repository ini berisi implementasi penelitian tentang pengaruh strategi
*chunking* terhadap kinerja retrieval pada dokumen putusan pengadilan Indonesia.
Fokus utamanya adalah membandingkan dua pendekatan:

1. **Fixed-size chunking** sebagai baseline.
2. **Structure-aware chunking** yang memanfaatkan bagian-bagian dalam putusan,
   seperti identitas terdakwa, fakta, pertimbangan hukum, dan amar putusan.

Penelitian ini dilatarbelakangi oleh bentuk putusan pengadilan yang panjang dan
memiliki susunan tertentu. Pemotongan teks hanya berdasarkan ukuran berisiko
memisahkan informasi yang seharusnya dibaca sebagai satu bagian. Repository ini
disiapkan untuk menguji apakah penggunaan struktur dokumen dapat menghasilkan
unit retrieval yang lebih relevan.

## Status pengembangan

Pipeline yang tersedia saat ini mencakup:

```text
PDF
  -> ekstraksi teks per halaman
  -> pembersihan teks
  -> deteksi struktur dokumen
  -> fixed-size / structure-aware chunking
  -> audit struktur dan distribusi chunk
  -> scoring review struktur
  -> template pertanyaan dan metrik evaluasi retrieval
  -> JSONL
```

Metrik Recall, MRR, dan nDCG sudah tersedia. Embedding, vector database,
retrieval, dan generation belum diimplementasikan. File untuk komponen tersebut
masih berupa placeholder agar batas antarbagian sistem sudah jelas sejak awal.
Audit eksplorasi dan lembar anotasi tersedia untuk memvalidasi keluaran chunking
sebelum index dibangun.

## Struktur repository

```text
configs/          Konfigurasi pipeline dan strategi chunking
data/             Data mentah dan artefak hasil setiap tahap
experiments/      Catatan konfigurasi dan hasil eksperimen
notebooks/        Eksplorasi data dan analisis hasil
scripts/          CLI untuk menjalankan pipeline secara berurutan
src/              Implementasi utama
tests/            Unit test
vector_db/        Penyimpanan index lokal pada tahap berikutnya
```

Kode utama dipisahkan berdasarkan tanggung jawab:

- `src/preprocessing/`: ekstraksi PDF, pembersihan teks, dan deteksi section.
- `src/chunking/`: interface chunker dan dua strategi yang dibandingkan.
- `src/utils/`: pembacaan konfigurasi, JSONL, dan logging.
- `src/cli.py`: orkestrasi command-line tanpa menyimpan logic pemrosesan inti.

## Instalasi

Gunakan Python 3.10 atau versi yang lebih baru.

```powershell
git clone https://github.com/indahgithaa/qa-legal.git
cd qa-legal
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Untuk Linux atau macOS, aktivasi virtual environment dengan:

```bash
source .venv/bin/activate
```

Project dipasang dalam mode editable melalui `requirements.txt`. Script dapat
dijalankan dari root repository tanpa mengubah `PYTHONPATH` atau `sys.path`.

## Menyiapkan data

Letakkan PDF putusan di:

```text
data/raw/court_decisions/
```

Subfolder diperbolehkan. Nama file relatif ikut disimpan sebagai provenance,
sedangkan `document_id` dibuat secara deterministik dari path file. Dataset PDF
dan seluruh artefak berukuran besar diabaikan oleh Git.

### Sampel eksplorasi 20 dokumen

Eksplorasi awal dapat menggunakan sampel purposive 20 dokumen yang tercatat di
`experiments/exploration_20_manifest.json`. Salin file pada manifest ke
`data/raw/exploration_20/`, lalu jalankan:

```powershell
python scripts/01_extract_pdf.py --config configs/exploration.yaml
python scripts/02_preprocess.py --config configs/exploration.yaml
python scripts/03_chunk.py --config configs/exploration_baseline.yaml
python scripts/03_chunk.py --config configs/exploration_structure_aware.yaml
```

Output disimpan pada subfolder `exploration_20` di setiap tahap. Sampel ini
memaksimalkan variasi pengadilan dan tahun untuk eksplorasi format; sampel tidak
dimaksudkan untuk mengestimasi distribusi statistik seluruh corpus.

Audit hasil eksplorasi dan buat lembar review manual dengan:

```powershell
python scripts/audit_exploration.py
```

Perintah ini memeriksa coverage karakter dan offset, merangkum cakupan label,
membandingkan distribusi kedua strategi, serta menulis laporan dan template
review ke `experiments/results/`. Petunjuk anotasi dan kriteria penerimaan berada
di `experiments/structure_validation_protocol.md`.

Setelah lembar review diisi, hitung metrik batas struktur dengan:

```powershell
python scripts/score_structure_review.py
```

Siapkan 80 slot pertanyaan pilot yang terstratifikasi dengan:

```powershell
python scripts/prepare_retrieval_questions.py
```

Skema anotasi bukti, aturan relevansi, pemisahan pilot dan holdout, serta metrik
eksperimen dijelaskan di `experiments/retrieval_evaluation_protocol.md`.

## Menjalankan pipeline

### 1. Ekstraksi PDF

```powershell
python scripts/01_extract_pdf.py --config configs/default.yaml
```

Ekstraksi menggunakan PyMuPDF dan menghasilkan satu record untuk setiap
halaman di `data/extracted/pages.jsonl`. Secara default, baris teks nonhorizontal
dikeluarkan untuk mencegah fragmen watermark diagonal tersisip di tengah isi
putusan.

### 2. Pembersihan teks dan deteksi struktur

```powershell
python scripts/02_preprocess.py --config configs/default.yaml
```

Tahap ini menghasilkan:

- `data/processed/pages.jsonl`, berisi teks mentah dan teks bersih per halaman;
- `data/processed/sections.jsonl`, berisi section yang terdeteksi beserta posisi
  karakternya dalam dokumen.

Pembersihan teks memperbaiki artefak encoding yang umum dan menghapus baris
boilerplate Mahkamah Agung yang dikenali secara eksplisit, seperti header
direktori, URL, nomor halaman, disclaimer, dan informasi kontak. Kalimat hukum
yang hanya menyebut Mahkamah Agung tidak dihapus.

### 3. Membuat baseline chunks

```powershell
python scripts/03_chunk.py --config configs/baseline.yaml
```

Output disimpan di `data/chunks/fixed_size/chunks.jsonl`.

### 4. Membuat structure-aware chunks

```powershell
python scripts/03_chunk.py --config configs/structure_aware.yaml
```

Output disimpan di `data/chunks/structure_aware/chunks.jsonl`.

Setiap script menyediakan opsi override, misalnya `--input`, `--output`, atau
`--input-dir`. Jalankan script dengan `--help` untuk melihat opsi lengkap.

## Format data

Hasil ekstraksi disimpan per halaman. Contoh ringkas:

```json
{
  "document_id": "putusan-contoh-a1b2c3d4",
  "filename": "pidana/putusan-contoh.pdf",
  "page_number": 1,
  "raw_text": "..."
}
```

Hasil deteksi struktur menyimpan label dan rentang karakter:

```json
{
  "document_id": "putusan-contoh-a1b2c3d4",
  "section_label": "pertimbangan_hukum",
  "section_heading": "MENIMBANG",
  "start_position": 4210,
  "end_position": 8932,
  "section_text": "..."
}
```

Teks sebelum heading pertama atau teks yang tidak dapat dikenali tidak dibuang.
Bagian tersebut diberi label `unknown` sehingga coverage dokumen tetap utuh.

## Strategi chunking

### Fixed-size

Dokumen dipotong menjadi window berdasarkan jumlah kata. Window berikutnya
menggunakan overlap yang tetap. Strategi ini tidak mempertimbangkan pergantian
bagian dokumen dan digunakan sebagai baseline.

### Structure-aware

Implementasi mengadaptasi *Structure-Aware Chunking* (SAC-H+) dari Sonowal dan
Sadhu (2025) ke putusan pidana Indonesia. Detector bekerja secara top-down:

1. menjangkar `amar_putusan` pada 20% terakhir dokumen;
2. mencari transisi berpresisi tinggi dari fakta ke analisis hukum sebelum amar;
3. memberi label narasi sebelumnya sebagai `fakta`; dan
4. mempertahankan kepala putusan, identitas, penahanan, serta penutup sebagai
   sub-struktur yang lebih rinci.

Section yang terlalu panjang dipotong pada batas kalimat. Dua kalimat terakhir
dari chunk sebelumnya dibawa ke chunk berikutnya untuk menjaga konteks lokal,
sementara kalimat yang melebihi batas ukuran memakai word-window sebagai
fallback. Satu chunk tidak pernah melintasi batas section.

Rujukan metode: Himadri Sonowal dan Saisab Sadhu, 2025,
[Structure-Aware Chunking for Abstractive Summarization of Long Legal
Documents](https://aclanthology.org/2025.justnlp-main.19/).

Kedua strategi mengimplementasikan interface `BaseChunker`. Parameter yang
berpengaruh pada eksperimen berada di file YAML agar perbandingan dapat dilakukan
dengan konfigurasi yang konsisten.

## Menjalankan test

```powershell
python -m pytest
```

Test yang tersedia mencakup ekstraksi PDF sederhana, penyaringan watermark,
normalisasi dan pembersihan boilerplate, fallback deteksi struktur, preservasi
isi dokumen, overlap fixed-size, batas section, dan round-trip JSONL.
Metrik review struktur serta Recall, MRR, dan nDCG juga diuji tanpa dependensi
evaluasi tambahan.

## Konfigurasi

`configs/default.yaml` menyimpan path dan parameter umum. Konfigurasi eksperimen
di `configs/baseline.yaml` dan `configs/structure_aware.yaml` mewarisi nilai
tersebut lalu hanya mengganti strategi serta lokasi output yang relevan.

Penyaringan noise PDF dapat dimatikan secara terpisah untuk eksperimen ablasi:

```yaml
extraction:
  exclude_rotated_text: true

preprocessing:
  repair_mojibake: true
  remove_court_boilerplate: true

structure_detection:
  conclusion_search_fraction: 0.20
```

Parameter chunking awal:

```yaml
chunking:
  max_words: 300
  overlap_words: 50
  overlap_sentences: 2  # khusus structure-aware; word overlap menjadi fallback
```

Nilai ini masih merupakan konfigurasi awal, bukan hasil tuning.

## Batasan saat ini

Deteksi struktur masih menggunakan pola heading berbasis regular expression.
Format putusan dapat berbeda antar-pengadilan, jenis perkara, dan periode, serta
hasil ekstraksi PDF dapat mengandung noise atau berasal dari OCR. Karena itu,
detector perlu divalidasi pada sampel data nyata sebelum dipakai dalam eksperimen
retrieval.

Tahap berikutnya adalah menyelesaikan review manual batas section dan pertanyaan
pilot, lalu membekukan konfigurasi chunking sebelum membangun index embedding.
Evaluasi final tetap memerlukan sampel holdout pada tingkat dokumen.
