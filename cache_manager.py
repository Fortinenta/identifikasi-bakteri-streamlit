import sys
import argparse
import os

# Menambahkan path proyek agar bisa mengimpor dari direktori lain
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bacdive.client import BacdiveClient
from bacdive_mapper import fetch_and_cache_profiles_by_taxonomy

# --- Kelas Dummy untuk Meniru Elemen Streamlit di Konsol ---
class ConsoleLogger:
    """Meniru st.container() untuk logging di konsol."""
    def info(self, message):
        print(f"[INFO] {message}")

    def json(self, data):
        # Tidak menampilkan JSON lengkap di konsol agar tidak terlalu ramai,
        # cukup beri notifikasi. Data lengkap ada di cache.
        if isinstance(data, dict) and data.get("general", {}).get("taxonomy", {}):
            tax = data["general"]["taxonomy"]
            name = f"{tax.get('genus', '')} {tax.get('species', '')}".strip()
            print(f"  -> Response body diterima untuk: {name}")
        else:
            print("  -> Response body diterima.")

    def expander(self, title):
        print(f"\n{title}")
        return self

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class ConsolePlaceholder:
    """Meniru st.empty() untuk status di konsol."""
    def text(self, message):
        # Gunakan carriage return untuk menimpa baris yang sama
        sys.stdout.write(f"\r\033[K{message}") # \033[K membersihkan sisa baris
        sys.stdout.flush()

    def success(self, message):
        print(f"\n[SUCCESS] {message}")

    def warning(self, message):
        print(f"\n[WARNING] {message}")

    def error(self, message):
        print(f"\n[ERROR] {message}")

# --- Fungsi Utama Skrip ---
def get_credentials_from_secrets():
    """Membaca kredensial dari file secrets.toml secara manual."""
    try:
        secrets_path = os.path.join(".streamlit", "secrets.toml")
        with open(secrets_path, "r") as f:
            # Parsing sederhana, mengasumsikan format `key = "value"`
            lines = f.readlines()
            secrets = {}
            for line in lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    secrets[key.strip()] = value.strip().strip('"'')
            return secrets['email'], secrets['password']
    except Exception:
        print("Error: Tidak dapat membaca kredensial dari .streamlit/secrets.toml")
        print("Pastikan file tersebut ada dan berisi email serta password Anda.")
        return None, None

def main():
    parser = argparse.ArgumentParser(
        description="Utilitas untuk mengambil dan menyimpan profil lengkap dari BacDive ke cache lokal.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("genera", nargs='+', help="Satu atau lebih nama genus yang ingin diambil. Contoh: Aeromonas Vibrio")
    args = parser.parse_args()

    email, password = get_credentials_from_secrets()
    if not email or not password:
        sys.exit(1)

    print("Menginisialisasi klien BacDive...")
    client = BacdiveClient(email, password)
    if not client.authenticated:
        print("Autentikasi BacDive gagal. Periksa kembali kredensial Anda.")
        sys.exit(1)
    
    print("Klien berhasil diautentikasi.")
    
    # Siapkan objek dummy pengganti elemen Streamlit
    status_placeholder = ConsolePlaceholder()
    log_container = ConsoleLogger()

    for genus in args.genera:
        print(f"\n=========================================")
        print(f"Memulai proses untuk genus: {genus}")
        print(f"=========================================")
        fetch_and_cache_profiles_by_taxonomy(client, genus, status_placeholder, log_container)
        # Beri baris baru setelah status progress selesai
        print()

    print("\nSemua genus yang diminta telah diproses.")
    print("File 'bacdive_cache.json' telah diperbarui dan siap untuk Anda periksa.")

if __name__ == "__main__":
    main()
