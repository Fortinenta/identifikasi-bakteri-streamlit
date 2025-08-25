🔄 Alur Lengkap

Ambil Genus dari file input

Di process_sample() (app.py), pertama diambil kolom Genus dari row.to_dict().

Kalau kosong → dilewati (tidak diproses).

genus = user_input.get("Genus")
if not genus or pd.isna(genus):
    return []


Fetch profil BacDive berdasarkan Genus

Fungsi fetch_and_cache_profiles_by_taxonomy(client, genus, status_placeholder) dipanggil.

Jika cache ada dan masih valid → pakai cache.

Kalau tidak, akan:

client.search(taxonomy=genus) → ambil daftar strain ID untuk genus itu.

client.retrieve(id) → ambil detail strain satu per satu.

Hasilnya diolah jadi dict profiles dengan struktur:

{
  "12345": { "Nama Bakteri": "...", "Gram_stain": "positive", "Motility": "negative", ... },
  "67890": { ... }
}


Perbandingan parameter

Untuk setiap profil BacDive:

calculate_weighted_similarity(user_input, bacdive_profile) dipanggil.

Di sini:

Semua kolom di file input distandarisasi (normalize_columns() + normalisasi nilai + / Positif → positive).

Dibandingkan dengan nilai profil BacDive.

Jika cocok → skor bertambah sesuai WEIGHTS.

Jika tidak cocok → dicatat sebagai ❌.

Hasilnya berupa skor % kemiripan + tabel detail cocok/tidak cocok.

Hanya hasil dengan skor > 0 yang disimpan

if score > 0:
    identification_results.append({...})


Urutkan hasil berdasarkan persentase

Paling tinggi jadi Rank 1 (identifikasi utama).

Ditampilkan ke user.

📌 Jadi singkatnya:

Langkah 1: Program cek dulu kolom Genus.

Langkah 2: Ambil semua profil BacDive untuk genus itu.

Langkah 3: Bandingkan parameter input (Gram, Motilitas, dsb) dengan tiap profil.

Langkah 4: Hitung skor → simpan kalau > 0.

Langkah 5: Urutkan hasil, tampilkan kandidat teratas.