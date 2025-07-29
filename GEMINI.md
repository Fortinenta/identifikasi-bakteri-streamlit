# Prompt Perbaikan Aplikasi Identifikasi Bakteri

## Masalah Utama yang Perlu Diperbaiki:

### 1. **Format Data BacDive API Response**
**Masalah**: Fungsi `display_bacdive_info()` mengharapkan struktur data yang tidak sesuai dengan format response sebenarnya dari BacDive API.

**Perbaikan yang diperlukan**:
- Tambahkan logging untuk melihat struktur data yang dikembalikan dari BacDive API
- Sesuaikan parsing data dengan format response yang sebenarnya
- Tambahkan penanganan untuk berbagai format response yang mungkin

```python
def display_bacdive_info(bacdive_info):
    st.subheader("Informasi Tambahan dari BacDive")
    
    # Debug: tampilkan struktur data
    st.write("Debug - Raw BacDive data structure:")
    st.json(bacdive_info)
    
    # Perbaiki parsing sesuai struktur sebenarnya
    # Contoh: jika data berbentuk list atau nested dict yang berbeda
```

### 2. **Algoritma Identifikasi Bakteri**
**Masalah**: Algoritma matching terlalu sederhana dan tidak menangani variasi format data dengan baik.

**Perbaikan yang diperlukan**:
- Implementasikan normalisasi data yang lebih robust
- Tambahkan scoring algorithm yang lebih sophisticated
- Tangani missing values dan partial matches
- Implementasikan fuzzy matching untuk nama bakteri

```python
def identifikasi_bakteri_improved(row_data, database):
    # Implementasi algoritma yang lebih canggih
    # - Weighted scoring berdasarkan importance test
    # - Fuzzy string matching
    # - Confidence interval calculation
```

### 3. **Integrasi BacDive API yang Lebih Robust**
**Masalah**: Pencarian di BacDive tidak optimal dan tidak menangani berbagai format nama bakteri.

**Perbaikan yang diperlukan**:
- Implementasikan multiple search strategies (genus only, genus+species, dengan/tanpa subspecies)
- Tambahkan fallback search jika exact match gagal
- Implementasikan caching untuk mengurangi API calls
- Tambahkan error handling yang lebih baik

```python
def search_bacdive_robust(client, bacteria_name):
    # Strategy 1: Full name search
    # Strategy 2: Genus + species only
    # Strategy 3: Genus only
    # Strategy 4: Partial matching
```

### 4. **Penanganan Template dan Upload File**
**Masalah**: Normalisasi data upload tidak konsisten dengan database internal.

**Perbaikan yang diperlukan**:
- Standardisasi format kolom antara template, upload, dan database
- Implementasikan validation untuk uploaded data
- Tambahkan mapping yang lebih comprehensive untuk berbagai format input

### 5. **User Experience Improvements**
**Perbaikan yang diperlukan**:
- Tambahkan progress indicators untuk operasi yang memakan waktu
- Implementasikan session state management yang lebih baik
- Tambahkan export functionality untuk hasil identifikasi
- Implementasikan batch processing dengan progress bar

### 6. **Error Handling dan Logging**
**Perbaikan yang diperlukan**:
- Tambahkan comprehensive error handling untuk semua API calls
- Implementasikan logging untuk debugging
- Tambahkan user-friendly error messages
- Implementasikan retry mechanism untuk failed API calls

### 7. **Database Structure Optimization**
**Perbaikan yang diperlukan**:
- Standarisasi format data dalam database_bakteri.xlsx
- Tambahkan metadata untuk setiap test (importance weight, category)
- Implementasikan data validation untuk database entries

## Prioritas Perbaikan:

### **Priority 1 (Critical)**:
1. Fix BacDive API data parsing
2. Improve bacteria identification algorithm
3. Standardize data formats across all components

### **Priority 2 (Important)**:
1. Implement robust error handling
2. Add progress indicators
3. Improve search strategies

### **Priority 3 (Enhancement)**:
1. Add export functionality
2. Implement caching
3. Add data validation

## Implementasi yang Disarankan:

### Step 1: Debug dan Analisis Data BacDive
```python
# Tambahkan fungsi debug untuk memahami format response BacDive
def debug_bacdive_response(client, bacteria_name):
    count = client.search(taxonomy=bacteria_name)
    if count > 0:
        for i, entry in enumerate(client.retrieve()):
            st.write(f"Entry {i}:")
            st.json(entry)
            if i >= 2:  # Limit untuk debug
                break
```

### Step 2: Refactor Identification Algorithm
```python
def advanced_bacteria_identification(test_results, database, weights=None):
    # Implementasi scoring yang lebih canggih
    # Dengan weighted tests dan confidence calculation
    pass
```

### Step 3: Implement Robust BacDive Integration
```python
def enhanced_bacdive_search(client, bacteria_name):
    # Multi-strategy search dengan fallback
    # Caching mechanism
    # Better error handling
    pass
```

## Testing Strategy:
1. Test dengan berbagai format nama bakteri
2. Test dengan data partial/incomplete
3. Test error scenarios (network issues, invalid data)
4. Performance testing dengan large datasets

## Expected Outcomes:
- Eliminasi hasil kosong dari BacDive searches
- Peningkatan akurasi identifikasi bakteri
- User experience yang lebih smooth
- Error handling yang robust
- Performance yang lebih baik