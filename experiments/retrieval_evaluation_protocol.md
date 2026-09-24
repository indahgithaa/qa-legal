# Protokol evaluasi retrieval

## Tujuan

Evaluasi membandingkan `fixed_size` dan `structure_aware` dengan pertanyaan,
corpus dokumen, model embedding, dan parameter pencarian yang sama. Unit analisis
utama adalah pertanyaan, sehingga selisih skor kedua strategi dapat dihitung
secara berpasangan.

Sampel `exploration_20` dipakai sebagai pilot untuk memperbaiki pipeline dan
pedoman anotasi. Hasil dari sampel ini tidak menjadi estimasi final karena
dokumennya sudah dipakai ketika mengembangkan detector. Evaluasi final harus
memakai dokumen holdout yang belum digunakan untuk menyusun pola atau memilih
parameter.

## Komposisi pilot

Buat 80 pertanyaan dari 20 dokumen, masing-masing empat pertanyaan:

- satu pertanyaan administratif, bergantian antara `identitas_terdakwa` dan
  `riwayat_penahanan`, sehingga setiap kategori memiliki 10 pertanyaan;
- satu pertanyaan `fakta`;
- satu pertanyaan `pertimbangan_hukum`; dan
- satu pertanyaan `amar_putusan`.

Pertanyaan harus dapat dijawab dari satu dokumen, menggunakan bahasa yang wajar,
dan tidak menyalin kalimat bukti secara utuh. Hindari petunjuk yang hanya cocok
dengan kata-kata persis pada dokumen. Setiap pertanyaan mempunyai satu jawaban
rujukan dan satu rentang bukti minimal yang tetap cukup untuk mendukung jawaban.

Template pilot dibuat dengan:

```powershell
python scripts/prepare_retrieval_questions.py
```

## Skema anotasi

Setiap baris memiliki kolom berikut:

| Kolom | Isi |
|---|---|
| `query_id` | ID stabil dan unik. |
| `document_id` | Dokumen yang memuat jawaban. |
| `target_section_label` | Strata pertanyaan yang direncanakan. |
| `question` | Pertanyaan retrieval. |
| `reference_answer` | Jawaban singkat yang didukung dokumen. |
| `evidence_start_position` | Offset awal bukti pada teks bersih dokumen. |
| `evidence_end_position` | Offset akhir eksklusif bukti. |
| `difficulty` | `easy`, `medium`, atau `hard`. |
| `review_status` | `draft`, `approved`, atau `rejected`. |
| `notes` | Catatan ambiguitas atau keputusan reviewer. |

Offset bukti selalu mengacu pada penggabungan `clean_text` halaman menurut
`page_number`, sama seperti input detector dan chunker. Rentang harus diverifikasi
dengan memastikan potongan teks pada offset tersebut sama dengan bukti yang
dipilih.

## Relevansi chunk

Ground truth disimpan sebagai rentang bukti dokumen, bukan sebagai ID chunk.
Setelah kedua strategi selesai menghasilkan chunk, kandidat relevansi diturunkan
secara terpisah untuk setiap strategi:

- grade 2: chunk memuat seluruh rentang bukti;
- grade 1: chunk memuat sebagian bukti dan masih cukup untuk menjawab;
- grade 0: chunk tidak cukup untuk menjawab.

Kasus grade 1 harus diperiksa manual karena overlap karakter saja belum menjamin
bahwa konteks jawaban tersedia. Cara ini mencegah skema anotasi menguntungkan
salah satu strategi dan memungkinkan nDCG memakai tingkat relevansi.

## Prosedur eksperimen

1. Selesaikan dan review pertanyaan tanpa melihat hasil retrieval.
2. Bekukan preprocessing, detector, ukuran chunk, overlap, model embedding, dan
   parameter retrieval sebelum menjalankan holdout.
3. Bangun dua index dari corpus yang sama, satu index per strategi.
4. Jalankan setiap pertanyaan pada kedua index dengan nilai `k` yang sama.
5. Laporkan Recall@1/3/5/10, MRR@1/3/5/10, dan nDCG@1/3/5/10 secara keseluruhan
   serta per `target_section_label`.
6. Hitung selisih skor per pertanyaan antara SAC dan fixed-size. Laporkan interval
   kepercayaan bootstrap berpasangan untuk selisih rata-rata pada evaluasi final.
7. Tinjau contoh kemenangan dan kegagalan kedua strategi, khususnya bukti yang
   berada dekat batas section atau batas chunk.

Jika konfigurasi diubah setelah melihat hasil pilot, catat perubahan dan
alasannya. Konfigurasi tersebut kemudian dibekukan sebelum evaluasi holdout.

## Kriteria kesiapan

Eksperimen embedding dimulai setelah review batas struktur selesai dan seluruh
pertanyaan pilot berstatus `approved`. Klaim utama baru dibuat dari holdout yang
terpisah pada tingkat dokumen. Pertanyaan dari satu dokumen tidak boleh dibagi ke
set pengembangan dan holdout.
