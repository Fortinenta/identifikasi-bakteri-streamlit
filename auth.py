import requests
import streamlit as st
import time

TOKEN_URL = "https://sso.dsmz.de/auth/realms/dsmz/protocol/openid-connect/token"

def get_authenticated_session(email, password, max_retries=3):
    """
    Authenticates with the DSMZ SSO and returns an authenticated requests.Session object.
    Added retry mechanism and better error handling.
    """
    data = {
        "grant_type": "password",
        "client_id": "api.bacdive.public",
        "username": email,
        "password": password,
    }
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"Mencoba autentikasi ulang... (percobaan {attempt + 1}/{max_retries})")
                time.sleep(2)  # Wait before retry
            
            response = requests.post(TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                print("Authentication failed: No access token received from BacDive.")
                return None
            
            # Create authenticated session
            session = requests.Session()
            session.headers.update({"Authorization": f"Bearer {access_token}"})
            
            # Test the session with a simple API call - PERBAIKAN: endpoint yang benar
            test_endpoints = [
                "https://api.bacdive.dsmz.de/",
                "https://api.bacdive.dsmz.de/fetch",
                "https://api.bacdive.dsmz.de/taxon"
            ]
            
            session_validated = False
            for test_endpoint in test_endpoints:
                try:
                    test_response = session.get(test_endpoint, timeout=10)
                    if test_response.status_code in [200, 404]:  # 404 juga OK untuk beberapa endpoint
                        print(f"✅ Autentikasi BacDive berhasil! (tested with {test_endpoint})")
                        session_validated = True
                        break
                    else:
                        print(f"Test endpoint {test_endpoint} returned {test_response.status_code}")
                except Exception as e:
                    print(f"Test endpoint {test_endpoint} failed: {e}")
                    continue
            
            if session_validated:
                return session
            else:
                print("Token diterima tapi tidak dapat memvalidasi akses API.")
                
        except requests.exceptions.HTTPError as err:
            last_error = f"HTTP error during authentication: {err}"
            if err.response.status_code == 401:
                print("❌ Kredensial salah. Periksa email dan password Anda.")
                return None  # Don't retry for auth errors
            elif err.response.status_code >= 500:
                print(f"Server error (attempt {attempt + 1}): {err}")
            else:
                print(f"HTTP error: {err}")
                if hasattr(err, 'response') and err.response:
                    print(f"Response body: {err.response.text}")
                    
        except requests.exceptions.Timeout:
            last_error = "Request timeout during authentication"
            print(f"Request timeout (attempt {attempt + 1}). Mencoba lagi...")
            
        except requests.exceptions.ConnectionError:
            last_error = "Connection error during authentication"
            print(f"Connection error (attempt {attempt + 1}). Periksa koneksi internet Anda.")
            
        except requests.exceptions.RequestException as e:
            last_error = f"Error during authentication request: {e}"
            print(f"Request error: {e}")
            
        except ValueError as e:
            last_error = "Failed to decode authentication response from BacDive"
            print("Failed to decode authentication response from BacDive.")
            if 'response' in locals():
                print(f"Response text: {response.text}")
            
        except Exception as e:
            last_error = f"Unexpected error during authentication: {e}"
            print(f"Unexpected error: {e}")
    
    # All retries failed
    print(f"❌ Autentikasi gagal setelah {max_retries} percobaan.")
    if last_error:
        print(f"Error terakhir: {last_error}")
    
    return None

def test_api_connection():
    """
    Test basic connectivity to BacDive API endpoints.
    Returns dict with proper structure for cache_manager.py
    """
    endpoints_to_test = [
        ("API Base", "https://api.bacdive.dsmz.de/"),
        ("Token Endpoint", "https://sso.dsmz.de/auth/realms/dsmz/protocol/openid-connect/token"),
        ("Strain Endpoint", "https://api.bacdive.dsmz.de/fetch"),
        ("Taxon Endpoint", "https://api.bacdive.dsmz.de/taxon")
    ]
    
    results = {}
    
    for name, endpoint in endpoints_to_test:
        try:
            # Use GET for most endpoints, POST for token endpoint
            if "token" in endpoint.lower():
                # POST request without credentials should return 400/401 (expected)
                response = requests.post(endpoint, data={}, timeout=10)
            else:
                response = requests.get(endpoint, timeout=10)
            
            # For token endpoint, 400/401/405 are expected responses (endpoint is working)
            if "token" in endpoint.lower():
                accessible = response.status_code in [400, 401, 405]
            else:
                # For API endpoints, 200 (success) or 404 (not found but accessible) are good
                # 401/403 means authentication required but endpoint exists
                accessible = response.status_code in [200, 401, 403, 404]
            
            results[name] = {
                'endpoint': endpoint,
                'status': response.status_code,
                'accessible': accessible
            }
            
        except requests.exceptions.RequestException as e:
            results[name] = {
                'endpoint': endpoint,
                'status': 'Error',
                'accessible': False,
                'error': str(e)
            }
    
    return results

def validate_credentials(email, password):
    """
    Validate email and password format before attempting authentication.
    """
    errors = []
    
    if not email or not email.strip():
        errors.append("Email tidak boleh kosong")
    elif '@' not in email:
        errors.append("Format email tidak valid")
    
    if not password or not password.strip():
        errors.append("Password tidak boleh kosong")
    elif len(password) < 6:
        errors.append("Password terlalu pendek (minimal 6 karakter)")
    
    return errors