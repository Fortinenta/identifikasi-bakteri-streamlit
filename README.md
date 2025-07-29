# 🧫 BakteriFinder: Aplikasi Identifikasi Bakteri Otomatis

**BakteriFinder** adalah aplikasi berbasis Streamlit yang dirancang untuk mengidentifikasi jenis bakteri berdasarkan hasil uji laboratorium mikrobiologi, seperti pewarnaan Gram, uji biokimia, dan fermentasi karbohidrat.

---

## 🎯 Tujuan Proyek

Aplikasi ini bertujuan untuk:
- Membantu identifikasi bakteri secara otomatis dan cepat
- Mengurangi kesalahan manusia dalam interpretasi hasil lab
- Mendukung pembelajaran dan penelitian mikrobiologi
- Dapat digunakan di laboratorium, kampus, atau proyek riset

---

## 🧪 Data Input

Aplikasi menerima file dalam format:
- `.csv`
- `.xlsx` (Excel)

### Kolom yang dibutuhkan (contoh):
- Sampel
- Gram
- Katalase
- Oksidase
- Glukosa
- Laktosa
- H2S
- MR
- VP
- Citrate
- Urease
- Indol
- Motilitas
- Dnase
- Esculin
- Nitrate
- dan lainnya sesuai kebutuhan

---

## 🤖 Metode Identifikasi

Aplikasi menggunakan metode **Rule-Based Matching**, yaitu mencocokkan kombinasi hasil uji dengan database referensi bakteri.

Contoh logika identifikasi:

```python
if Gram == "-" and Oksidase == "+" and Katalase == "+" and Motilitas == "-" and Dnase == "+":
    return "Kemungkinan: Aeromonas salmonicida"
```

> Ke depan, sistem ini dapat dikembangkan menggunakan **Machine Learning**.

---

## 🧱 Struktur Proyek

```
identifikasi-bakteri-streamlit/
├── app.py                   # Aplikasi utama Streamlit
├── database_bakteri.xlsx   # Database referensi bakteri
├── contoh_data.csv         # Contoh input data uji lab
└── README.md               # Dokumentasi proyek ini
```

---

## 🖥️ Fitur Aplikasi

| Fitur                           | Deskripsi                                                |
|--------------------------------|-----------------------------------------------------------|
| 📁 Upload File CSV/Excel        | Input data uji lab bakteri                                |
| 📊 Preview Data                 | Menampilkan data yang diupload                            |
| 🔍 Identifikasi Otomatis        | Analisis berdasarkan rule logika                          |
| 🧠 Interpretasi Hasil           | Menjelaskan hasil identifikasi                            |
| ⬇️ Download Hasil               | Unduh hasil identifikasi dalam file baru                  |
| 📚 Database Bakteri Referensi   | Disimpan dalam Excel untuk kemudahan update               |

---

## ⚙️ Teknologi yang Digunakan

- Python
- Streamlit
- Pandas
- OpenPyXL (untuk baca file Excel)
- Anaconda (opsional)

---

## 🚀 Cara Menjalankan Aplikasi

1. Buat virtual environment (opsional):
    ```bash
    conda create -n streamlit-env python=3.10 -y
    conda activate streamlit-env
    ```

2. Install dependensi:
    ```bash
    pip install streamlit pandas openpyxl
    ```

3. Jalankan aplikasi:
    ```bash
    streamlit run app.py
    ```

---

## 🔮 Rencana Pengembangan Selanjutnya

- ✅ Tambah lebih banyak jenis bakteri (Salmonella, E. coli, dll)
- ✅ Tambah pengolahan fermentasi karbohidrat dan uji lanjutan
- ⏳ Integrasi model machine learning
- ⏳ Export hasil ke PDF
- ⏳ Visualisasi data uji

---

## 📌 Manfaat Aplikasi

- Mempercepat proses identifikasi dari hasil uji lab
- Mendukung kegiatan riset dan pendidikan mikrobiologi
- Dapat dioperasikan tanpa perlu setup rumit
- Cocok digunakan untuk skripsi, laboratorium, dan praktikum

---

📬 Untuk saran dan pengembangan lebih lanjut, silakan hubungi pengembang atau kontribusi di repositori ini.