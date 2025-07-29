import streamlit as st
import pandas as pd
from io import BytesIO
from docx import Document
from docx.shared import Inches
from bacdive.client import BacdiveClient

st.set_page_config(
    page_title="🧫 BakteriFinder: Aplikasi Identifikasi Bakteri Otomatis",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def init_bacdive_client():
    client = BacdiveClient("fortadox@gmail.com", "qkz899mv24")
    return client

def identifikasi_bakteri(row_data, database):
    matches = []
    db_cols = [col for col in database.columns if col not in ["Nama_Bakteri", "Deskripsi", "Habitat", "Patogenisitas"]]
    for _, db_row in database.iterrows():
        score = 0
        for column in db_cols:
            if column in row_data and str(row_data[column]).strip() == str(db_row[column]).strip():
                score += 1
        
        confidence = (score / len(db_cols)) * 100
        matches.append((db_row["Nama_Bakteri"], confidence, db_row["Deskripsi"])) 
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches

def generate_full_docx_report(all_samples_data, all_results, bacdive_client):
    document = Document()
    document.add_heading('Laporan Hasil Identifikasi Bakteri - Laporan Lengkap', 0)
    document.add_paragraph(f"Tanggal Analisis: {pd.to_datetime('today').strftime('%d %B %Y')}")
    document.add_paragraph(f"Total Sampel Dianalisis: {len(all_samples_data)}")
    document.add_page_break()

    for index, sample_data in all_samples_data.iterrows():
        sample_id = sample_data['Sampel']
        top_match = all_results[sample_id][0]

        document.add_heading(f'ID Sampel: {sample_id}', level=1)

        document.add_heading('Hasil Uji Biokimia', level=2)
        table_data = sample_data.drop("Sampel").reset_index()
        table_data.columns = ['Uji Biokimia', 'Hasil']
        table = document.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Uji Biokimia'
        hdr_cells[1].text = 'Hasil'
        for _, row in table_data.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text = str(row['Uji Biokimia'])
            row_cells[1].text = str(row['Hasil'])

        document.add_heading('Hasil Identifikasi', level=2)
        p = document.add_paragraph()
        p.add_run('Bakteri Teridentifikasi: ').bold = True
        p.add_run(top_match[0])
        p = document.add_paragraph()
        p.add_run('Tingkat Kepercayaan: ').bold = True
        p.add_run(f"{top_match[1]:.2f}%")
        p = document.add_paragraph()
        p.add_run('Deskripsi Singkat: ').bold = True
        p.add_run(top_match[2])

        # Fetch BacDive info for each sample
        count = bacdive_client.search(taxonomy=top_match[0])
        if count > 0:
            bacdive_info = next(bacdive_client.retrieve(), None)
            if bacdive_info:
                document.add_heading('Informasi Detail dari BacDive', level=2)
                general_info = bacdive_info.get('General', {})
                name_morphology = general_info.get('Name, Type, Strain, Morphology', {})
                culture_growth = general_info.get('Culture and growth conditions', {})

                if name_morphology.get('gram stain'):
                    document.add_paragraph(f"Pewarnaan Gram: {name_morphology['gram stain']}")
                if name_morphology.get('cell shape'):
                    document.add_paragraph(f"Bentuk Sel: {name_morphology['cell shape']}")
                if culture_growth.get('culture temp'):
                    document.add_paragraph(f"Suhu Pertumbuhan: {culture_growth['culture temp']}")
                if culture_growth.get('oxygen tolerance'):
                    document.add_paragraph(f"Toleransi Oksigen: {culture_growth['oxygen tolerance']}")
        
        if index < len(all_samples_data) - 1:
            document.add_page_break()

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer

def main():
    st.title("🧫 BakteriFinder: Aplikasi Identifikasi Bakteri Otomatis")

    client = init_bacdive_client()
    if not client or not client.authenticated:
        st.error("Login otomatis ke BacDive gagal. Periksa kredensial atau koneksi jaringan.")
        st.stop()
    else:
        st.success("Berhasil terhubung ke BacDive API.")

    st.session_state.client = client

    with st.sidebar:
        st.header("Panduan Penggunaan")
        st.info(
            "1. **Upload File**: Gunakan format `.csv` atau `.xlsx`.\n"
            "2. **Mulai Analisis**: Klik tombol 'Identifikasi Bakteri'.\n"
            "3. **Lihat Hasil**: Pilih sampel dari dropdown untuk melihat laporan.\n"
            "4. **Unduh Laporan**: Klik tombol download untuk menyimpan laporan."
        )

    uploaded_file = st.file_uploader("Upload file CSV atau Excel", type=["csv", "xlsx"])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                data = pd.read_csv(uploaded_file)
            else:
                data = pd.read_excel(uploaded_file)
            st.session_state.data = data
            st.write("**Preview Data:**")
            st.dataframe(data.head())
        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca file: {e}")
            st.stop()

    if 'data' in st.session_state and st.button("Identifikasi Bakteri"):
        with st.spinner("Menganalisis semua sampel..."):
            try:
                database = pd.read_excel("database_bakteri.xlsx")
                st.session_state.database = database
            except FileNotFoundError:
                st.error("File 'database_bakteri.xlsx' tidak ditemukan.")
                st.stop()

            all_results = {}
            for index, row in st.session_state.data.iterrows():
                sample_id = row['Sampel']
                top_matches = identifikasi_bakteri(row, st.session_state.database)
                all_results[sample_id] = top_matches
            st.session_state.all_results = all_results

    if 'all_results' in st.session_state:
        st.header("Hasil Identifikasi Keseluruhan")
        summary_df = pd.DataFrame([
            {'Sampel': sample, 'Bakteri Teridentifikasi': results[0][0], 'Tingkat Kepercayaan (%)': f"{results[0][1]:.2f}"}
            for sample, results in st.session_state.all_results.items()
        ])
        st.dataframe(summary_df)

        # --- Download Button for Full Report ---
        with st.spinner("Menyiapkan laporan lengkap untuk diunduh..."):
            docx_buffer = generate_full_docx_report(
                st.session_state.data, 
                st.session_state.all_results, 
                st.session_state.client
            )
            st.download_button(
                label="📥 Download Laporan Lengkap (.docx)",
                data=docx_buffer,
                file_name="Laporan_Identifikasi_Lengkap.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        st.header("Laporan Detail per Sampel")
        selected_sample = st.selectbox("Pilih Sampel untuk melihat detail laporan:", options=st.session_state.data['Sampel'].unique())

        if selected_sample:
            sample_data = st.session_state.data[st.session_state.data['Sampel'] == selected_sample].iloc[0]
            top_match = st.session_state.all_results[selected_sample][0]
            
            st.subheader(f"Preview Laporan untuk Sampel: {selected_sample}")
            st.markdown(f"**Bakteri Teridentifikasi:** {top_match[0]}")
            st.markdown(f"**Tingkat Kepercayaan:** {top_match[1]:.2f}%")
            st.markdown(f"**Deskripsi:** {top_match[2]}")

            st.subheader("Hasil Uji Biokimia")
            st.table(sample_data.drop("Sampel"))

            with st.spinner(f"Mengambil data dari BacDive untuk {top_match[0]}..."):
                count = st.session_state.client.search(taxonomy=top_match[0])
                if count > 0:
                    bacdive_info = next(st.session_state.client.retrieve(), None)
                    if bacdive_info:
                        st.subheader("Informasi Tambahan dari BacDive")
                        st.json(bacdive_info)
                else:
                    st.warning("Tidak ditemukan informasi tambahan di BacDive.")

if __name__ == "__main__":
    main()
