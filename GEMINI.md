# Perbaikan Aplikasi BacDive Streamlit

## Masalah Yang Ditemukan:

### 1. **Struktur JSON Response BacDive Tidak Sesuai dengan Parser**
Berdasarkan file JSON Anda (`bacdive_590.json`), struktur response BacDive berbeda dengan yang diharapkan kode:

**Struktur Aktual:**
```json
{
    "results": {
        "590": {
            "General": {...},
            "Name and taxonomic classification": {...},
            "Morphology": {},
            "Culture and growth conditions": {...},
            "Physiology and metabolism": {...}
        }
    }
}
```

**Yang Diharapkan Kode:**
```json
{
    "general": {
        "taxonomy": {...}
    }
}
```

### 2. **Mapping Path JSON Tidak Sesuai**
Kode mencari data di path yang tidak ada dalam response aktual BacDive.

## Solusi Perbaikan:

### **File: `bacdive_mapper.py`**

#### A. Perbaiki Fungsi `extract_bacdive_data()`:

```python
def extract_bacdive_data(strain_json, param_keys):
    profile = {}
    
    # Perbaikan: Sesuaikan dengan struktur JSON BacDive yang sebenarnya
    try:
        # BacDive menggunakan "Name and taxonomic classification" bukan "general.taxonomy"
        if "Name and taxonomic classification" in strain_json:
            taxonomy = strain_json["Name and taxonomic classification"]
            genus = taxonomy.get("genus", "Unknown")
            species = taxonomy.get("species", "sp.")
            strain_designation = taxonomy.get("strain designation", "")
            
            if strain_designation:
                profile['Nama Bakteri'] = f"{genus} {species} {strain_designation}".strip()
            else:
                profile['Nama Bakteri'] = f"{genus} {species}".strip()
        else:
            profile['Nama Bakteri'] = "Unknown Species"
    except (KeyError, TypeError) as e:
        print(f"Error extracting taxonomy: {e}")
        profile['Nama Bakteri'] = "Unknown Species"

    for param in param_keys:
        profile[param] = extract_parameter_value(strain_json, param)
    
    return profile
```

#### B. Perbaiki `PARAM_TO_BACDIVE_KEY` Mapping:

```python
PARAM_TO_BACDIVE_KEY = {
    # Sesuaikan dengan struktur BacDive yang sebenarnya
    'Gram_stain': [
        ["Morphology", "cell shape"], 
        ["Name and taxonomic classification", "phylum"]  # Bacillota = Gram positive
    ],
    'Motility': [["Morphology", "motility"]],
    'Catalase': [
        ["Physiology and metabolism", "enzymes", "catalase"], 
        ["Physiology and metabolism", "catalase"]
    ],
    'Oxidase': [
        ["Physiology and metabolism", "enzymes", "oxidase"], 
        ["Physiology and metabolism", "oxidase"]
    ],
    'Temperature_range': [
        ["Culture and growth conditions", "culture temp"],
        ["Culture and growth conditions", "temperature"]
    ],
    # Tambahkan mapping lainnya sesuai struktur BacDive
    'Glucose': [
        ["Physiology and metabolism", "metabolite utilization", "glucose"],
        ["Physiology and metabolism", "carbon source utilization", "glucose"]
    ],
    # ... mapping lainnya
}
```

#### C. Perbaiki Fungsi `extract_parameter_value()`:

```python
def extract_parameter_value(strain_json, param):
    paths = PARAM_TO_BACDIVE_KEY.get(param, [])
    
    # Khusus untuk Gram stain, deteksi dari phylum
    if param == 'Gram_stain':
        try:
            phylum = strain_json.get("Name and taxonomic classification", {}).get("phylum", "")
            if phylum.lower() in ['firmicutes', 'bacillota']:
                return 'positive'
            elif phylum.lower() in ['proteobacteria']:
                return 'negative'
        except:
            pass
    
    # Khusus untuk temperature dari culture conditions
    if param == 'Temperature_range':
        try:
            culture_temp = strain_json.get("Culture and growth conditions", {}).get("culture temp", {})
            if isinstance(culture_temp, dict):
                temp = culture_temp.get("temperature")
                if temp:
                    return temp
        except:
            pass
    
    # Coba semua path yang mungkin
    for path in paths:
        current = strain_json
        try:
            for key in path:
                current = current[key]
            
            if current and current not in (None, "", [], {}):
                # Jika dict, ambil nilai yang relevan
                if isinstance(current, dict):
                    return current.get('growth', current.get('result', current.get('activity', str(current))))
                return current
        except (KeyError, TypeError):
            continue
    
    return 'N/A' if param not in {'pH_range', 'Temperature_range', 'NaCl_tolerance'} else None
```

### **File: `app.py`**

#### D. Tambahkan Debug Logging:

Tambahkan setelah line yang mengambil response JSON:

```python
def fetch_and_cache_profiles_by_taxonomy(session, genus, status_placeholder, log_container):
    # ... kode existing ...
    
    for i, bid in enumerate(strain_ids, start=1):
        status_placeholder.text(f"☁️ Mengambil & memproses profil {i}/{total_ids} (ID: {bid})…")
        try:
            r = session.get(f"https://api.bacdive.dsmz.de/fetch/{bid}")
            r.raise_for_status()
            raw = r.json()
            
            # DEBUG: Log struktur JSON untuk debugging
            if i == 1:
                log_container.info(f"Sample JSON structure keys: {list(raw.keys())}")
                if 'Name and taxonomic classification' in raw:
                    log_container.info(f"Taxonomy keys: {list(raw['Name and taxonomic classification'].keys())}")
                log_container.json(raw)
            
            clean = extract_bacdive_data(raw, param_keys)
            log_container.info(f"Extracted profile for ID {bid}: {clean.get('Nama Bakteri', 'Unknown')}")
            
            if clean.get("Nama Bakteri", "N/A") != "Unknown Species":
                profiles[str(bid)] = clean
        except Exception as e:
            log_container.error(f"Error processing ID {bid}: {str(e)}")
        
        time.sleep(0.35)
```

## Langkah-Langkah Testing:

### 1. **Test dengan Data JSON Anda**
Buat fungsi test sederhana:

```python
def test_json_parsing():
    # Gunakan data JSON Anda sebagai test
    test_json = {
        "General": {...},  # isi dengan data dari bacdive_590.json
        "Name and taxonomic classification": {...},
        # dst
    }
    
    param_keys = get_param_keys()
    result = extract_bacdive_data(test_json, param_keys)
    print("Test result:", result)
```

### 2. **Verifikasi API Response**
Tambahkan logging untuk melihat struktur response yang sebenarnya:

```python
# Di dalam fetch_and_cache_profiles_by_taxonomy
print(f"Raw API response keys: {list(raw.keys())}")
print(f"First level structure: {raw}")
```

### 3. **Check Authentication**
Pastikan autentikasi berhasil dengan menambahkan logging:

```python
# Di auth.py, tambahkan setelah mendapat token
if access_token:
    print(f"✅ Authentication successful. Token starts with: {access_token[:20]}...")
```

## File yang Perlu Dimodifikasi:

1. **`bacdive_mapper.py`** - Fungsi parsing utama
2. **`app.py`** - Tambah debug logging
3. **Test dengan file JSON sampel Anda** - Untuk validasi parsing

## Langkah Implementasi:

1. **Backup file existing**
2. **Implementasi perbaikan satu per satu**
3. **Test dengan satu genus dulu** (misal: Bacillus)
4. **Cek log output** untuk memastikan parsing berhasil
5. **Gradually expand** ke genus lainnya

Dengan perbaikan ini, aplikasi Anda seharusnya bisa mengambil dan memproses data dari BacDive API dengan benar.