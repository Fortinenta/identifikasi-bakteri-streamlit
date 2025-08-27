#!/usr/bin/env python3
"""
Simple test script to verify BacDive API connection and endpoints
Run this before using the main Streamlit app to diagnose issues
"""

import requests
import json
import sys
import os

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import get_authenticated_session, test_api_connection, validate_credentials

def get_credentials():
    """Get credentials from secrets.toml or user input"""
    secrets_paths = [
        os.path.join(".streamlit", "secrets.toml"),
        "secrets.toml"
    ]
    
    for secrets_path in secrets_paths:
        if os.path.exists(secrets_path):
            print(f"Reading credentials from: {secrets_path}")
            try:
                with open(secrets_path, "r") as f:
                    content = f.read()
                    # Simple TOML parsing
                    lines = content.split('\n')
                    in_bacdive = False
                    email = password = None
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('[bacdive]'):
                            in_bacdive = True
                        elif line.startswith('[') and in_bacdive:
                            break
                        elif in_bacdive and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key == 'email':
                                email = value
                            elif key == 'password':
                                password = value
                    
                    if email and password:
                        return email, password
                        
            except Exception as e:
                print(f"Error reading {secrets_path}: {e}")
    
    # If no secrets file, ask for input
    print("\nEnter your BacDive credentials:")
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    
    return email, password

def test_endpoints():
    """Test basic endpoint connectivity"""
    print("=" * 60)
    print("TESTING BASIC ENDPOINT CONNECTIVITY")
    print("=" * 60)
    
    results = test_api_connection()
    
    for name, result in results.items():
        endpoint = result['endpoint']
        status = result['status']
        accessible = result['accessible']
        
        status_symbol = "✅" if accessible else "❌"
        print(f"{status_symbol} {name}: {endpoint}")
        print(f"   Status: {status}")
        
        if 'error' in result:
            print(f"   Error: {result['error']}")
        elif name == "Token Endpoint" and status in [400, 401, 405]:
            print(f"   Note: Expected response - endpoint is working")
        
        print()

def test_authentication():
    """Test authentication with BacDive"""
    print("=" * 60)
    print("TESTING AUTHENTICATION")
    print("=" * 60)
    
    email, password = get_credentials()
    
    # Validate credentials format
    errors = validate_credentials(email, password)
    if errors:
        print("Credential validation errors:")
        for error in errors:
            print(f"  - {error}")
        return None
    
    print(f"Attempting authentication with email: {email}")
    session = get_authenticated_session(email, password)
    
    if session:
        print("✅ Authentication successful!")
        return session
    else:
        print("❌ Authentication failed!")
        return None

def test_api_calls(session):
    """Test actual API calls with authenticated session"""
    print("=" * 60)
    print("TESTING API CALLS")
    print("=" * 60)
    
    # Test different endpoint patterns
    test_endpoints = [
        ("List strains", "https://api.bacdive.dsmz.de/fetch"),
        ("Taxon endpoint", "https://api.bacdive.dsmz.de/taxon"),
        ("Search Bacillus", "https://api.bacdive.dsmz.de/taxon/Bacillus"),
        ("Search Streptococcus", "https://api.bacdive.dsmz.de/taxon/Streptococcus"),
        ("Search Aeromonas", "https://api.bacdive.dsmz.de/taxon/Aeromonas"),
    ]
    
    successful_calls = 0
    
    for name, endpoint in test_endpoints:
        try:
            print(f"\nTesting: {name}")
            print(f"URL: {endpoint}")
            
            response = session.get(endpoint, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Response type: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"   Response keys: {list(data.keys())}")
                    if 'results' in data:
                        results = data['results']
                        print(f"   Results count: {len(results) if isinstance(results, list) else 'N/A'}")
                elif isinstance(data, list):
                    print(f"   Results count: {len(data)}")
                
                successful_calls += 1
                
            elif response.status_code == 404:
                print(f"⚠️  Not found (404) - this might be expected for some genera")
                
            elif response.status_code in [401, 403]:
                print(f"❌ Authentication issue ({response.status_code})")
                
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print(f"\nSummary: {successful_calls}/{len(test_endpoints)} endpoints successful")
    return successful_calls > 0

def main():
    """Main test function"""
    print("BacDive API Connection Test")
    print("=" * 60)
    
    # Step 1: Test basic connectivity
    test_endpoints()
    
    # Step 2: Test authentication
    session = test_authentication()
    if not session:
        print("\nCannot proceed with API tests - authentication failed")
        return False
    
    # Step 3: Test API calls
    success = test_api_calls(session)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTS PASSED - Your BacDive connection should work!")
        print("You can now run your Streamlit application.")
    else:
        print("❌ TESTS FAILED - There are issues with the API connection")
        print("Check the errors above and verify your credentials.")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)