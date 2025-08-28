import pandas as pd
import json
import os
import time
import streamlit as st
import requests

# --- 0. Konfigurasi Cache ---
CACHE_FILE = "bacdive_cache.json"
CACHE_DURATION_SECONDS = 24 * 60 * 60  # Cache berlaku selama 24 jam

# --- 1. MAPPING & WEIGHTS YANG DIPERBAIKI ---
COLUMN_ALIASES = {
    "Motilitas": "Motility", "Pewarnaan Gram": "Gram_stain", "Gram": "Gram_stain",
    "Katalase": "Catalase", "Oksidase": "Oxidase", "Indol": "Indole", "Urease": "Urease",
    "Dnase": "DNase", "Gelatin": "Gelatinase", "Nitrate Reduction": "Nitrate_reduction",
    "H2S": "H2S_production", "Glukosa": "Glucose", "Laktosa": "Lactose", "Maltosa": "Maltose",
    "Sukrosa": "Sucrose", "Manitol": "Mannitol", "Sorbitol": "Sorbitol", "Xilosa": "Xylose",
    "Arabinosa": "Arabinose", "Trehalosa": "Trehalose",
}

# PERBAIKAN: Mapping yang lebih akurat sesuai struktur BacDive
PARAM_TO_BACDIVE_KEY = {
    'Gram_stain': [
        ["Name and taxonomic classification", "phylum"],  # Inference dari phylum
        ["Morphology", "gram stain"], 
        ["Morphology", "Gram stain"],
        ["Morphology", "cell wall and cell membranes", "gram stain"]
    ],
    'Motility': [
        ["Morphology", "motility"],
        ["Morphology", "Motility"],
        ["Morphology", "cell motility"]
    ],
    'Catalase': [
        ["Physiology and metabolism", "enzymes", "catalase"], 
        ["Physiology and metabolism", "catalase"],
        ["Physiology and metabolism", "enzyme activities", "catalase"]
    ],
    'Oxidase': [
        ["Physiology and metabolism", "enzymes", "oxidase"], 
        ["Physiology and metabolism", "oxidase"],
        ["Physiology and metabolism", "enzyme activities", "oxidase"]
    ],
    'Urease': [
        ["Physiology and metabolism", "enzymes", "urease"], 
        ["Physiology and metabolism", "urease"],
        ["Physiology and metabolism", "enzyme activities", "urease"]
    ],
    'DNase': [
        ["Physiology and metabolism", "enzymes", "DNase"], 
        ["Physiology and metabolism", "DNase"],
        ["Physiology and metabolism", "enzyme activities", "DNase"]
    ],
    'Gelatinase': [
        ["Physiology and metabolism", "enzymes", "gelatinase"], 
        ["Physiology and metabolism", "gelatinase"],
        ["Physiology and metabolism", "enzyme activities", "gelatinase"]
    ],
    'Nitrate_reduction': [
        ["Physiology and metabolism", "nitrate reduction"],
        ["Physiology and metabolism", "Nitrate reduction"],
        ["Physiology and metabolism", "metabolic test results", "nitrate reduction"]
    ],
    'Indole': [
        ["Physiology and metabolism", "indole test"],
        ["Physiology and metabolism", "Indole"],
        ["Physiology and metabolism", "metabolic test results", "indole"]
    ],
    'MR': [
        ["Physiology and metabolism", "methyl red test"],
        ["Physiology and metabolism", "Methyl red"],
        ["Physiology and metabolism", "metabolic test results", "methyl red"]
    ],
    'VP': [
        ["Physiology and metabolism", "voges proskauer test"],
        ["Physiology and metabolism", "Voges Proskauer"],
        ["Physiology and metabolism", "metabolic test results", "voges proskauer"]
    ],
    'Citrate': [
        ["Physiology and metabolism", "citrate utilization"],
        ["Physiology and metabolism", "Citrate"],
        ["Physiology and metabolism", "carbon sources", "citrate"]
    ],
    'H2S_production': [
        ["Physiology and metabolism", "H2S production"],
        ["Physiology and metabolism", "hydrogen sulfide"],
        ["Physiology and metabolism", "metabolic test results", "H2S"]
    ],
    'Glucose': [
        ["Physiology and metabolism", "carbon sources", "glucose"], 
        ["Physiology and metabolism", "metabolite utilization", "glucose"],
        ["Physiology and metabolism", "Glucose"]
    ],
    'Lactose': [
        ["Physiology and metabolism", "carbon sources", "lactose"], 
        ["Physiology and metabolism", "metabolite utilization", "lactose"],
        ["Physiology and metabolism", "Lactose"]
    ],
    'Sucrose': [
        ["Physiology and metabolism", "carbon sources", "sucrose"], 
        ["Physiology and metabolism", "metabolite utilization", "sucrose"],
        ["Physiology and metabolism", "Sucrose"]
    ],
    'Mannitol': [
        ["Physiology and metabolism", "carbon sources", "mannitol"], 
        ["Physiology and metabolism", "metabolite utilization", "mannitol"]
    ],
    'Sorbitol': [
        ["Physiology and metabolism", "carbon sources", "sorbitol"], 
        ["Physiology and metabolism", "metabolite utilization", "sorbitol"]
    ],
    'Temperature_range': [
        ["Culture and growth conditions", "culture temp"],
        ["Culture and growth conditions", "temperature range"],
        ["Culture and growth conditions", "Temperature"]
    ],
    'pH_range': [
        ["Culture and growth conditions", "pH"],
        ["Culture and growth conditions", "pH range"]
    ],
    'NaCl_tolerance': [
        ["Culture and growth conditions", "NaCl"],
        ["Culture and growth conditions", "sodium chloride"]
    ]
}

WEIGHTS = {
    'Gram_stain': 3, 'Motility': 3, 'Catalase': 3, 'Oxidase': 3, 'Urease': 3, 'DNase': 3, 'Gelatinase': 3,
    'Indole': 2, 'MR': 2, 'VP': 2, 'Citrate': 2, 'Lysine_decarboxylase': 2, 'Ornithine_decarboxylase': 2, 
    'Arginine_dihydrolase': 2, 'Nitrate_reduction': 2, 'H2S_production': 2,
    'Glucose': 1, 'Lactose': 1, 'Sucrose': 1, 'Mannitol': 1, 'Sorbitol': 1, 'Xylose': 1, 'Arabinose': 1, 
    'Trehalose': 1, 'Inositol': 1, 'Maltose': 1, 'Raffinose': 1, 'Fructose': 1,
    'NaCl_tolerance': 1, 'Temperature_range': 1, 'pH_range': 1
}

# --- 2. Fungsi Utilitas & Normalisasi ---
def get_param_keys():
    return list(PARAM_TO_BACDIVE_KEY.keys())

def normalize_columns(df):
    df.columns = [COLUMN_ALIASES.get(col.strip(), col.strip()) for col in df.columns]
    return df

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try: 
                return json.load(f)
            except json.JSONDecodeError: 
                return {}
    return {}

def save_cache(cache_data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=4)

def _normalize_simple_value(x):
    if x is None: 
        return 'nd'
    s = str(x).strip().lower()
    if s in {'+', 'pos', 'positive', 'acid', 'ferment', 'present', 'detected', 'true', 'yes', 'ya'}: 
        return 'positive'
    if s in {'-', 'neg', 'negative', 'absent', 'not detected', 'false', 'no', 'tidak'}: 
        return 'negative'
    if 'variable' in s or 'v+' in s: 
        return 'variable'
    return s or 'nd'

def _parse_range(val):
    if val is None: 
        return None
    if isinstance(val, (int, float)): 
        return (float(val), float(val))
    if isinstance(val, dict):
        mi, ma = val.get('min'), val.get('max')
        return (float(mi), float(ma)) if mi is not None and ma is not None else None
    if isinstance(val, (list, tuple)) and len(val) == 2:
        try: 
            return (float(val[0]), float(val[1]))
        except (ValueError, TypeError): 
            return None
    s = str(val)
    if '-' in s:
        try:
            a, b = s.replace('–', '-').split('-', 1)
            return (float(a.strip()), float(b.strip()))
        except (ValueError, TypeError): 
            return None
    try: 
        return (float(s), float(s))
    except (ValueError, TypeError): 
        return None

def extract_parameter_value(strain_json, param):
    """
    PERBAIKAN: Extract parameter value dengan debugging yang lebih baik
    """
    paths = PARAM_TO_BACDIVE_KEY.get(param, [])
    
    # KHUSUS: Gram stain detection dari phylum
    if param == 'Gram_stain':
        try:
            taxonomy = strain_json.get("Name and taxonomic classification", {})
            phylum = taxonomy.get("phylum", "")
            if phylum:
                phylum_lower = phylum.lower()
                if any(term in phylum_lower for term in ['firmicutes', 'bacillota', 'actinobacteria', 'actinomycetes']):
                    return 'positive'
                elif any(term in phylum_lower for term in ['proteobacteria', 'bacteroidetes']):
                    return 'negative'
        except Exception:
            pass
    
    # KHUSUS: Temperature dari culture conditions
    if param == 'Temperature_range':
        try:
            culture_conditions = strain_json.get("Culture and growth conditions", {})
            if culture_conditions:
                temp_data = culture_conditions.get("culture temp")
                if temp_data and isinstance(temp_data, dict):
                    # Cek apakah ada nilai temperature
                    temp_val = temp_data.get("temperature")
                    if temp_val:
                        return _parse_range(temp_val)
        except Exception:
            pass
    
    # Coba semua path yang mungkin
    for path in paths:
        current = strain_json
        try:
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    # Key tidak ditemukan, coba path berikutnya
                    break
            else:
                # Semua key dalam path ditemukan
                if current and current not in (None, "", [], {}):
                    # Range parameters
                    if param in {'pH_range', 'Temperature_range', 'NaCl_tolerance'}:
                        return _parse_range(current)
                    
                    # Jika list, ambil item pertama yang valid
                    if isinstance(current, list) and current:
                        current = current[0]
                    
                    # Jika dict, cari nilai yang relevan
                    if isinstance(current, dict):
                        # Prioritas key untuk hasil test
                        priority_keys = ['result', 'test result', 'activity', 'growth', 'ability', 'utilization', 'production']
                        for result_key in priority_keys:
                            if result_key in current and current[result_key] is not None:
                                return _normalize_simple_value(current[result_key])
                        
                        # Cari key lain yang bukan metadata
                        for k, v in current.items():
                            if k.lower() not in ['reference', 'method', 'note', 'id', '@ref'] and v is not None:
                                return _normalize_simple_value(v)
                    
                    return _normalize_simple_value(current)
                
        except (KeyError, TypeError, AttributeError):
            continue
    
    return 'N/A' if param not in {'pH_range', 'Temperature_range', 'NaCl_tolerance'} else None

def extract_bacdive_data(strain_json, param_keys):
    """
    PERBAIKAN UTAMA: Extract data dengan debugging yang lebih baik
    Menangani struktur response BacDive yang sebenarnya
    """
    profile = {}
    
    # PERBAIKAN: Menangani struktur response yang sebenarnya
    # Response format: {"results": {"strain_id": {actual_data}}}
    actual_strain_data = strain_json
    
    # Jika ada struktur results, ambil data strain pertama
    if "results" in strain_json and isinstance(strain_json["results"], dict):
        strain_ids = list(strain_json["results"].keys())
        if strain_ids:
            actual_strain_data = strain_json["results"][strain_ids[0]]
    
    try:
        # Extract taxonomy information
        if "Name and taxonomic classification" in actual_strain_data:
            taxonomy = actual_strain_data["Name and taxonomic classification"]
            genus = taxonomy.get("genus", "Unknown")
            species = taxonomy.get("species", "sp.")
            strain_designation = taxonomy.get("strain designation", "")
            
            # Bersihkan nama species dari format HTML italic tags
            if species:
                species = species.replace("<I>", "").replace("</I>", "").replace("<i>", "").replace("</i>", "")
                # Ambil hanya nama species tanpa bagian author
                if "(" in species:
                    species = species.split("(")[0].strip()
                # Ambil bagian kedua dari nama binomial jika ada
                species_parts = species.split()
                if len(species_parts) >= 2:
                    species = species_parts[1]
            
            if strain_designation:
                profile['Nama Bakteri'] = f"{genus} {species} {strain_designation}".strip()
            else:
                profile['Nama Bakteri'] = f"{genus} {species}".strip()
        else:
            # Fallback: coba dari General section
            if "General" in actual_strain_data:
                general = actual_strain_data["General"]
                dsm_number = general.get("DSM-Number", "")
                if dsm_number:
                    profile['Nama Bakteri'] = f"DSM {dsm_number}"
                else:
                    bacdive_id = general.get("BacDive-ID", "")
                    profile['Nama Bakteri'] = f"BacDive {bacdive_id}"
            else:
                profile['Nama Bakteri'] = "Unknown Species"
                
    except (KeyError, TypeError, IndexError) as e:
        print(f"Error extracting taxonomy: {e}")
        profile['Nama Bakteri'] = "Unknown Species"

    # Extract parameters menggunakan data strain yang sebenarnya
    for param in param_keys:
        try:
            profile[param] = extract_parameter_value(actual_strain_data, param)
        except Exception as e:
            print(f"Error extracting {param}: {e}")
            profile[param] = 'N/A' if param not in {'pH_range', 'Temperature_range', 'NaCl_tolerance'} else None
    
    return profile

def fetch_and_cache_profiles_by_taxonomy(session, genus, status_placeholder, log_container):
    """
    PERBAIKAN UTAMA: Menggunakan endpoint BacDive yang benar dan menangani berbagai format response
    """
    cache = load_cache()
    now = time.time()

    # Check cache validity
    if genus in cache and (now - cache[genus].get('timestamp', 0)) < CACHE_DURATION_SECONDS:
        cached_profiles = cache[genus].get('profiles', {})
        if isinstance(cached_profiles, dict) and cached_profiles:
            first_profile = next(iter(cached_profiles.values()), None)
            if isinstance(first_profile, dict) and first_profile.get('Nama Bakteri', 'Unknown') not in ['Unknown sp.', 'Unknown Species', 'Strain count']:
                status_placeholder.text(f"✅ Cache valid ditemukan untuk genus {genus}.")
                log_container.info(f"Menggunakan {len(cached_profiles)} profil dari cache.")
                time.sleep(0.3)
                return cached_profiles
        
        log_container.warning(f"Cache untuk genus {genus} ditemukan tapi tidak valid. Mengambil ulang dari API.")

    # PERBAIKAN UTAMA: Menggunakan endpoint yang sudah terbukti bekerja dari test
    status_placeholder.text(f"⚙ Mencari strain untuk genus {genus}...")
    
    # Gunakan endpoint /taxon/{genus} yang sudah terbukti bekerja
    search_url = f"https://api.bacdive.dsmz.de/taxon/{genus}"
    
    try:
        log_container.info(f"Menggunakan endpoint: {search_url}")
        resp = session.get(search_url, timeout=30)
        resp.raise_for_status()
        
        search_data = resp.json()
        log_container.info(f"Response berhasil dari {search_url}")
        log_container.info(f"Response keys: {list(search_data.keys())}")
        
        # Berdasarkan test hasil, response format adalah: {"count": X, "results": [...]}
        if 'results' in search_data:
            strain_ids = search_data['results']
            total_count = search_data.get('count', len(strain_ids))
            log_container.info(f"Found {len(strain_ids)} strain dalam response (total: {total_count})")
        else:
            log_container.error(f"Unexpected response structure: {search_data}")
            return {}
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            status_placeholder.warning(f"Genus '{genus}' tidak ditemukan di BacDive.")
            log_container.warning(f"404 - Genus {genus} not found in BacDive database")
        else:
            status_placeholder.error(f"HTTP Error {e.response.status_code} saat mencari {genus}")
            log_container.error(f"HTTP {e.response.status_code}: {e}")
        return {}
    except (requests.RequestException, json.JSONDecodeError) as e:
        status_placeholder.error(f"Gagal mencari strain untuk {genus}: {e}")
        log_container.error(f"Search error for {genus}: {e}")
        return {}

    if not strain_ids:
        status_placeholder.warning(f"Tidak ada strain yang ditemukan untuk genus {genus}.")
        log_container.warning(f"Empty results for genus: {genus}")
        return {}

    log_container.info(f"Processing {len(strain_ids)} strain references for genus {genus}")

    profiles = {}
    param_keys = get_param_keys()
    total_ids = len(strain_ids)
    
    # PERBAIKAN: Setiap item di results adalah referensi strain, bukan data lengkap
    # Format typical: {"id": 12345, "url": "https://api.bacdive.dsmz.de/fetch/12345"}
    processed = 0
    max_profiles = 20  # Batasi untuk performa
    
    for i, strain_ref in enumerate(strain_ids[:max_profiles]):
        global_i = i + 1
        
        status_placeholder.text(f"⚙ Mengambil profil {global_i}/{min(total_ids, max_profiles)}...")
        
        try:
            # Strain reference biasanya berupa dict dengan id dan url
            if isinstance(strain_ref, dict):
                strain_id = strain_ref.get('id')
                strain_url = strain_ref.get('url')
                
                if not strain_id:
                    log_container.warning(f"No ID found in strain reference: {strain_ref}")
                    continue
                
                # Gunakan URL langsung jika ada, atau buat URL dari ID
                if strain_url:
                    fetch_url = strain_url
                else:
                    fetch_url = f"https://api.bacdive.dsmz.de/fetch/{strain_id}"

            else:
                # Jika strain_ref langsung berupa ID
                strain_id = strain_ref
                fetch_url = f"https://api.bacdive.dsmz.de/fetch/{strain_id}"
            
            log_container.info(f"Fetching: {fetch_url}")
            
            # Fetch data lengkap strain
            r = session.get(fetch_url, timeout=30)
            r.raise_for_status()
            strain_data = r.json()
            
            # Debug first response structure
            if global_i == 1:
                log_container.info(f"Sample strain data keys: {list(strain_data.keys())}")
            
            # Extract profile data
            clean = extract_bacdive_data(strain_data, param_keys)
            
            if clean.get("Nama Bakteri", "N/A") not in ["Unknown Species", "Unknown sp.", "N/A", "Strain count"]:
                profiles[str(strain_id)] = clean
                log_container.info(f"✅ Extracted: {clean.get('Nama Bakteri', 'Unknown')}")
                processed += 1
            else:
                log_container.warning(f"Could not extract proper species name for strain ID {strain_id}: got '{clean.get('Nama Bakteri', 'N/A')}'")
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                log_container.warning(f"Strain data not found (404) for reference {i}")
            else:
                log_container.error(f"HTTP {e.response.status_code} for strain reference {i}: {e}")
        except (requests.RequestException, json.JSONDecodeError) as e:
            log_container.error(f"Error fetching strain reference {i}: {e}")
        except Exception as e:
            log_container.error(f"Unexpected error processing strain reference {i}: {e}")
        
        time.sleep(0.3)  # Rate limiting yang lebih moderat
    
    # Save to cache
    cache[genus] = {"timestamp": now, "profiles": profiles}
    save_cache(cache)
    
    status_placeholder.text(f"✅ Selesai mengambil data untuk {genus}.")
    log_container.info(f"Successfully cached {len(profiles)} profiles for genus {genus}")
    
    return profiles

def get_single_strain_json(session, genus):
    """
    PERBAIKAN: Mengambil satu contoh JSON dengan endpoint yang terbukti bekerja
    """
    search_url = f"https://api.bacdive.dsmz.de/taxon/{genus}"
    
    try:
        response = session.get(search_url, timeout=30)
        response.raise_for_status()
        search_data = response.json()
        
        # Berdasarkan test hasil, format response: {"count": X, "results": [...]}
        if 'results' not in search_data or not search_data['results']:
            return {"error": f"Tidak ada strain yang ditemukan untuk genus '{genus}'."}
        
        strain_refs = search_data['results']
        
        # Ambil strain pertama
        first_strain_ref = strain_refs[0]
        
        if isinstance(first_strain_ref, dict):
            strain_id = first_strain_ref.get('id')
            strain_url = first_strain_ref.get('url')
            
            if not strain_id:
                return {"error": "Tidak dapat menemukan ID strain dari response pertama."}
            
            # Fetch data lengkap strain
            if strain_url:
                retrieve_url = strain_url
            else:
                retrieve_url = f"https://api.bacdive.dsmz.de/fetch/{strain_id}"

            retrieve_response = session.get(retrieve_url, timeout=30)
            retrieve_response.raise_for_status()
            
            strain_data = retrieve_response.json()
            
            return {
                "bacdive_id": strain_id, 
                "data": strain_data,
                "debug_info": {
                    "total_strains_found": search_data.get('count', len(strain_refs)),
                    "json_structure_keys": list(strain_data.keys())
                }
            }
        else:
            return {"error": f"Format strain reference tidak dikenali: {first_strain_ref}"}
        
    except requests.exceptions.HTTPError as http_err:
        details = http_err.response.text if hasattr(http_err, 'response') and http_err.response else "No details"
        return {"error": f"Error HTTP: {http_err}", "details": details}
    except requests.exceptions.RequestException as e:
        return {"error": f"Error Koneksi: {e}"}
    except json.JSONDecodeError:
        return {"error": "Gagal mem-parsing respons JSON dari server."}

# --- 4. Fungsi Scoring (tidak berubah) ---
def _overlap_ratio(a, b):
    if a is None or b is None: 
        return 0.0
    (a1, a2), (b1, b2) = a, b
    lo = max(min(a1, a2), min(b1, b2))
    hi = min(max(a1, a2), max(b1, b2))
    inter = max(0.0, hi - lo)
    union = (max(a1, a2) - min(a1, a2)) + (max(b2, b1) - min(b1, b1)) - inter
    return inter / union if union > 0 else 0.0

def calculate_weighted_similarity(user_input, bacdive_profile):
    score, max_possible = 0.0, 0.0
    details = []
    normalized_user = {k: _normalize_simple_value(v) for k, v in user_input.items() if str(v).strip() != ''}

    for param, weight in WEIGHTS.items():
        max_possible += weight
        uval_raw = user_input.get(param)
        uval_norm = normalized_user.get(param)
        bval = bacdive_profile.get(param)

        if param in {'pH_range', 'Temperature_range', 'NaCl_tolerance'}:
            urange = _parse_range(uval_raw) if uval_raw and str(uval_raw).strip() not in {'nd', 'n/a'} else None
            brange = bval if isinstance(bval, tuple) else _parse_range(bval)
            
            part = _overlap_ratio(urange, brange)
            score += weight * part
            det_mark = '✅' if part >= 0.75 else ('➖' if part > 0.1 else '❌')
            bval_disp = f"{brange[0]}-{brange[1]}" if brange else 'N/A'
            details.append({"Parameter": param, "Input": uval_raw or 'N/A', "BacDive Match": bval_disp, "Bobot": weight, "Cocok": det_mark})
            continue

        if not uval_norm or uval_norm == 'nd' or bval in {None, 'N/A', 'nd'}:
            details.append({"Parameter": param, "Input": uval_raw or 'N/A', "BacDive Match": bval or 'N/A', "Bobot": weight, "Cocok": "❓"})
            continue

        if bval == 'variable' or uval_norm == 'variable':
            score += weight * 0.5
            mark = '➖'
        else:
            match = (uval_norm == bval)
            if match: 
                score += weight
            mark = '✅' if match else '❌'
        
        details.append({"Parameter": param, "Input": uval_raw or 'N/A', "BacDive Match": bval, "Bobot": weight, "Cocok": mark})

    similarity = (score / max_possible) * 100.0 if max_possible > 0 else 0.0
    return similarity, details