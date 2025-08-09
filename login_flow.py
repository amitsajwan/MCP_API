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

LOGIN_URL = os.getenv("LOGIN_URL") or "http://localhost:8080/app/FA7/1/v1/s2s/keylink/authentication/login"
BANKS_URL = os.getenv("BANKS_URL") or "http://localhost:8080/app/FA7/1/v1/s2s/keylink/banks?module=MAILBOX_OUTBOX"

USERNAME = os.getenv("USER_NAME") or "AmitS"
PASSWORD = os.getenv("PASSWORD") or "test123"
API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "X-API-KEY")
API_KEY_HEADER_VALUE = os.getenv("API_KEY_HEADER_VALUE", "")

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
    credentials = f"{USERNAME}:{PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------
def login_and_get_session():
    cached_token = load_token()
    session = requests.Session()

    if cached_token:
        logging.info("Using cached JSESSIONID...")
        session.cookies.set("JSESSIONID", cached_token)
        return session

    logging.info("Performing Basic Auth login...")

    # First, get initial cookies (pre-login handshake)
    preflight_resp = session.get(LOGIN_URL, verify=False)
    preflight_resp.raise_for_status()
    logging.info(f"Preflight cookies: {session.cookies.get_dict()}")

    headers = {
        "Authorization": get_basic_auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if API_KEY_HEADER_VALUE:
        headers[API_KEY_HEADER_NAME] = API_KEY_HEADER_VALUE

    # Send login request with whatever cookies we got in preflight
    resp = session.post(LOGIN_URL, headers=headers, cookies=session.cookies, verify=False)
    resp.raise_for_status()

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
# Test GET /banks
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    session = login_and_get_session()

    logging.info(f"Testing GET {BANKS_URL}")
    resp = session.get(BANKS_URL, verify=False)
    logging.info(f"Status: {resp.status_code}")
    logging.info(f"Body: {resp.text}")
