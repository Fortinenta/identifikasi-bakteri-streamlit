import requests
import streamlit as st

TOKEN_URL = "https://sso.dsmz.de/auth/realms/dsmz/protocol/openid-connect/token"

def get_authenticated_session(email, password):
    """
    Authenticates with the DSMZ SSO and returns an authenticated requests.Session object.
    """
    data = {
        "grant_type": "password",
        "client_id": "api.bacdive.public", # Corrected client_id
        "username": email,
        "password": password,
    }
    
    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            st.error("Authentication failed: No access token received from BacDive.")
            return None
        
        st.info(f"Access Token: {access_token}") # Added log statement
            
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {access_token}"})
        return session
        
    except requests.exceptions.HTTPError as err:
        st.error(f"HTTP error during authentication: {err}")
        st.error(f"Response body: {err.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error during authentication request: {e}")
        return None
    except ValueError:
        st.error("Failed to decode authentication response from BacDive.")
        st.error(f"Response text: {response.text}")
        return None
