import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import openpyxl
import os
import requests
import json
from datetime import datetime
import time

# Note: Untuk support file Excel yang lebih lengkap, install packages tambahan:
# pip install xlrd pyxlsb requests

# Konfigurasi halaman
st.set_page_config(
    page_title="🧫 BakteriFinder: Aplikasi Identifikasi Bakteri Otomatis",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Kolom yang diperlukan untuk identifikasi
REQUIRED_COLUMNS = [
    'Sampel', 'Gram', 'Katalase', 'Oksidase', 'Glukosa', 'Laktosa', 
    'H2S', 'MR', 'VP', 'Citrate', 'Urease', 'Indol', 'Motilitas', 
    'Dnase', 'Esculin', 'Nitrate'
]

# Kolom uji (exclude Sampel dan kolom deskripsi)
TEST_COLUMNS = REQUIRED_COLUMNS[1:]

# Mapping untuk BacDive API field names
BACDIVE_FIELD_MAPPING = {
    'Gram': 'gram_stain',
    'Katalase': 'catalase',
    'Oksidase': 'oxidase',
    'Glukosa': 'glucose',
    'Laktosa': 'lactose',
    'H2S': 'h2s_production',
    'MR': 'methyl_red',
    'VP': 'voges_proskauer',
    'Citrate': 'citrate_utilization',
    'Urease': 'urease',
    'Indol': 'indole',
    'Motilitas': 'motility',
    'Dnase': 'dnase',
    'Esculin': 'esculin_hydrolysis',
    'Nitrate': 'nitrate_reduction'
}

class BacDiveAPI:
    """Class untuk mengakses BacDive API"""
    
    def __init__(self, username=None, password=None):
        self.base_url = "https://bacdive.dsmz.de/api/"
        self.username = username
        self.password = password
        self.session = None
        self.authenticated = False
    
    def authenticate(self):
        """Autentikasi ke BacDive API"""
        if not self.username or not self.password:
            return False, "Username dan password BacDive diperlukan"
        
        try:
            self.session = requests.Session()
            auth_url = f"{self.base_url}login/"
            
            response = self.session.post(auth_url, 
                                       auth=(self.username, self.password),
                                       timeout=30)
            
            if response.status_code == 200:
                self.authenticated = True
                return True, "Berhasil login ke BacDive"
            else:
                return False, f"Login gagal: {response.status_code}"
                
        except Exception as e:
            return False, f"Error saat login: {str(e)}"
    
    def search_bacteria(self, species_name):
        """Mencari data bakteri berdasarkan nama spesies"""
        if not self.authenticated:
            return None, "Belum terotentikasi ke BacDive"
        
        try:
            search_url = f"{self.base_url}taxon/search/"
            params = {'species': species_name}
            
            response = self.session.get(search_url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"Search gagal: {response.status_code}"
                
        except Exception as e:
            return None, f"Error saat search: {str(e)}"
    
    def get_strain_data(self, strain_id):
        """Mendapatkan data strain lengkap"""
        if not self.authenticated:
            return None, "Belum terotentikasi ke BacDive"
        
        try:
            strain_url = f"{self.base_url}strain/{strain_id}/"
            
            response = self.session.get(strain_url, timeout=30)
            
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"Get strain data gagal: {response.status_code}"
                
        except Exception as e:
            return None, f"Error saat get strain data: {str(e)}"
    
    def bulk_search(self, species_list, max_strains_per_species=3):
        """Pencarian bulk untuk multiple species"""
        if not self.authenticated:
            return None, "Belum terotentikasi ke BacDive"
        
        all_data = []
        for species in species_list:
            search_result, error = self.search_bacteria(species)
            if not error and search_result and 'results' in search_result:
                count = 0
                for result in search_result['results']:
                    if count >= max_strains_per_species:
                        break
                    strain_id = result.get('strain_id')
                    if strain_id:
                        strain_data, error = self.get_strain_data(strain_id)
                        if strain_data and not error:
                            all_data.append(strain_data)
                            count += 1
                        time.sleep(0.5)  # Rate limiting
        
        return all_data, None

def read_uploaded_file(uploaded_file):
    """Membaca file yang diupload dengan support untuk berbagai format Excel"""
    try:
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # Untuk CSV, coba beberapa encoding
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    data = pd.read_csv(uploaded_file, encoding=encoding)
                    return data, None
                except UnicodeDecodeError:
                    continue
            return None, "Gagal membaca CSV dengan semua encoding yang dicoba"
        
        elif file_extension in ['xlsx', 'xls', 'xlsm', 'xlsb']:
            # Untuk Excel, gunakan engine yang sesuai
            engines = {
                'xls': ['xlrd', None],
                'xlsx': ['openpyxl', None],
                'xlsm': ['openpyxl', None],
                'xlsb': ['pyxlsb', None]
            }
            
            engines_to_try = engines.get(file_extension, [None])
            
            for engine in engines_to_try:
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    if engine:
                        data = pd.read_excel(uploaded_file, engine=engine)
                    else:
                        data = pd.read_excel(uploaded_file)
                    return data, None
                except Exception as e:
                    if engine == engines_to_try[-1]:  # Last engine failed
                        return None, f"Error membaca Excel dengan semua engine: {str(e)}"
                    continue
        
        else:
            return None, f"Format file '{file_extension}' tidak didukung"
        
    except Exception as e:
        return None, f"Error membaca file: {str(e)}"

def create_sample_database():
    """Buat database contoh jika file tidak ada"""
    sample_data = [
        {
            'Nama_Bakteri': 'Escherichia coli',
            'Gram': '-', 'Katalase': '+', 'Oksidase': '-', 'Glukosa': '+', 'Laktosa': '+',
            'H2S': '-', 'MR': '+', 'VP': '-', 'Citrate': '-', 'Urease': '-', 'Indol': '+',
            'Motilitas': '+', 'Dnase': '-', 'Esculin': '-', 'Nitrate': '+',
            'Deskripsi': 'Bakteri gram negatif, berbentuk batang, fakultatif anaerob',
            'Habitat': 'Usus manusia dan hewan, lingkungan',
            'Patogenisitas': 'Beberapa strain patogenik (EPEC, ETEC, EHEC)',
            'Sumber': 'Database lokal'
        },
        {
            'Nama_Bakteri': 'Staphylococcus aureus',
            'Gram': '+', 'Katalase': '+', 'Oksidase': '-', 'Glukosa': '+', 'Laktosa': '-',
            'H2S': '-', 'MR': '+', 'VP': '+', 'Citrate': '+', 'Urease': '+', 'Indol': '-',
            'Motilitas': '-', 'Dnase': '+', 'Esculin': '-', 'Nitrate': '+',
            'Deskripsi': 'Bakteri gram positif, berbentuk bulat bergerombol',
            'Habitat': 'Kulit, hidung, tenggorokan manusia',
            'Patogenisitas': 'Patogen oportunistik, infeksi kulit, pneumonia',
            'Sumber': 'Database lokal'
        },
        {
            'Nama_Bakteri': 'Pseudomonas aeruginosa',
            'Gram': '-', 'Katalase': '+', 'Oksidase': '+', 'Glukosa': '+', 'Laktosa': '-',
            'H2S': '-', 'MR': '-', 'VP': '-', 'Citrate': '+', 'Urease': '-', 'Indol': '-',
            'Motilitas': '+', 'Dnase': '+', 'Esculin': '-', 'Nitrate': '+',
            'Deskripsi': 'Bakteri gram negatif, aerob obligat, menghasilkan pigmen biru-hijau',
            'Habitat': 'Tanah, air, lingkungan rumah sakit',
            'Patogenisitas': 'Patogen nosokomial, infeksi pada pasien immunocompromised',
            'Sumber': 'Database lokal'
        },
        {
            'Nama_Bakteri': 'Salmonella spp.',
            'Gram': '-', 'Katalase': '+', 'Oksidase': '-', 'Glukosa': '+', 'Laktosa': '-',
            'H2S': '+', 'MR': '+', 'VP': '-', 'Citrate': '+', 'Urease': '-', 'Indol': '-',
            'Motilitas': '+', 'Dnase': '-', 'Esculin': '-', 'Nitrate': '+',
            'Deskripsi': 'Bakteri gram negatif, fakultatif anaerob, non-laktosa fermenter',
            'Habitat': 'Usus manusia dan hewan, makanan terkontaminasi',
            'Patogenisitas': 'Penyebab gastroenteritis, demam tifoid',
            'Sumber': 'Database lokal'
        },
        {
            'Nama_Bakteri': 'Bacillus subtilis',
            'Gram': '+', 'Katalase': '+', 'Oksidase': '+', 'Glukosa': '+', 'Laktosa': '-',
            'H2S': '-', 'MR': '-', 'VP': '+', 'Citrate': '+', 'Urease': '-', 'Indol': '-',
            'Motilitas': '+', 'Dnase': '-', 'Esculin': '+', 'Nitrate': '+',
            'Deskripsi': 'Bakteri gram positif, berbentuk batang, pembentuk spora',
            'Habitat': 'Tanah, air, dekomposisi bahan organik',
            'Patogenisitas': 'Umumnya non-patogenik, probiotik',
            'Sumber': 'Database lokal'
        },
        {
            'Nama_Bakteri': 'Streptococcus pyogenes',
            'Gram': '+', 'Katalase': '-', 'Oksidase': '-', 'Glukosa': '+', 'Laktosa': '-',
            'H2S': '-', 'MR': '+', 'VP': '-', 'Citrate': '-', 'Urease': '-', 'Indol': '-',
            'Motilitas': '-', 'Dnase': '-', 'Esculin': '-', 'Nitrate': '-',
            'Deskripsi': 'Bakteri gram positif, berbentuk bulat berantai',
            'Habitat': 'Tenggorokan, kulit manusia',
            'Patogenisitas': 'Patogen, penyebab faringitis, impetigo, necrotizing fasciitis',
            'Sumber': 'Database lokal'
        },
        {
            'Nama_Bakteri': 'Enterococcus faecalis',
            'Gram': '+', 'Katalase': '-', 'Oksidase': '-', 'Glukosa': '+', 'Laktosa': '-',
            'H2S': '-', 'MR': '+', 'VP': '+', 'Citrate': '-', 'Urease': '-', 'Indol': '-',
            'Motilitas': '-', 'Dnase': '-', 'Esculin': '+', 'Nitrate': '-',
            'Deskripsi': 'Bakteri gram positif, berbentuk bulat berpasangan atau berantai',
            'Habitat': 'Usus manusia dan hewan',
            'Patogenisitas': 'Patogen oportunistik, infeksi saluran kemih, endokarditis',
            'Sumber': 'Database lokal'
        }
    ]
    
    df = pd.DataFrame(sample_data)
    try:
        df.to_excel('database_bakteri.xlsx', index=False, engine='openpyxl')
        return True, f"Database contoh berhasil dibuat dengan {len(sample_data)} spesies bakteri"
    except Exception as e:
        return False, f"Gagal membuat database contoh: {str(e)}"

def load_database():
    """Load database bakteri dari file Excel dengan error handling"""
    try:
        database_file = "database_bakteri.xlsx"
        
        if os.path.exists(database_file):
            engines_to_try = ['openpyxl', 'xlrd', None]  # None = auto-detect
            
            for engine in engines_to_try:
                try:
                    if engine:
                        database = pd.read_excel(database_file, engine=engine)
                    else:
                        database = pd.read_excel(database_file)
                    return database, None
                except Exception as engine_error:
                    if engine == engines_to_try[-1]:  # Last engine failed
                        return None, f"Error membaca database dengan semua engine: {str(engine_error)}"
                    continue
        else:
            return None, "File 'database_bakteri.xlsx' tidak ditemukan"
            
    except Exception as e:
        return None, f"Error membaca database: {str(e)}"

def fetch_from_bacdive(species_list, username, password):
    """Fetch data dari BacDive API untuk daftar spesies"""
    bacdive = BacDiveAPI(username, password)
    
    # Authenticate
    success, message = bacdive.authenticate()
    if not success:
        return None, message
    
    fetched_data = []
    progress_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, species in enumerate(species_list):
            status_text.text(f"Mengambil data untuk: {species}")
            
            # Search species
            search_result, error = bacdive.search_bacteria(species)
            if error:
                st.warning(f"Gagal mencari {species}: {error}")
                continue
            
            # Process search results
            if search_result and 'results' in search_result:
                for result in search_result['results'][:3]:  # Ambil max 3 strain per spesies
                    strain_id = result.get('strain_id')
                    if strain_id:
                        strain_data, error = bacdive.get_strain_data(strain_id)
                        if strain_data and not error:
                            # Parse strain data and convert to our format
                            parsed_data = parse_bacdive_data(strain_data)
                            if parsed_data:
                                fetched_data.append(parsed_data)
                        
                        # Rate limiting
                        time.sleep(0.5)
            
            progress_bar.progress((i + 1) / len(species_list))
        
        status_text.text("Selesai mengambil data dari BacDive")
    
    return fetched_data, None

def parse_bacdive_data(strain_data):
    """Parse data dari BacDive ke format yang sesuai dengan aplikasi"""
    try:
        parsed = {
            'Nama_Bakteri': strain_data.get('species', 'Unknown'),
            'Sumber': 'BacDive API'
        }
        
        # Initialize all test columns with unknown values
        for col in TEST_COLUMNS:
            parsed[col] = 'unknown'
        
        # Parse physiological data if available
        if 'physiology_and_metabolism' in strain_data:
            phys_data = strain_data['physiology_and_metabolism']
            
            # Map BacDive fields to our columns
            for our_field, bacdive_field in BACDIVE_FIELD_MAPPING.items():
                if bacdive_field in phys_data:
                    value = phys_data[bacdive_field]
                    # Convert to our format (+ or -)
                    if isinstance(value, bool):
                        parsed[our_field] = '+' if value else '-'
                    elif isinstance(value, str):
                        if value.lower() in ['positive', 'pos', '+', 'yes']:
                            parsed[our_field] = '+'
                        elif value.lower() in ['negative', 'neg', '-', 'no']:
                            parsed[our_field] = '-'
        
        # Add additional info if available
        parsed['Deskripsi'] = strain_data.get('description', '')
        parsed['Habitat'] = strain_data.get('isolation_source', '')
        parsed['Patogenisitas'] = strain_data.get('pathogenicity', '')
        
        return parsed
        
    except Exception as e:
        st.warning(f"Error parsing BacDive data: {str(e)}")
        return None

def create_bacdive_database(username, password, extended_species_list=False):
    """Membuat database dari BacDive API sebagai pengganti database lokal"""
    
    # Daftar spesies yang umum untuk identifikasi
    common_species = [
        "Escherichia coli", "Staphylococcus aureus", "Pseudomonas aeruginosa",
        "Salmonella enterica", "Bacillus subtilis", "Streptococcus pyogenes",
        "Enterococcus faecalis", "Klebsiella pneumoniae", "Proteus mirabilis",
        "Citrobacter freundii", "Enterobacter cloacae", "Serratia marcescens"
    ]
    
    if extended_species_list:
        # Daftar extended untuk database yang lebih lengkap
        extended_species = [
            "Acinetobacter baumannii", "Stenotrophomonas maltophilia",
            "Burkholderia cepacia", "Alcaligenes faecalis", "Moraxella catarrhalis",
            "Haemophilus influenzae", "Neisseria gonorrhoeae", "Listeria monocytogenes",
            "Clostridium perfringens", "Bacteroides fragilis", "Prevotella melaninogenica",
            "Fusobacterium nucleatum", "Actinomyces israelii", "Nocardia asteroides",
            "Mycobacterium tuberculosis", "Corynebacterium diphtheriae"
        ]
        common_species.extend(extended_species)
    
    bacdive = BacDiveAPI(username, password)
    
    # Test authentication
    success, message = bacdive.authenticate()
    if not success:
        return None, message
    
    st.info(f"🌐 Mengambil data dari BacDive API untuk {len(common_species)} spesies...")
    
    # Fetch data
    fetched_data, error = fetch_from_bacdive(common_species, username, password)
    
    if error:
        return None, error
    
    if not fetched_data:
        return None, "Tidak ada data yang berhasil diambil dari BacDive"
    
    # Convert to DataFrame
    df = pd.DataFrame(fetched_data)
    
    # Save to Excel
    try:
        df.to_excel('database_bakteri_bacdive.xlsx', index=False, engine='openpyxl')
        return df, f"Database BacDive berhasil dibuat dengan {len(fetched_data)} strain bakteri"
    except Exception as e:
        return df, f"Data berhasil diambil tapi gagal disave ke Excel: {str(e)}"

def validate_data(data):
    """Validasi data input"""
    errors = []
    
    # Cek kolom yang diperlukan
    missing_cols = []
    for col in REQUIRED_COLUMNS:
        # Case-insensitive check
        col_found = False
        for data_col in data.columns:
            if col.lower() == data_col.lower():
                col_found = True
                break
        if not col_found:
            missing_cols.append(col)
    
    if missing_cols:
        errors.append(f"Kolom yang hilang: {', '.join(missing_cols)}")
    
    # Cek apakah ada data
    if data.empty:
        errors.append("File tidak berisi data.")
    
    # Cek format data uji (harus + atau -)
    for col in TEST_COLUMNS:
        for data_col in data.columns:
            if col.lower() == data_col.lower():
                invalid_values = data[data_col].dropna().unique()
                valid_values = ['+', '-', 'pos', 'neg', 'positive', 'negative', 'unknown', '?']
                invalid_values = [v for v in invalid_values if str(v).strip().lower() not in valid_values]
                if invalid_values:
                    errors.append(f"Kolom '{data_col}' mengandung nilai tidak valid: {invalid_values}. Gunakan '+', '-', atau 'unknown'.")
                break
    
    return errors

def normalize_data(data):
    """Normalisasi data input untuk konsistensi"""
    data_normalized = data.copy()
    
    # Normalisasi nama kolom (case-insensitive)
    column_mapping = {}
    for req_col in REQUIRED_COLUMNS:
        for data_col in data.columns:
            if req_col.lower() == data_col.lower():
                column_mapping[data_col] = req_col
                break
    
    data_normalized = data_normalized.rename(columns=column_mapping)
    
    # Normalisasi nilai uji
    for col in TEST_COLUMNS:
        if col in data_normalized.columns:
            data_normalized[col] = data_normalized[col].astype(str).str.strip().str.lower()
            data_normalized[col] = data_normalized[col].replace({
                'pos': '+', 'positive': '+', 'ya': '+', 'yes': '+',
                'neg': '-', 'negative': '-', 'tidak': '-', 'no': '-',
                '?': 'unknown', 'nan': 'unknown', 'none': 'unknown'
            })
    
    return data_normalized

def calculate_confidence_score(score, total_tests, unknown_count=0):
    """Hitung confidence score berdasarkan matching dengan penalti untuk unknown"""
    if total_tests == 0:
        return 0, "No Data"
    
    # Penalti untuk unknown values
    penalty = (unknown_count / total_tests) * 10  # Max 10% penalty
    percentage = ((score / total_tests) * 100) - penalty
    percentage = max(0, percentage)  # Tidak boleh negatif
    
    if percentage >= 95:
        return percentage, "Perfect Match"
    elif percentage >= 80:
        return percentage, "High Confidence"
    elif percentage >= 60:
        return percentage, "Medium Confidence"
    elif percentage >= 40:
        return percentage, "Low Confidence"
    else:
        return percentage, "No Match"

def identifikasi_bakteri(row_data, database):
    """Identifikasi bakteri dengan scoring yang lebih akurat"""
    matches = []
    
    # Normalisasi database juga
    database_normalized = database.copy()
    for col in TEST_COLUMNS:
        if col in database_normalized.columns:
            database_normalized[col] = database_normalized[col].astype(str).str.strip().str.lower()
            database_normalized[col] = database_normalized[col].replace({
                'pos': '+', 'positive': '+',
                'neg': '-', 'negative': '-',
                '?': 'unknown', 'nan': 'unknown', 'none': 'unknown'
            })
    
    for index, db_row in database_normalized.iterrows():
        score = 0
        total_tests = 0
        unknown_count = 0
        matched_tests = []
        
        for col in TEST_COLUMNS:
            if col in row_data and col in db_row:
                row_val = str(row_data[col]).strip().lower()
                db_val = str(db_row[col]).strip().lower()
                
                # Skip jika kedua nilai unknown
                if row_val == 'unknown' and db_val == 'unknown':
                    continue
                
                total_tests += 1
                
                # Hitung unknown
                if row_val == 'unknown' or db_val == 'unknown':
                    unknown_count += 1
                    # Partial score untuk unknown (0.3 dari 1)
                    score += 0.3
                elif row_val == db_val:
                    score += 1
                    matched_tests.append(col)
        
        if total_tests > 0:
            percentage, confidence = calculate_confidence_score(score, total_tests, unknown_count)
            
            matches.append({
                'nama': db_row.get("Nama_Bakteri", "Unknown"),
                'score': round(score, 1),
                'total_tests': total_tests,
                'percentage': round(percentage, 1),
                'confidence': confidence,
                'matched_tests': matched_tests,
                'unknown_count': unknown_count,
                'deskripsi': db_row.get("Deskripsi", ""),
                'habitat': db_row.get("Habitat", ""),
                'patogenisitas': db_row.get("Patogenisitas", ""),
                'sumber': db_row.get("Sumber", "Database lokal")
            })
    
    # Sort by percentage, then by score
    matches.sort(key=lambda x: (x['percentage'], x['score']), reverse=True)
    return matches

def create_results_dataframe(data, results):
    """Buat DataFrame hasil untuk download"""
    results_list = []
    
    for i, (index, row) in enumerate(data.iterrows()):
        sampel = row.get('Sampel', f'Sampel_{i+1}')
        if i < len(results) and len(results[i]) > 0:
            top_result = results[i][0]
            results_list.append({
                'Sampel': sampel,
                'Kandidat_Utama': top_result['nama'],
                'Confidence_Score': f"{top_result['percentage']}%",
                'Confidence_Level': top_result['confidence'],
                'Matched_Tests': f"{top_result['score']}/{top_result['total_tests']}",
                'Unknown_Tests': top_result['unknown_count'],
                'Deskripsi': top_result['deskripsi'],
                'Habitat': top_result['habitat'],
                'Patogenisitas': top_result['patogenisitas'],
                'Sumber_Data': top_result['sumber'],
                'Waktu_Analisis': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            results_list.append({
                'Sampel': sampel,
                'Kandidat_Utama': 'Tidak teridentifikasi',
                'Confidence_Score': '0%',
                'Confidence_Level': 'No Match',
                'Matched_Tests': '0/0',
                'Unknown_Tests': 0,
                'Deskripsi': '',
                'Habitat': '',
                'Patogenisitas': '',
                'Sumber_Data': '',
                'Waktu_Analisis': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    return pd.DataFrame(results_list)

def main():
    st.title("🧫 BakteriFinder: Aplikasi Identifikasi Bakteri Otomatis")
    st.markdown("**Aplikasi untuk mengidentifikasi bakteri berdasarkan hasil uji laboratorium mikrobiologi**")
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Panduan Penggunaan")
        st.markdown("""
        1. **Upload File**: Upload file CSV atau Excel berisi data hasil uji bakteri
        2. **Validasi**: Pastikan file memiliki kolom yang diperlukan
        3. **Analisis**: Klik tombol 'Identifikasi Bakteri' untuk memulai
        4. **Hasil**: Lihat