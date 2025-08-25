import pandas as pd
import json
import os
import time
import streamlit as st
import requests

# --- 0. Konfigurasi Cache ---
CACHE_FILE = "bacdive_cache.json"
CACHE_DURATION_SECONDS = 24 * 60 * 60  # Cache berlaku selama 24 jam

# --- 1. MAPPING & WEIGHTS ---
COLUMN_ALIASES = {
    "Motilitas": "Motility",
    "Pewarnaan Gram": "Gram_stain",
    "Gram": "Gram_stain",
    "Katalase": "Catalase",
    "Oksidase": "Oxidase",
    "Indol": "Indole",
    "Urease": "Urease",
    "Dnase": "DNase",
    "Gelatin": "Gelatinase",
    "Nitrate Reduction": "Nitrate_reduction",
    "H2S": "H2S_production",
    "Glukosa": "Glucose",
    "Laktosa": "Lactose",
    "Maltosa": "Maltose",
    "Sukrosa": "Sucrose",
    "Manitol": "Mannitol",
    "Sorbitol": "Sorbitol",
    "Xilosa": "Xylose",
    "Arabinosa": "Arabinose",
    "Trehalosa": "Trehalose",
}

PARAM_TO_BACDIVE_KEY = {
    'Gram_stain': [
        ["morphology", "gram stain"],
        ["morphology", "Gram stain"],
        ["morphology", "Gram reaction"]
    ],
    'Motility': [["morphology", "motility"]],
    'Catalase': [
        ["physiology and metabolism", "catalase"],
        ["physiology and metabolism", "enzymes", "catalase"]
    ],
    'Oxidase': [
        ["physiology and metabolism", "oxidase"],
        ["physiology and metabolism", "enzymes", "oxidase"]
    ],
    'Urease': [
        ["physiology and metabolism", "urease"],
        ["physiology and metabolism", "enzymes", "urease"]
    ],
    'DNase': [
        ["physiology and metabolism", "DNase"],
        ["physiology and metabolism", "enzymes", "DNase"]
    ],
    'Gelatinase': [
        ["physiology and metabolism", "gelatinase"],
        ["physiology and metabolism", "enzymes", "gelatinase"]
    ],
    'Nitrate_reduction': [["physiology and metabolism", "nitrate reduction"]],
    'Indole': [["physiology and metabolism", "indole test"]],
    'MR': [["physiology and metabolism", "methyl red test"]],
    'VP': [["physiology and metabolism", "voges proskauer test"]],
    'Citrate': [["physiology and metabolism", "citrate utilization"]],
    'Ornithine_decarboxylase': [["physiology and metabolism", "ornithine decarboxylase"]],
    'Lysine_decarboxylase': [["physiology and metabolism", "lysine decarboxylase"]],
    'Arginine_dihydrolase': [["physiology and metabolism", "arginine dihydrolase"]],
    'H2S_production': [["physiology and metabolism", "H2S production"]],
    'Glucose': [
        ["physiology and metabolism", "glucose utilization"],
        ["physiology and metabolism", "metabolite utilization", "glucose"]
    ],
    'Lactose': [
        ["physiology and metabolism", "lactose utilization"],
        ["physiology and metabolism", "metabolite utilization", "lactose"]
    ],
    'Sucrose': [
        ["physiology and metabolism", "sucrose utilization"],
        ["physiology and metabolism", "metabolite utilization", "sucrose"]
    ],
    'Mannitol': [
        ["physiology and metabolism", "mannitol utilization"],
        ["physiology and metabolism", "metabolite utilization", "mannitol"]
    ],
    'Sorbitol': [
        ["physiology and metabolism", "sorbitol utilization"],
        ["physiology and metabolism", "metabolite utilization", "sorbitol"]
    ],
    'Xylose': [
        ["physiology and metabolism", "xylose utilization"],
        ["physiology and metabolism", "metabolite utilization", "xylose"]
    ],
    'Arabinose': [
        ["physiology and metabolism", "arabinose utilization"],
        ["physiology and metabolism", "metabolite utilization", "arabinose"]
    ],
    'Trehalose': [
        ["physiology and metabolism", "trehalose utilization"],
        ["physiology and metabolism", "metabolite utilization", "trehalose"]
    ],
    'Inositol': [
        ["physiology and metabolism", "inositol utilization"],
        ["physiology and metabolism", "metabolite utilization", "inositol"]
    ],
    'Maltose': [
        ["physiology and metabolism", "maltose utilization"],
        ["physiology and metabolism", "metabolite utilization", "maltose"]
    ],
    'Raffinose': [
        ["physiology and metabolism", "raffinose utilization"],
        ["physiology and metabolism", "metabolite utilization", "raffinose"]
    ],
    'Fructose': [
        ["physiology and metabolism", "fructose utilization"],
        ["physiology and metabolism", "metabolite utilization", "fructose"]
    ],
    'NaCl_tolerance': [["culture and growth conditions", "sodium chloride (NaCl) growth tolerance"]],
    'Temperature_range': [["culture and growth conditions", "temperature range"]],
    'pH_range': [["culture and growth conditions", "pH range"]],
}

WEIGHTS = {
    'Gram_stain': 3, 'Motility': 3, 'Catalase': 3, 'Oxidase': 3, 'Urease': 3, 
    'DNase': 3, 'Gelatinase': 3,
    'Indole': 2, 'MR': 2, 'VP': 2, 'Citrate': 2, 'Lysine_decarboxylase': 2, 
    'Ornithine_decarboxylase': 2, 'Arginine_dihydrolase': 2, 'Nitrate_reduction': 2, 
    'H2S_production': 2,
    'Glucose': 1, 'Lactose': 1, 'Sucrose': 1, 'Mannitol': 1, 'Sorbitol': 1,
    'Xylose': 1, 'Arabinose': 1, 'Trehalose': 1, 'Inositol': 1, 'Maltose': 1,
    'Raffinose': 1, 'Fructose': 1,
    'NaCl_tolerance': 1, 'Temperature_range': 1, 'pH_range': 1
}

def get_param_keys():
    return list(PARAM_TO_BACDIVE_KEY.keys())

def normalize_columns(df):
    new_columns = []
    for col in df.columns:
        col_strip = col.strip()
        if col_strip in COLUMN_ALIASES:
            new_columns.append(COLUMN_ALIASES[col_strip])
        else:
            new_columns.append(col_strip)
    df.columns = new_columns
    return df

# --- 2. FUNGSI-FUNGSI CACHE ---
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

# --- 3. FUNGSI INTERAKSI API & LOGIKA INTI ---
def fetch_and_cache_profiles_by_taxonomy(session, genus, status_placeholder, log_container):
    """Mengambil PROFIL LENGKAP berdasarkan genus menggunakan session requests."""
    cache = load_cache()
    current_time = time.time()

    if genus in cache and (current_time - cache[genus]['timestamp']) < CACHE_DURATION_SECONDS:
        status_placeholder.text(f"✔️ Cache ditemukan untuk genus {genus}. Menggunakan data profil dari cache.")
        log_container.info(f"Menggunakan {len(cache[genus]['profiles'])} profil dari cache untuk genus {genus}.")
        time.sleep(0.5)
        return cache[genus]['profiles']

    status_placeholder.text(f"☁️ Mencari ID strain untuk genus {genus} via API BacDive...")
    search_url = f"https://api.bacdive.dsmz.de/taxon/{genus}"
    log_container.info(f"API Search URL: {search_url}")
    
    try:
        response = session.get(search_url)
        response.raise_for_status()
        search_results = response.json()
        
        # Extract strain_ids directly from the 'results' list
        strain_ids = search_results.get('results', [])

        if not strain_ids: # Check if the list of IDs is empty
            status_placeholder.text(f"Tidak ada strain ditemukan untuk genus {genus}.")
            return {}

        total_ids = len(strain_ids)
        
        # --- Debugging: Fetch and display one single strain JSON ---
        if len(strain_ids) > 0: # Changed condition
            # print(f"strain_ids content: {strain_ids}") # REMOVED FOR DEBUGGING
            first_bacdive_id = strain_ids[0]
            log_container.info(f"Mengambil detail untuk satu ID strain ({first_bacdive_id}) untuk debugging...")
            single_retrieve_url = f"https://api.bacdive.dsmz.de/fetch/{first_bacdive_id}"
            try:
                single_strain_response = session.get(single_retrieve_url)
                single_strain_response.raise_for_status()
                single_strain_data = single_strain_response.json()
                log_container.json(single_strain_data) # Changed to .json() directly
            except requests.exceptions.RequestException as re:
                log_container.error(f"Gagal mengambil data untuk ID strain tunggal {first_bacdive_id}: {re}")
            except ValueError:
                log_container.error(f"Gagal decode JSON untuk ID strain tunggal {first_bacdive_id}. Response: {single_strain_response.text}")
        else: # Added else block for clarity
            log_container.error(f"strain_ids is empty for genus {genus}. Cannot fetch single strain for debugging.")
        # --- End Debugging ---

        log_container.info(f"Ditemukan {total_ids} ID strain untuk genus {genus}. Memulai pengambilan profil lengkap...")

        ids_to_fetch = ";".join(map(str, strain_ids))
        retrieve_url = f"https://api.bacdive.dsmz.de/fetch/{ids_to_fetch}"
        log_container.info(f"API Retrieve URL: {retrieve_url}")
        
        retrieve_response = session.get(retrieve_url)
        retrieve_response.raise_for_status()
        profiles = retrieve_response.json()

        for bacdive_id, strain_data in profiles.items():
            log_container.expander(f"Raw JSON for BacDive ID: {bacdive_id}").json(strain_data)

        cache[genus] = {
            'timestamp': current_time,
            'profiles': profiles
        }
        save_cache(cache)
        
        return profiles

    except requests.exceptions.HTTPError as http_err:
        status_placeholder.error(f"HTTP error saat mencari data untuk {genus}: {http_err}")
        if http_err.response:
            log_container.error(f"Response body: {http_err.response.text}")
        return {}
    except requests.exceptions.RequestException as e:
        status_placeholder.error(f"Terjadi error saat mengambil data untuk {genus}: {e}")
        return {}
    except ValueError:
        status_placeholder.error(f"Gagal decode JSON.")
        if 'response' in locals() and response:
             log_container.error(f"Search Response body: {response.text}")
        if 'retrieve_response' in locals() and retrieve_response:
             log_container.error(f"Retrieve Response body: {retrieve_response.text}")
        return {}


def calculate_weighted_similarity(user_input, bacdive_profile):
    score = 0
    max_possible_score = 0
    comparison_details = []
    
    clean_bacdive_profile = extract_clean_profile(bacdive_profile)

    normalized_user_input = {}
    for param, value in user_input.items():
        if pd.notna(value) and str(value).strip() != '':
            norm_value = str(value).lower().strip()
            if norm_value in ['+', 'positive', 'ya', 'yes', 'acid', 'positif', 'acid production', 'fermentation']:
                normalized_user_input[param] = 'positive'
            elif norm_value in ['-', 'negative', 'tidak', 'no', 'negatif', 'absent', 'not detected']:
                normalized_user_input[param] = 'negative'
            else:
                normalized_user_input[param] = norm_value

    for param, user_val in normalized_user_input.items():
        if param not in WEIGHTS:
            if param not in ["Sample_Name", "Genus"]:
                print(f"[INFO] Kolom '{param}' tidak ada di WEIGHTS, dilewati.")
            continue
        weight = WEIGHTS.get(param, 1)
        max_possible_score += weight
        
        bacdive_val = clean_bacdive_profile.get(param, 'N/A')
        
        is_match = (user_val == str(bacdive_val).lower())
        if is_match:
            score += weight
        comparison_details.append({
            "Parameter": param,
            "Input": user_input.get(param, 'N/A'),
            "BacDive Match": bacdive_val,
            "Bobot": weight,
            "Cocok": "✅" if is_match else "❌"
        })
    if max_possible_score == 0:
        return 0, []
    similarity_percentage = (score / max_possible_score) * 100
    return similarity_percentage, comparison_details

def extract_clean_profile(strain_data):
    profile = {}
    try:
        taxonomy = strain_data['general']['taxonomy']
        species = taxonomy['species']
        subspecies = taxonomy.get('subspecies', '')
        profile['Nama Bakteri'] = f"{taxonomy['genus']} {species} {subspecies}".strip()
    except KeyError:
        profile['Nama Bakteri'] = "Unknown Species"

    for param in get_param_keys():
        if param in PARAM_TO_BACDIVE_KEY:
            paths = PARAM_TO_BACDIVE_KEY[param]
            found_value = None
            for keys in paths:
                value = strain_data
                try:
                    for key in keys:
                        if isinstance(value, list):
                            value = next((item.get(key) for item in value if isinstance(item, dict) and key in item), None)
                        elif isinstance(value, dict):
                            value = value.get(key)
                        else:
                            value = None
                            break
                    if value is not None:
                        found_value = value
                        break
                except (KeyError, TypeError, StopIteration):
                    continue

            if found_value is not None:
                if isinstance(found_value, dict):
                    final_val = found_value.get('ability', found_value.get('activity'))
                    if str(final_val).lower() in ['+', 'positive', 'acid', 'acid production', 'fermentation']:
                         profile[param] = 'positive'
                    elif str(final_val).lower() in ['-', 'negative', 'no', 'absent', 'not detected']:
                         profile[param] = 'negative'
                    else:
                         profile[param] = final_val if final_val else 'N/A'
                else:
                    if str(found_value).lower() in ['+', 'positive', 'acid', 'acid production', 'fermentation']:
                        profile[param] = 'positive'
                    elif str(found_value).lower() in ['-', 'negative', 'no', 'absent', 'not detected']:
                        profile[param] = 'negative'
                    else:
                        profile[param] = found_value if found_value else 'N/A'
            else:
                profile[param] = 'N/A'
        else:
            profile[param] = 'N/A'
    return profile