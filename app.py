import streamlit as st
import pandas as pd
import io
import time
import os
from auth import get_authenticated_session
from bacdive_mapper import (
    fetch_and_cache_profiles_by_taxonomy,
    calculate_weighted_similarity,
    normalize_columns,
    extract_clean_profile
)

# --- 1. Konfigurasi Aplikasi ---
st.set_page_config(
    page_title="🧬 Identifikasi Bakteri (BacDive API)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. Inisialisasi Sesi ---
@st.cache_resource
def init_session():
    try:
        email = st.secrets["bacdive"]["email"]
        password = st.secrets["bacdive"]["password"]
        session = get_authenticated_session(email, password)
        if session:
            st.success("Autentikasi Berhasil!")
            return session
        else:
            st.error("Autentikasi BacDive gagal. Periksa kredensial Anda di secrets.toml.")
            return None
    except KeyError:
        st.error("Kredensial BacDive (email/password) tidak ditemukan di secrets.toml.")
        return None
    except Exception as e:
        st.error(f"Gagal menginisialisasi sesi: {e}")
        return None

# --- 3. Logika Inti ---
def process_sample(session, user_input, log_container):
    """Fungsi utama untuk memproses satu sampel: fetch, cache, dan analisis."""
    genus = user_input.get("Genus")
    if not genus or pd.isna(genus):
        st.warning("Kolom 'Genus' tidak ditemukan atau kosong untuk sampel ini. Sampel dilewati.")
        return []

    status_placeholder = st.empty()
    
    raw_profiles = fetch_and_cache_profiles_by_taxonomy(session, genus, status_placeholder, log_container)
    
    if not raw_profiles:
        status_placeholder.warning(f"Tidak ada profil yang ditemukan untuk genus '{genus}'.")
        time.sleep(3)
        status_placeholder.empty()
        return []
    
    status_placeholder.success(f"Ditemukan {len(raw_profiles)} profil untuk genus '{genus}'. Memulai analisis perbandingan...")
    time.sleep(2)

    identification_results = []
    progress_bar = st.progress(0)
    total_profiles = len(raw_profiles)

    for i, (bacdive_id, bacdive_profile) in enumerate(raw_profiles.items()):
        status_placeholder.text(f"⚙️ Membandingkan dengan profil {i+1} dari {total_profiles} (ID: {bacdive_id})...")
        
        score, details = calculate_weighted_similarity(user_input, bacdive_profile)
        
        if score > 0:
            clean_profile = extract_clean_profile(bacdive_profile)
            identification_results.append({
                "Rank": 0,
                "Nama Bakteri": clean_profile.get("Nama Bakteri", "N/A"),
                "Persentase": score,
                "ID": bacdive_id,
                "details": details
            })
        progress_bar.progress((i + 1) / total_profiles)

    status_placeholder.text("✅ Perbandingan selesai!")
    time.sleep(1)
    status_placeholder.empty()
    progress_bar.empty()
    
    identification_results.sort(key=lambda x: x["Persentase"], reverse=True)
    for i, result in enumerate(identification_results):
        result["Rank"] = i + 1
        
    return identification_results

def fetch_and_display_detailed_profiles(session, genera_list):
    """Mengambil semua profil mentah, menampilkannya dalam tabel detail, dan mengembalikan tabel tersebut."""
    st.header("3. Data Detail dari BacDive")
    st.info("Tabel ini berisi data lengkap yang diambil dari BacDive untuk setiap strain, yang telah diratakan (flattened) dari format JSON aslinya.")

    all_dfs = []
    progress_bar = st.progress(0, text="Mengambil profil untuk semua genus...")

    for i, genus in enumerate(genera_list):
        status_placeholder = st.empty()
        log_container = st.container()
        raw_profiles = {}

        with st.expander(f"Log Fetch untuk Genus: {genus}", expanded=False):
            raw_profiles = fetch_and_cache_profiles_by_taxonomy(session, genus, status_placeholder, st)

        if raw_profiles:
            for bacdive_id, profile_json in raw_profiles.items():
                # Flatten the JSON data
                df_flat = pd.json_normalize(profile_json, sep='_')
                df_flat['bacdive_id'] = bacdive_id
                df_flat['genus_input'] = genus
                all_dfs.append(df_flat)
        
        progress_bar.progress((i + 1) / len(genera_list), text=f"Selesai mengambil profil untuk {genus}")
        status_placeholder.empty()

    progress_bar.empty()
    
    if not all_dfs:
        st.warning("Tidak ada profil yang ditemukan untuk genus yang diberikan.")
        return pd.DataFrame()

    final_df = pd.concat(all_dfs, ignore_index=True)

    cols = ['bacdive_id', 'genus_input'] + [col for col in final_df.columns if col not in ['bacdive_id', 'genus_input']]
    final_df = final_df[cols]

    with st.expander("Tampilkan/Sembunyikan Tabel Data Detail", expanded=True):
        st.dataframe(final_df)
        
        csv_buffer = io.StringIO()
        final_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download Data Detail Lengkap (.csv)",
            data=csv_buffer.getvalue(),
            file_name="bacdive_detailed_data.csv",
            mime="text/csv",
            key="download-detailed-profiles"
        )
    return final_df

# --- 4. Tampilan Aplikasi (UI) ---
def highlight_mismatch(s):
    return ['background-color: #FFCDD2' if v == '❌' else '' for v in s]

def main():
    st.title("🔬 Identifikasi Bakteri Berbasis Genus")
    st.info("Upload file CSV/Excel dengan kolom **Sample_Name** dan **Genus** untuk memulai identifikasi.")

    session = init_session()
    if not session:
        st.stop()

    with st.sidebar:
        st.header("Panduan Penggunaan")
        st.info(
            "1. **Download Template**: Unduh `template_input.csv`.\n"
            "2. **Isi Data**: Masukkan nama sampel, **genus**, dan hasil uji lab.\n"
            "3. **Upload File**: Unggah file yang sudah diisi.\n"
            "4. **Hasil**: Hasil akan muncul secara otomatis per sampel."
        )
        if os.path.exists("template_input.csv"):
            with open("template_input.csv", "r") as f:
                st.download_button(
                    label="📥 Download Template Input",
                    data=f.read(),
                    file_name="template_input.csv",
                    mime="text/csv"
                )

    st.header("1. Upload File Input")
    uploaded_file = st.file_uploader("Unggah file CSV/Excel", type=["csv", "xlsx"])

    if uploaded_file:
        try:
            data = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            data = normalize_columns(data)
            
            st.header("2. Preview Data Input (Setelah Normalisasi)")
            st.dataframe(data)

            unique_genera = data["Genus"].dropna().unique()

            if len(unique_genera) > 0:
                st.info(f"Ditemukan {len(unique_genera)} genus unik di file Anda: **{', '.join(unique_genera)}**.")
                
                fetch_and_display_detailed_profiles(session, unique_genera)

                st.header("4. Hasil Identifikasi per Sampel")
                for index, row in data.iterrows():
                    st.divider()
                    sample_name = row.get("Sample_Name", f"Sampel #{index + 1}")
                    st.subheader(f"▶️ Hasil untuk Sampel: {sample_name}")
                    
                    user_input = row.to_dict()
                    
                    with st.expander(f"Lihat Log Detail Proses Fetch API untuk Sampel: {sample_name}"):
                        log_container = st.container()
                        results = process_sample(session, user_input, log_container)

                    if results:
                        top_result = results[0]
                        st.success(f"**Identifikasi Utama:** `{top_result['Nama Bakteri']}` ({top_result['Persentase']:.2f}% kemiripan)")

                        with st.expander("Lihat Daftar Kandidat & Laporan Detail"):
                            st.subheader("Daftar Kandidat Teratas (Top 10)")
                            results_df = pd.DataFrame(results).head(10)[["Rank", "Nama Bakteri", "Persentase", "ID"]]
                            st.dataframe(results_df)

                            st.subheader("Laporan Perbandingan (vs Kandidat Utama)")
                            report_df = pd.DataFrame(top_result['details'])
                            st.dataframe(report_df.style.apply(highlight_mismatch, subset=['Cocok']))

                            csv_buffer = io.StringIO()
                            results_df.to_csv(csv_buffer, index=False)
                            st.download_button(
                                label=f"📥 Download Kandidat (.csv) untuk {sample_name}",
                                data=csv_buffer.getvalue(),
                                file_name=f"kandidat_{sample_name.replace(' ', '_')}.csv",
                                mime="text/csv",
                                key=f"csv_{index}"
                            )
                    else:
                        st.write(f"Tidak ada hasil yang cocok ditemukan untuk sampel {sample_name}.")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses file: {e}")
            st.exception(e)

if __name__ == "__main__":
    main()