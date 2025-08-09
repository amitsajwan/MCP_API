import os
import base64
import re
import logging
import requests
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Load configuration
# -----------------------------------------------------------------------------
load_dotenv()

LOGIN_URL = os.getenv("LOGIN_URL")  # e.g. http://localhost:8081/api/v1/keylink/authentication/login
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "X-API-KEY")  # optional, if needed
API_KEY_HEADER_VALUE = os.getenv("API_KEY_HEADER_VALUE", "")          # optional, if needed

TOKEN_CACHE_FILE = "token_cache.txt"

logging.basicConfig(level=logging.INFO)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def save_token(token):
    with open(TOKEN_CACHE_FILE, "w") as f:
        f.write(token)

def load_token():
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            return f.read().strip()
    return None

def get_basic_auth_header():
    """Mimics Java getBasicAuthorizationHeaderValue()"""
    credentials = f"{USERNAME}:{PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

# -----------------------------------------------------------------------------
# Login function
# -----------------------------------------------------------------------------
def login_and_get_session():
    cached_token = load_token()
    session = requests.Session()

    if cached_token:
        logging.info("Using cached JSESSIONID...")
        session.cookies.set("JSESSIONID", cached_token)
        return session

    logging.info("Performing Basic Auth login...")

    headers = {
        "Authorization": get_basic_auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if API_KEY_HEADER_VALUE:
        headers[API_KEY_HEADER_NAME] = API_KEY_HEADER_VALUE

    resp = session.post(LOGIN_URL, headers=headers, verify=False)
    resp.raise_for_status()

    # Extract JSESSIONID from Set-Cookie
    token = None
    if "set-cookie" in resp.headers:
        match = re.search(r'JSESSIONID=([^;]+)', resp.headers["set-cookie"])
        if match:
            token = match.group(1)

    if not token:
        raise RuntimeError("No JSESSIONID found in login response.")

    save_token(token)
    logging.info(f"JSESSIONID obtained: {token}")
    return session

# -----------------------------------------------------------------------------
# Example usage
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    session = login_and_get_session()

    # Example authenticated call:
    url = os.getenv("TEST_API_URL")  # e.g. http://localhost:8081/api/v1/keylink/someendpoint
    if url:
        resp = session.get(url, verify=False)
        print("Response status:", resp.status_code)
        print("Response body:", resp.text)
    else:
        print("Session ready. Use 'session' object for further requests.")
