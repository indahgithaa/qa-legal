# Protokol validasi struktur dokumen

Tujuan tahap ini adalah memeriksa kepatuhan implementasi terhadap SAC-H+ dan
menganalisis kesalahan batas section. Kepatuhan metode diperiksa otomatis dan
menjadi gerbang pipeline; review manusia dipakai sebagai audit diagnostik.
Sampel eksplorasi 20 dokumen dipakai untuk mengembangkan aturan. Hasil pada
sampel ini tidak boleh dilaporkan sebagai estimasi performa final detector karena
aturan telah diperbaiki berdasarkan dokumen yang sama.

Jalankan pemeriksaan kepatuhan utama dengan:

```powershell
python scripts/validate_sac_compliance.py
```

Pemeriksaan ini mengikuti Sonowal dan Sadhu (2025): tiga strata retoris, cascade
top-down, conclusion pada jendela 20% akhir, trigger berpresisi tinggi, chunk
yang tidak melintasi strata, dan overlap konteks di dalam strata. Lulusnya
pemeriksaan membuktikan kesesuaian implementasi dengan metode, bukan akurasi
semantik setiap batas pada yurisdiksi Indonesia.

## Unit anotasi

Tinjau satu baris untuk setiap pasangan dokumen dan label pada
`experiments/results/exploration_20_structure_review.csv`. Gunakan teks bersih di
`data/processed/exploration_20/pages.jsonl` sebagai sumber anotasi, bukan PDF,
agar acuan sama dengan input detector.

Jalankan `python scripts/prepare_structure_review_context.py` untuk membuat
salinan baca yang menandai posisi setiap batas beserta teks sebelum dan
sesudahnya. Tetap simpan keputusan review pada file CSV.

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

- Isi `gold_present` dengan `yes` jika section memang ada dan `no` jika tidak.
- `exact`: label dan awal section tepat;
- `near`: label tepat, tetapi awal bergeser paling jauh satu paragraf;
- `missed`: section ada tetapi tidak terdeteksi;
- `false_positive`: batas terdeteksi bukan awal section tersebut;
- `not_applicable`: section memang tidak ada pada dokumen.

Isi `gold_heading` untuk `near`, `missed`, dan `false_positive`. Jangan mengubah
kolom hasil detector karena kolom tersebut adalah prediksi yang akan dievaluasi.
Kombinasi yang konsisten adalah `gold_present=yes` untuk `exact`, `near`, dan
`missed`; serta `gold_present=no` untuk `not_applicable`. `false_positive` dapat
memiliki `gold_present=yes` jika section sebenarnya ada di lokasi lain.
Status `exact`, `near`, dan `false_positive` dipakai pada baris `detected=yes`;
status `missed` dan `not_applicable` dipakai pada baris `detected=no`.

## Metrik audit manusia

Laporkan exact boundary accuracy, accuracy dengan toleransi satu paragraf,
recall per label, dan jumlah false positive. Target diagnostik yang digunakan:

1. `amar_putusan` mencapai exact recall 100%;
2. `identitas_terdakwa`, `fakta`, `pertimbangan_hukum`, dan `penutup` masing-masing
   mencapai recall dengan toleransi minimal 90%;
3. tidak ada false positive yang menyebabkan `amar_putusan` atau
   `pertimbangan_hukum` tertukar; dan
4. semua dokumen tetap memiliki coverage karakter 100% tanpa overlap section.

Review lengkap 140 baris tidak menjadi prasyarat pembangunan index. Sebelum
publikasi, audit batas makro `fakta`, `pertimbangan_hukum`, dan `amar_putusan`
pada holdout yang belum pernah dipakai untuk menulis pola regex. Klaim utama
tentang manfaat chunking ditentukan oleh evaluasi retrieval berpasangan pada
holdout tersebut.
