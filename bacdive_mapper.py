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
    return list(WEIGHTS.keys())

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
        return 'N/A'
    s = str(x).strip().lower()
    if s in {'+', 'pos', 'positive', 'acid', 'ferment', 'present', 'detected', 'true', 'yes', 'ya'}: 
        return 'positive'
    if s in {'-', 'neg', 'negative', 'absent', 'not detected', 'false', 'no', 'tidak'}: 
        return 'negative'
    if 'variable' in s or 'v+' in s or '+/-' in s: 
        return 'variable'
    return s or 'N/A'

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
    PERBAIKAN UTAMA: Extract parameter berdasarkan struktur JSON BacDive yang sebenarnya
    Menggunakan data dari response_14711.json sebagai referensi
    """
    
    # GRAM STAIN - dari cell morphology
    if param == 'Gram_stain':
        try:
            morphology = strain_json.get("Morphology", {})
            if isinstance(morphology, dict):
                cell_morphology = morphology.get("cell morphology", {})
                if isinstance(cell_morphology, dict):
                    gram_stain = cell_morphology.get("gram stain")
                    if gram_stain:
                        return _normalize_simple_value(gram_stain)
                        
            # Fallback: dari phylum inference
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
            
    # MOTILITY - dari cell morphology
    elif param == 'Motility':
        try:
            morphology = strain_json.get("Morphology", {})
            if isinstance(morphology, dict):
                cell_morphology = morphology.get("cell morphology", {})
                if isinstance(cell_morphology, dict):
                    motility = cell_morphology.get("motility")
                    if motility == "no":
                        return 'negative'
                    elif motility == "yes":
                        return 'positive'
        except Exception:
            pass
    
    # ENZYMES - dari enzymes section
    elif param in ['Catalase', 'Oxidase', 'Urease', 'DNase']:
        try:
            physiology = strain_json.get("Physiology and metabolism", {})
            if isinstance(physiology, dict):
                enzymes = physiology.get("enzymes", [])
                if isinstance(enzymes, list):
                    enzyme_name_map = {
                        'Catalase': 'catalase',
                        'Oxidase': 'oxidase', 
                        'Urease': 'urease',
                        'DNase': 'DNase'
                    }
                    target_enzyme = enzyme_name_map.get(param)
                    if target_enzyme:
                        for enzyme_entry in enzymes:
                            if isinstance(enzyme_entry, dict):
                                enzyme_value = enzyme_entry.get("value", "")
                                activity = enzyme_entry.get("activity", "")
                                if target_enzyme.lower() in enzyme_value.lower():
                                    return _normalize_simple_value(activity)
        except Exception:
            pass
    
    # VP TEST - dari metabolite tests
    elif param == 'VP':
        try:
            physiology = strain_json.get("Physiology and metabolism", {})
            if isinstance(physiology, dict):
                metabolite_tests = physiology.get("metabolite tests", [])
                if isinstance(metabolite_tests, list):
                    for test in metabolite_tests:
                        if isinstance(test, dict):
                            if test.get("metabolite") == "acetoin" or "voges-proskauer" in str(test).lower():
                                vp_result = test.get("voges-proskauer-test")
                                if vp_result:
                                    return _normalize_simple_value(vp_result)
        except Exception:
            pass
    
    # NITRATE REDUCTION - dari metabolite utilization
    elif param == 'Nitrate_reduction':
        try:
            physiology = strain_json.get("Physiology and metabolism", {})
            if isinstance(physiology, dict):
                metabolite_utilization = physiology.get("metabolite utilization", [])
                if isinstance(metabolite_utilization, list):
                    for util in metabolite_utilization:
                        if isinstance(util, dict):
                            metabolite = util.get("metabolite", "")
                            if metabolite == "nitrate":
                                activity = util.get("utilization activity")
                                return _normalize_simple_value(activity)
        except Exception:
            pass
    
    # CARBOHYDRATE FERMENTATION - dari API tests atau metabolite utilization
    elif param in ['Glucose', 'Lactose', 'Sucrose', 'Mannitol', 'Sorbitol', 'Xylose', 'Arabinose', 'Trehalose', 'Maltose', 'Raffinose']:
        try:
            physiology = strain_json.get("Physiology and metabolism", {})
            if isinstance(physiology, dict):
                
                # Cek dari API 50CHac terlebih dahulu
                api_50chac = physiology.get("API 50CHac", {})
                if isinstance(api_50chac, dict):
                    # Mapping nama parameter ke kode API
                    api_code_map = {
                        'Glucose': ['GLU', 'glucose'],
                        'Lactose': ['LAC', 'lactose'], 
                        'Sucrose': ['SAC', 'sucrose'],
                        'Mannitol': ['MAN', 'mannitol'],
                        'Sorbitol': ['SOR', 'sorbitol'],
                        'Xylose': ['DXYL', 'LXYL', 'xylose'],
                        'Arabinose': ['LARA', 'DARA', 'arabinose'],
                        'Trehalose': ['TRE', 'trehalose'],
                        'Maltose': ['MAL', 'maltose'],
                        'Raffinose': ['RAF', 'raffinose']
                    }
                    
                    if param in api_code_map:
                        for code in api_code_map[param]:
                            if code in api_50chac:
                                result = api_50chac[code]
                                return _normalize_simple_value(result)
                
                # Cek dari API rID32STR
                api_rid32str = physiology.get("API rID32STR", {})
                if isinstance(api_rid32str, dict):
                    rid_code_map = {
                        'Glucose': ['GLU'],
                        'Lactose': ['LAC'],
                        'Sucrose': ['SAC'],
                        'Mannitol': ['MAN'],
                        'Sorbitol': ['SOR'], 
                        'Trehalose': ['TRE'],
                        'Maltose': ['MAL'],
                        'Raffinose': ['RAF']
                    }
                    
                    if param in rid_code_map:
                        for code in rid_code_map[param]:
                            if code in api_rid32str:
                                result = api_rid32str[code]
                                return _normalize_simple_value(result)
                
                # Cek dari metabolite utilization
                metabolite_utilization = physiology.get("metabolite utilization", [])
                if isinstance(metabolite_utilization, list):
                    metabolite_name_map = {
                        'Glucose': ['D-glucose', 'glucose'],
                        'Lactose': ['lactose'],
                        'Sucrose': ['sucrose'], 
                        'Mannitol': ['D-mannitol', 'mannitol'],
                        'Sorbitol': ['D-sorbitol', 'sorbitol'],
                        'Xylose': ['D-xylose', 'L-xylose', 'xylose'],
                        'Arabinose': ['L-arabinose', 'D-arabinose', 'arabinose'],
                        'Trehalose': ['trehalose'],
                        'Maltose': ['maltose'],
                        'Raffinose': ['raffinose']
                    }
                    
                    if param in metabolite_name_map:
                        for util in metabolite_utilization:
                            if isinstance(util, dict):
                                metabolite = util.get("metabolite", "")
                                for target_name in metabolite_name_map[param]:
                                    if target_name.lower() in metabolite.lower():
                                        activity = util.get("utilization activity")
                                        test_type = util.get("kind of utilization tested", "")
                                        if "builds acid from" in test_type or not test_type:
                                            return _normalize_simple_value(activity)
        except Exception:
            pass
    
    # TEMPERATURE RANGE - dari culture temp
    elif param == 'Temperature_range':
        try:
            culture_conditions = strain_json.get("Culture and growth conditions", {})
            if isinstance(culture_conditions, dict):
                culture_temp = culture_conditions.get("culture temp", [])
                if isinstance(culture_temp, list):
                    temperatures = []
                    for temp_entry in culture_temp:
                        if isinstance(temp_entry, dict):
                            temp_val = temp_entry.get("temperature")
                            growth = temp_entry.get("growth")
                            if temp_val and growth == "positive":
                                if isinstance(temp_val, (int, float)):
                                    temperatures.append(float(temp_val))
                                elif isinstance(temp_val, str) and '-' in temp_val:
                                    # Handle range like "25-41"
                                    try:
                                        parts = temp_val.split('-')
                                        temperatures.extend([float(p.strip()) for p in parts])
                                    except:
                                        pass
                    
                    if temperatures:
                        min_temp = min(temperatures)
                        max_temp = max(temperatures)
                        return (min_temp, max_temp) if min_temp != max_temp else (min_temp, min_temp)
        except Exception:
            pass
    
    # NaCl TOLERANCE - dari halophily
    elif param == 'NaCl_tolerance':
        try:
            physiology = strain_json.get("Physiology and metabolism", {})
            if isinstance(physiology, dict):
                halophily = physiology.get("halophily", {})
                if isinstance(halophily, dict):
                    growth = halophily.get("growth")
                    concentration = halophily.get("concentration", "")
                    if growth == "no" and "6.5" in concentration:
                        return 'negative'
                    elif growth == "yes":
                        return 'positive'
        except Exception:
            pass
    
    # DEFAULT: Parameter tidak ditemukan
    if param in ['Temperature_range', 'pH_range', 'NaCl_tolerance']:
        return None
    else:
        return 'N/A'

def extract_bacdive_data(strain_json, param_keys):
    """
    PERBAIKAN UTAMA: Extract data dengan struktur response BacDive yang sebenarnya
    """
    profile = {}
    
    # Handle nested response structure
    actual_strain_data = strain_json
    if "results" in strain_json and isinstance(strain_json["results"], dict):
        strain_ids = list(strain_json["results"].keys())
        if strain_ids:
            actual_strain_data = strain_json["results"][strain_ids[0]]
    
    try:
        # Extract taxonomy information - IMPROVED
        taxonomy = actual_strain_data.get("Name and taxonomic classification", {})
        
        if taxonomy:
            # Ambil genus
            genus = taxonomy.get("genus", "Unknown")
            
            # Ambil species dengan pembersihan HTML tags
            species = taxonomy.get("species", "sp.")
            if species:
                # Bersihkan HTML italic tags
                species = species.replace("<I>", "").replace("</I>", "").replace("<i>", "").replace("</i>", "")
                # Ambil bagian species tanpa author info
                if "(" in species:
                    species = species.split("(")[0].strip()
                # Ekstrak nama species dari binomial
                species_parts = species.split()
                if len(species_parts) >= 2:
                    species = species_parts[1]
            
            # Coba ambil strain designation dari berbagai tempat
            strain_designation = ""
            
            # Cari di LPSN section terlebih dahulu
            lpsn = taxonomy.get("LPSN", {})
            if isinstance(lpsn, dict):
                full_name = lpsn.get("full scientific name", "")
                if full_name:
                    # Ekstrak strain dari full scientific name
                    parts = full_name.split()
                    if len(parts) > 2:
                        strain_designation = " ".join(parts[2:])
            
            # Jika tidak ada, cari di strain designation
            if not strain_designation:
                strain_designation = taxonomy.get("strain designation", "")
            
            # Jika masih tidak ada, cari di General section
            if not strain_designation:
                general = actual_strain_data.get("General", {})
                if isinstance(general, dict):
                    dsm_number = general.get("DSM-Number")
                    if dsm_number:
                        strain_designation = f"DSM {dsm_number}"
            
            # Buat nama lengkap
            if strain_designation:
                profile['Nama Bakteri'] = f"{genus} {species} {strain_designation}".strip()
            else:
                profile['Nama Bakteri'] = f"{genus} {species}".strip()
        else:
            profile['Nama Bakteri'] = "Unknown Species"
                
    except Exception as e:
        print(f"Error extracting taxonomy: {e}")
        profile['Nama Bakteri'] = "Unknown Species"

    # Extract parameters
    for param in param_keys:
        try:
            profile[param] = extract_parameter_value(actual_strain_data, param)
        except Exception as e:
            print(f"Error extracting {param}: {e}")
            profile[param] = 'N/A' if param not in {'pH_range', 'Temperature_range', 'NaCl_tolerance'} else None
    
    return profile

def fetch_and_cache_profiles_by_taxonomy(session, genus, status_placeholder, log_container=None):
    """
    Fetch profiles by taxonomy. The log_container is now optional to allow for silent fetching.
    """
    cache = load_cache()
    now = time.time()

    # Check cache validity
    if genus in cache and (now - cache[genus].get('timestamp', 0)) < CACHE_DURATION_SECONDS:
        cached_profiles = cache[genus].get('profiles', {})
        if isinstance(cached_profiles, dict) and cached_profiles:
            first_profile = next(iter(cached_profiles.values()), None)
            if isinstance(first_profile, dict) and first_profile.get('Nama Bakteri', 'Unknown') not in ['Unknown sp.', 'Unknown Species', 'Strain count']:
                status_placeholder.text(f"Cache valid ditemukan untuk genus {genus}.")
                if log_container:
                    log_container.info(f"Menggunakan {len(cached_profiles)} profil dari cache.")
                time.sleep(0.3)
                return cached_profiles
        
        if log_container:
            log_container.warning(f"Cache untuk genus {genus} ditemukan tapi tidak valid. Mengambil ulang dari API.")

    status_placeholder.text(f"Mencari strain untuk genus {genus}...")
    search_url = f"https://api.bacdive.dsmz.de/taxon/{genus}"
    
    try:
        if log_container:
            log_container.info(f"Menggunakan endpoint: {search_url}")
        resp = session.get(search_url, timeout=30)
        resp.raise_for_status()
        
        search_data = resp.json()
        if log_container:
            log_container.info(f"Response berhasil dari {search_url}")
        
        if 'results' in search_data:
            strain_ids = search_data['results']
            total_count = search_data.get('count', len(strain_ids))
            if log_container:
                log_container.info(f"Found {len(strain_ids)} strain dalam response (total: {total_count})")
        else:
            if log_container:
                log_container.error(f"Unexpected response structure: {search_data}")
            return {}
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            status_placeholder.warning(f"Genus '{genus}' tidak ditemukan di BacDive.")
            if log_container:
                log_container.warning(f"404 - Genus {genus} not found in BacDive database")
        else:
            status_placeholder.error(f"HTTP Error {e.response.status_code} saat mencari {genus}")
            if log_container:
                log_container.error(f"HTTP {e.response.status_code}: {e}")
        return {}
    except (requests.RequestException, json.JSONDecodeError) as e:
        status_placeholder.error(f"Gagal mencari strain untuk {genus}: {e}")
        if log_container:
            log_container.error(f"Search error for {genus}: {e}")
        return {}

    if not strain_ids:
        status_placeholder.warning(f"Tidak ada strain yang ditemukan untuk genus {genus}.")
        if log_container:
            log_container.warning(f"Empty results for genus: {genus}")
        return {}

    if log_container:
        log_container.info(f"Processing {len(strain_ids)} strain references for genus {genus}")

    profiles = {}
    param_keys = get_param_keys()
    total_ids = len(strain_ids)
    processed = 0
    # Batasan max_profiles dihapus untuk mengambil semua data
    
    for i, strain_ref in enumerate(strain_ids):
        global_i = i + 1
        
        status_placeholder.text(f"Mengambil profil {global_i}/{total_ids}...")
        
        try:
            if isinstance(strain_ref, dict):
                strain_id = strain_ref.get('id')
                strain_url = strain_ref.get('url')
                
                if not strain_id:
                    if log_container:
                        log_container.warning(f"No ID found in strain reference: {strain_ref}")
                    continue
                
                if strain_url:
                    fetch_url = strain_url
                else:
                    fetch_url = f"https://api.bacdive.dsmz.de/fetch/{strain_id}"

            else:
                strain_id = strain_ref
                fetch_url = f"https://api.bacdive.dsmz.de/fetch/{strain_id}"
            
            if log_container:
                log_container.info(f"Fetching: {fetch_url}")
            
            r = session.get(fetch_url, timeout=30)
            r.raise_for_status()
            strain_data = r.json()
            
            if global_i == 1 and log_container:
                log_container.info(f"Sample strain data keys: {list(strain_data.keys())}")
            
            clean = extract_bacdive_data(strain_data, param_keys)
            
            if clean.get("Nama Bakteri", "N/A") not in ["Unknown Species", "Unknown sp.", "N/A", "Strain count"]:
                profiles[str(strain_id)] = clean
                if log_container:
                    log_container.info(f"Extracted: {clean.get('Nama Bakteri', 'Unknown')}")
                processed += 1
            else:
                if log_container:
                    log_container.warning(f"Could not extract proper species name for strain ID {strain_id}: got '{clean.get('Nama Bakteri', 'N/A')}'")
                
        except requests.exceptions.HTTPError as e:
            if log_container:
                if e.response.status_code == 404:
                    log_container.warning(f"Strain data not found (404) for reference {i}")
                else:
                    log_container.error(f"HTTP {e.response.status_code} for strain reference {i}: {e}")
        except (requests.RequestException, json.JSONDecodeError) as e:
            if log_container:
                log_container.error(f"Error fetching strain reference {i}: {e}")
        except Exception as e:
            if log_container:
                log_container.error(f"Unexpected error processing strain reference {i}: {e}")
        
        time.sleep(0.3)
    
    # Save to cache
    cache[genus] = {"timestamp": now, "profiles": profiles}
    save_cache(cache)
    
    status_placeholder.text(f"Selesai mengambil data untuk {genus}.")
    if log_container:
        log_container.info(f"Successfully cached {len(profiles)} profiles for genus {genus}")
    
    return profiles

def get_single_strain_json(session, genus):
    """
    Mengambil satu contoh JSON - tidak berubah dari versi sebelumnya
    """
    search_url = f"https://api.bacdive.dsmz.de/taxon/{genus}"
    
    try:
        response = session.get(search_url, timeout=30)
        response.raise_for_status()
        search_data = response.json()
        
        if 'results' not in search_data or not search_data['results']:
            return {"error": f"Tidak ada strain yang ditemukan untuk genus '{genus}'."}
        
        strain_refs = search_data['results']
        first_strain_ref = strain_refs[0]
        
        if isinstance(first_strain_ref, dict):
            strain_id = first_strain_ref.get('id')
            strain_url = first_strain_ref.get('url')
            
            if not strain_id:
                return {"error": "Tidak dapat menemukan ID strain dari response pertama."}
            
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
    union = max(max(a1, a2), max(b1, b2)) - min(min(a1, a2), min(b1, b2))
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
            urange = _parse_range(uval_raw) if uval_raw and str(uval_raw).strip() not in {'N/A', 'n/a'} else None
            brange = bval if isinstance(bval, tuple) else _parse_range(bval)
            part = _overlap_ratio(urange, brange)
            score += weight * part
            det_mark = '✅' if part >= 0.75 else ('➖' if part > 0.1 else '❌')
            bval_disp = f"{brange[0]}-{brange[1]}" if brange else 'N/A'
            details.append({"Parameter": param, "Input": uval_raw or 'N/A', "BacDive Match": bval_disp, "Bobot": weight, "Cocok": det_mark})
            continue

        if not uval_norm or uval_norm == 'N/A' or bval in {None, 'N/A'}:
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