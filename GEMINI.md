# Prompt untuk Debugging Ekstraksi Parameter BacDive

## Masalah yang Dihadapi
Aplikasi Streamlit untuk identifikasi bakteri menggunakan BacDive API berhasil mengambil data strain, namun **tidak dapat menampilkan detail parameter** seperti Gram_stain, Motility, Catalase, Oxidase, dll. Semua parameter menunjukkan nilai "N/A".

## Analisis Masalah
1. **Struktur JSON BacDive tidak sesuai dengan mapping** yang ada di `PARAM_TO_BACDIVE_KEY`
2. **Fungsi `extract_clean_profile()`** gagal mengekstrak nilai dari nested JSON
3. **Path navigasi JSON** mungkin salah atau tidak lengkap
4. **Normalisasi nilai** (positive/negative) tidak bekerja dengan baik

## Tugas yang Perlu Dilakukan

### 1. Debug Struktur Data JSON
```python
# Tambahkan logging untuk melihat struktur actual JSON
def debug_json_structure(strain_data, bacdive_id):
    """Debug function to understand actual JSON structure"""
    print(f"\n=== DEBUG JSON STRUCTURE FOR ID: {bacdive_id} ===")
    
    # Print main sections
    for main_key in strain_data.keys():
        print(f"Main section: {main_key}")
        if isinstance(strain_data[main_key], dict):
            for sub_key in strain_data[main_key].keys():
                print(f"  - {sub_key}: {type(strain_data[main_key][sub_key])}")
    
    # Specific check for morphology and physiology sections
    if 'morphology' in strain_data:
        print(f"\nMORPHOLOGY KEYS: {list(strain_data['morphology'].keys())}")
    
    if 'physiology and metabolism' in strain_data:
        print(f"PHYSIOLOGY KEYS: {list(strain_data['physiology and metabolism'].keys())}")
    
    return strain_data
```

### 2. Perbaiki Fungsi Extract Clean Profile
```python
def extract_clean_profile_fixed(strain_data, debug=False):
    """Fixed version with better JSON navigation and debugging"""
    profile = {}
    
    if debug:
        debug_json_structure(strain_data, strain_data.get('id', 'unknown'))
    
    # Extract taxonomy (this probably works)
    try:
        taxonomy = strain_data['general']['taxonomy']
        species = taxonomy['species']
        subspecies = taxonomy.get('subspecies', '')
        profile['Nama Bakteri'] = f"{taxonomy['genus']} {species} {subspecies}".strip()
    except KeyError:
        profile['Nama Bakteri'] = "Unknown Species"

    # Enhanced parameter extraction with multiple fallback strategies
    for param in get_param_keys():
        profile[param] = extract_parameter_value(strain_data, param, debug)
    
    return profile

def extract_parameter_value(strain_data, param, debug=False):
    """Enhanced parameter extraction with multiple strategies"""
    if param not in PARAM_TO_BACDIVE_KEY:
        return 'N/A'
    
    paths = PARAM_TO_BACDIVE_KEY[param]
    found_value = None
    
    for path_index, keys in enumerate(paths):
        try:
            value = strain_data
            navigation_log = f"Path {path_index + 1}: "
            
            for key_index, key in enumerate(keys):
                navigation_log += f"[{key}]"
                
                if isinstance(value, list):
                    # Strategy 1: Find dict in list with key
                    temp_value = None
                    for item in value:
                        if isinstance(item, dict) and key in item:
                            temp_value = item[key]
                            break
                    value = temp_value
                elif isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                    break
                
                if value is None:
                    break
            
            if debug and value is not None:
                print(f"  {param} - {navigation_log} -> Found: {value}")
            
            if value is not None:
                found_value = normalize_bacdive_value(value)
                break
                
        except (KeyError, TypeError, AttributeError) as e:
            if debug:
                print(f"  {param} - Path {path_index + 1} failed: {e}")
            continue
    
    return found_value if found_value is not None else 'N/A'

def normalize_bacdive_value(value):
    """Normalize BacDive values to standard format"""
    if isinstance(value, dict):
        # Check common BacDive dict structures
        for possible_key in ['ability', 'activity', 'result', 'value', 'reaction']:
            if possible_key in value:
                return normalize_simple_value(value[possible_key])
        
        # If no standard key found, return the dict as string representation
        return str(value)
    else:
        return normalize_simple_value(value)

def normalize_simple_value(value):
    """Normalize simple values to positive/negative"""
    if value is None:
        return 'N/A'
    
    str_value = str(value).lower().strip()
    
    # Positive indicators
    positive_indicators = ['+', 'positive', 'yes', 'ya', 'acid', 'positif', 
                          'acid production', 'fermentation', 'present', 'detected']
    
    # Negative indicators  
    negative_indicators = ['-', 'negative', 'no', 'tidak', 'negatif', 
                          'absent', 'not detected', 'none']
    
    if any(indicator in str_value for indicator in positive_indicators):
        return 'positive'
    elif any(indicator in str_value for indicator in negative_indicators):
        return 'negative'
    else:
        return str_value
```

### 3. Tambahkan Mode Debug di Main App
```python
# Di fungsi main(), tambahkan checkbox debug
debug_mode = st.sidebar.checkbox("🐛 Debug Mode", help="Tampilkan struktur JSON untuk debugging")

# Modifikasi pemanggilan extract_clean_profile
if debug_mode:
    clean_profile = extract_clean_profile_fixed(bacdive_profile, debug=True)
else:
    clean_profile = extract_clean_profile(bacdive_profile)
```

### 4. Tambahkan Sample Data Inspector
```python
def inspect_sample_data(strain_data, sample_size=3):
    """Inspect first few strain data to understand structure"""
    st.subheader("🔍 Sample Data Inspector")
    
    with st.expander("Raw JSON Structure Analysis"):
        count = 0
        for bacdive_id, data in strain_data.items():
            if count >= sample_size:
                break
                
            st.write(f"**Strain ID: {bacdive_id}**")
            
            # Show main sections
            st.write("Main sections:", list(data.keys()))
            
            # Show morphology details if exists
            if 'morphology' in data:
                st.write("Morphology keys:", list(data['morphology'].keys()))
                st.json(data['morphology'])
            
            # Show physiology details if exists  
            if 'physiology and metabolism' in data:
                st.write("Physiology keys:", list(data['physiology and metabolism'].keys()))
                # Only show first few items to avoid overwhelming
                physio_data = data['physiology and metabolism']
                sample_physio = {k: v for i, (k, v) in enumerate(physio_data.items()) if i < 5}
                st.json(sample_physio)
            
            st.divider()
            count += 1
```

### 5. Testing Script untuk Validasi
```python
# Buat file terpisah: test_parameter_extraction.py
def test_parameter_extraction():
    """Test parameter extraction dengan data sample"""
    
    # Load sample data from cache
    cache = load_cache()
    
    for genus, data in cache.items():
        print(f"\n=== TESTING GENUS: {genus} ===")
        profiles = data.get('profiles', {})
        
        for bacdive_id, strain_data in list(profiles.items())[:2]:  # Test first 2 strains
            print(f"\nTesting strain ID: {bacdive_id}")
            
            # Test current extraction
            clean_profile = extract_clean_profile(strain_data)
            
            # Test fixed extraction
            clean_profile_fixed = extract_clean_profile_fixed(strain_data, debug=True)
            
            # Compare results
            print(f"\nComparison for {clean_profile.get('Nama Bakteri', 'Unknown')}:")
            for param in ['Gram_stain', 'Motility', 'Catalase', 'Oxidase']:
                old_val = clean_profile.get(param, 'N/A')
                new_val = clean_profile_fixed.get(param, 'N/A')
                status = "✅ SAME" if old_val == new_val else "🔄 DIFFERENT"
                print(f"  {param}: {old_val} -> {new_val} ({status})")

if __name__ == "__main__":
    test_parameter_extraction()
```

## Langkah Eksekusi
1. **Jalankan debug mode** untuk melihat struktur JSON actual
2. **Implementasikan fungsi perbaikan** extract_clean_profile_fixed()
3. **Test dengan sample data** menggunakan script testing
4. **Update mapping paths** berdasarkan struktur JSON yang ditemukan
5. **Validasi hasil** dengan membandingkan output lama vs baru

## Expected Output
Setelah perbaikan, parameter seperti:
- `Gram_stain: positive/negative` (bukan N/A)
- `Motility: positive/negative` (bukan N/A)  
- `Catalase: positive/negative` (bukan N/A)
- dll.

Akan menampilkan nilai actual dari BacDive, bukan "N/A".