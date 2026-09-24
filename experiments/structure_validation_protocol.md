# Protokol validasi struktur dokumen

Tujuan tahap ini adalah memastikan bahwa batas section cukup akurat sebelum
structure-aware chunking dibandingkan dengan baseline pada eksperimen retrieval.
Sampel eksplorasi 20 dokumen dipakai untuk mengembangkan aturan. Hasil pada
sampel ini tidak boleh dilaporkan sebagai estimasi performa final detector karena
aturan akan diperbaiki berdasarkan dokumen yang sama.

## Unit anotasi

Tinjau satu baris untuk setiap pasangan dokumen dan label pada
`experiments/results/exploration_20_structure_review.csv`. Gunakan teks bersih di
`data/processed/exploration_20/pages.jsonl` sebagai sumber anotasi, bukan PDF,
agar acuan sama dengan input detector.

Label yang ditinjau:

- `kepala_putusan`: judul putusan sampai sebelum identitas terdakwa;
- `identitas_terdakwa`: data nama, lahir, alamat, agama, dan pekerjaan;
- `riwayat_penahanan`: penangkapan/penahanan dan pengantar administrasi perkara;
- `fakta`: dakwaan, keterangan saksi/terdakwa, barang bukti, dan fakta hukum;
- `pertimbangan_hukum`: penilaian unsur, kesalahan, pemidanaan, serta keadaan
  memberatkan dan meringankan;
- `amar_putusan`: bagian yang dimulai dengan "MENGADILI" atau padanannya;
- `penutup`: tanggal putusan, majelis hakim, panitera, dan pihak yang hadir.

Definisi `fakta` dan `pertimbangan_hukum` harus diterapkan secara konsisten.
Jika dokumen tidak memberi heading eksplisit, gunakan paragraf transisi semantik
pertama sebagai `gold_heading` dan jelaskan keputusan singkat pada catatan.

## Nilai review_status

- `exact`: label dan awal section tepat;
- `near`: label tepat, tetapi awal bergeser paling jauh satu paragraf;
- `missed`: section ada tetapi tidak terdeteksi;
- `false_positive`: batas terdeteksi bukan awal section tersebut;
- `not_applicable`: section memang tidak ada pada dokumen.

Isi `gold_heading` untuk `near`, `missed`, dan `false_positive`. Jangan mengubah
kolom hasil detector karena kolom tersebut adalah prediksi yang akan dievaluasi.

## Metrik dan kriteria penerimaan

Laporkan exact boundary accuracy, accuracy dengan toleransi satu paragraf,
recall per label, dan jumlah false positive. Konfigurasi boleh dibekukan jika:

1. `amar_putusan` mencapai exact recall 100%;
2. `identitas_terdakwa`, `fakta`, `pertimbangan_hukum`, dan `penutup` masing-masing
   mencapai recall dengan toleransi minimal 90%;
3. tidak ada false positive yang menyebabkan `amar_putusan` atau
   `pertimbangan_hukum` tertukar; dan
4. semua dokumen tetap memiliki coverage karakter 100% tanpa overlap section.

Setelah aturan memenuhi kriteria pada sampel pengembangan, validasi sekali lagi
pada sampel holdout yang belum pernah dipakai untuk menulis pola regex. Baru
setelah itu bekukan konfigurasi chunking dan susun dataset pertanyaan retrieval.
