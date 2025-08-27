import sys
import argparse
import os
import json

# Menambahkan path proyek agar bisa mengimpor dari direktori lain
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import get_authenticated_session, test_api_connection, validate_credentials
from bacdive_mapper import fetch_and_cache_profiles_by_taxonomy

# --- Kelas Dummy untuk Meniru Elemen Streamlit di Konsol ---
class ConsoleLogger:
    """Meniru st.container() untuk logging di konsol."""
    def info(self, message):
        print(f"[INFO] {message}")

    def warning(self, message):
        print(f"[WARNING] {message}")

    def error(self, message):
        print(f"[ERROR] {message}")

    def success(self, message):
        print(f"[SUCCESS] {message}")

    def json(self, data):
        # Tidak menampilkan JSON lengkap di konsol agar tidak terlalu ramai,
        # cukup beri notifikasi. Data lengkap ada di cache.
        if isinstance(data, dict):
            # Check for BacDive structure
            if "Name and taxonomic classification" in data:
                tax = data["Name and taxonomic classification"]
                genus = tax.get("genus", "Unknown")
                species = tax.get("species", "sp.")
                strain = tax.get("strain designation", "")
                name = f"{genus} {species} {strain}".strip()
                print(f"  -> API Response received for: {name}")
            elif "results" in data and isinstance(data["results"], dict):
                # Handle wrapped response
                first_result = next(iter(data["results"].values()), {})
                if "Name and taxonomic classification" in first_result:
                    tax = first_result["Name and taxonomic classification"]
                    genus = tax.get("genus", "Unknown")
                    species = tax.get("species", "sp.")
                    name = f"{genus} {species}".strip()
                    print(f"  -> API Response received for: {name}")
                else:
                    print(f"  -> API Response received with {len(data['results'])} results")
            else:
                print("  -> API Response received (structure unknown)")
        else:
            print("  -> API Response received")

    def exception(self, exc):
        print(f"[EXCEPTION] {exc}")

class ConsolePlaceholder:
    """Meniru st.empty() untuk status di konsol."""
    def text(self, message):
        # Gunakan carriage return untuk menimpa baris yang sama
        sys.stdout.write(f"\r\033[K{message}")
        sys.stdout.flush()

    def success(self, message):
        print(f"\n[SUCCESS] {message}")

    def warning(self, message):
        print(f"\n[WARNING] {message}")

    def error(self, message):
        print(f"\n[ERROR] {message}")

    def empty(self):
        print()  # New line to clear the current status

# --- Fungsi Utilitas ---
def get_credentials_from_secrets():
    """Membaca kredensial dari file secrets.toml secara manual."""
    secrets_paths = [
        os.path.join(".streamlit", "secrets.toml"),
        "secrets.toml",
        os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml")
    ]
    
    for secrets_path in secrets_paths:
        try:
            if os.path.exists(secrets_path):
                print(f"Mencoba membaca kredensial dari: {secrets_path}")
                with open(secrets_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # Simple TOML parsing for bacdive section
                    lines = content.split('\n')
                    in_bacdive_section = False
                    email, password = None, None
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('[bacdive]'):
                            in_bacdive_section = True
                            continue
                        elif line.startswith('[') and in_bacdive_section:
                            break  # End of bacdive section
                        elif in_bacdive_section and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            if key == 'email':
                                email = value
                            elif key == 'password':
                                password = value
                    
                    if email and password:
                        print("Kredensial berhasil dibaca dari secrets.toml")
                        return email, password
        
        except Exception as e:
            print(f"Error membaca {secrets_path}: {e}")
            continue
    
    print("Error: Tidak dapat membaca kredensial dari secrets.toml")
    print("File secrets.toml harus berisi:")
    print("[bacdive]")
    print('email = "your_email@example.com"')
    print('password = "your_password"')
    return None, None

def get_credentials_from_input():
    """Meminta kredensial dari input pengguna jika tidak ada di secrets.toml."""
    print("\nKredensial tidak ditemukan di secrets.toml")
    print("Masukkan kredensial BacDive Anda:")
    
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    
    # Validate input
    errors = validate_credentials(email, password)
    if errors:
        print("Kredensial tidak valid:")
        for error in errors:
            print(f"  - {error}")
        return None, None
    
    return email, password

def display_cache_stats():
    """Menampilkan statistik cache saat ini."""
    cache_file = "bacdive_cache.json"
    
    if not os.path.exists(cache_file):
        print("Cache file tidak ditemukan.")
        return
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        print(f"\n=== STATISTIK CACHE ===")
        print(f"Total genus dalam cache: {len(cache_data)}")
        
        total_profiles = 0
        for genus, data in cache_data.items():
            profiles_count = len(data.get('profiles', {}))
            total_profiles += profiles_count
            timestamp = data.get('timestamp', 0)
            
            # Convert timestamp to readable format
            import datetime
            readable_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"  - {genus}: {profiles_count} profiles (terakhir update: {readable_time})")
        
        print(f"Total profiles tersimpan: {total_profiles}")
        
    except Exception as e:
        print(f"Error membaca cache: {e}")

def clear_cache(genus=None):
    """Membersihkan cache untuk genus tertentu atau seluruh cache."""
    cache_file = "bacdive_cache.json"
    
    if not os.path.exists(cache_file):
        print("Cache file tidak ditemukan.")
        return
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        if genus:
            if genus in cache_data:
                del cache_data[genus]
                print(f"Cache untuk genus '{genus}' berhasil dihapus.")
            else:
                print(f"Genus '{genus}' tidak ditemukan dalam cache.")
        else:
            cache_data.clear()
            print("Seluruh cache berhasil dihapus.")
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=4)
            
    except Exception as e:
        print(f"Error menghapus cache: {e}")

# --- Fungsi Utama Skrip ---
def main():
    parser = argparse.ArgumentParser(
        description="Utilitas untuk mengambil dan mengelola cache profil BacDive.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Perintah yang tersedia')
    
    # Subcommand: fetch
    fetch_parser = subparsers.add_parser('fetch', help='Mengambil data dari BacDive')
    fetch_parser.add_argument("genera", nargs='+', help="Nama genus yang ingin diambil")
    fetch_parser.add_argument("--force", action="store_true", help="Paksa update meskipun cache masih valid")
    
    # Subcommand: stats
    subparsers.add_parser('stats', help='Menampilkan statistik cache')
    
    # Subcommand: clear
    clear_parser = subparsers.add_parser('clear', help='Membersihkan cache')
    clear_parser.add_argument("--genus", help="Genus spesifik yang akan dihapus dari cache")
    
    # Subcommand: test
    subparsers.add_parser('test', help='Test koneksi ke BacDive API')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Handle different commands
    if args.command == 'stats':
        display_cache_stats()
        return
    
    if args.command == 'clear':
        clear_cache(args.genus)
        return
    
    if args.command == 'test':
        print("Testing koneksi ke BacDive API...")
        results = test_api_connection()
        
        for name, result in results.items():
            endpoint = result['endpoint']
            status = result['status']
            accessible = result['accessible']
            
            if accessible:
                print(f"✅ {endpoint}: {status}")
                if name == "Token Endpoint" and status in [400, 401, 405]:
                    print(f"   (Expected: Endpoint working, credentials not provided)")
            else:
                print(f"❌ {endpoint}: {status}")
                if 'error' in result:
                    print(f"   Error: {result['error']}")
                    
        print(f"\nEndpoint Information:")
        print(f"• API Base: Main BacDive API endpoint")
        print(f"• Token Endpoint: Authentication endpoint (400/401/405 = working)")
        print(f"• Use 'python cache_manager.py fetch <genus>' to test full authentication")
        return
    
    if args.command == 'fetch':
        # Get credentials
        email, password = get_credentials_from_secrets()
        if not email or not password:
            email, password = get_credentials_from_input()
            if not email or not password:
                sys.exit(1)

        print("Menginisialisasi sesi BacDive...")
        session = get_authenticated_session(email, password)
        if not session:
            print("Autentikasi BacDive gagal. Periksa kembali kredensial Anda.")
            sys.exit(1)
        
        print("Sesi berhasil diautentikasi.")
        
        # Siapkan objek dummy pengganti elemen Streamlit
        status_placeholder = ConsolePlaceholder()
        log_container = ConsoleLogger()

        for genus in args.genera:
            print(f"\n{'='*50}")
            print(f"Memulai proses untuk genus: {genus}")
            print(f"{'='*50}")
            
            try:
                profiles = fetch_and_cache_profiles_by_taxonomy(
                    session, genus, status_placeholder, log_container
                )
                
                if profiles:
                    print(f"\n✅ Berhasil mengambil {len(profiles)} profil untuk genus {genus}")
                else:
                    print(f"\n⚠️  Tidak ada profil ditemukan untuk genus {genus}")
                    
            except KeyboardInterrupt:
                print(f"\n❌ Proses dibatalkan oleh pengguna.")
                break
            except Exception as e:
                print(f"\n❌ Error memproses genus {genus}: {e}")
                continue

        print(f"\nProses selesai. File 'bacdive_cache.json' telah diperbarui.")

if __name__ == "__main__":
    main()