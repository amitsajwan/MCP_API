import os
import logging
import ssl
import re
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)

# Environment variables
load_balancer_url = os.getenv("LOAD_BALANCER_URL")
login_alias = os.getenv("LOGIN_ALIAS")
password = os.getenv("ACCESS_CARD_PASSWORD")
login_endpoint = os.getenv("LOGIN_ENDPOINT")
schema_url = os.getenv("SCHEMA_URL")
api_key_header_name = os.getenv("API_KEY_HEADER_NAME", "X-API-KEY")
api_key_header_value = os.getenv("API_KEY_HEADER_VALUE")
http_proxy = os.getenv("HTTP_PROXY")
https_proxy = os.getenv("HTTPS_PROXY")

# Proxy setup
proxies = {
    "http": http_proxy,
    "https": https_proxy
} if http_proxy and https_proxy else None

# Token cache file
TOKEN_CACHE_FILE = "token_cache.txt"

# SSL Adapter
class SSLContextAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)

# Session setup
session = requests.Session()
session.mount("https://", SSLContextAdapter())

# Save/Load token
def save_token(token):
    with open(TOKEN_CACHE_FILE, "w") as f:
        f.write(token)

def load_token():
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            return f.read().strip()
    return None

# Login process
def access_card_login():
    cached_token = load_token()
    if cached_token:
        logging.info("Using cached JSESSIONID.")
        session.headers.update({"Cookie": f"JSESSIONID={cached_token}"})
        return cached_token

    logging.info("Performing login flow...")

    # Step 1: Redirect
    resp = session.get(load_balancer_url, allow_redirects=False, proxies=proxies)
    resp.raise_for_status()
    location = resp.headers.get("Location")
    if not location:
        raise RuntimeError("Missing Location header in redirect.")
    direct_url = location.split("/global")[0]

    # Step 2: Init
    resp = session.get(location, proxies=proxies)
    resp.raise_for_status()

    # Step 3: Alias
    send_user_url = f"{direct_url}/global/login?login&legitimationtype=accessCard&loginalias={login_alias}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = session.post(send_user_url, headers=headers, proxies=proxies)
    resp.raise_for_status()

    # Step 4: Challenge
    if len(password) != 8:
        raise ValueError("ACCESS_CARD_PASSWORD must be exactly 8 characters.")
    challenge_parts = [password[i:i+2] for i in range(0, 8, 2)]
    challenge_payload = (
        f"loginalias_check={login_alias}&lastRequestAuthMethod=authenticate"
        f"&loginMethodSelect=accessCard&response1={challenge_parts[0]}"
        f"&response2={challenge_parts[1]}&response3={challenge_parts[2]}"
        f"&response4={challenge_parts[3]}&submit=Log in"
    )
    challenge_url = f"{direct_url}/global/login?login"
    resp = session.post(challenge_url, headers=headers, data=challenge_payload, proxies=proxies)
    resp.raise_for_status()

    # Step 5: Final login
    application_login_url = f"{direct_url}{schema_url}{login_endpoint}"
    final_headers = {
        "Accept": "application/json",
        api_key_header_name: api_key_header_value
    }
    resp = session.post(application_login_url, headers=final_headers, proxies=proxies)
    resp.raise_for_status()

    print(f"Final login status: {resp.status_code}")
    print(resp.headers)

    # Extract JSESSIONID
    token = None
    if "set-cookie" in resp.headers:
        match = re.search(r'JSESSIONID=([^;]+)', resp.headers["set-cookie"])
        if match:
            token = match.group(1)

    if not token:
        raise RuntimeError("Failed to obtain JSESSIONID.")

    save_token(token)
    session.headers.update({"Cookie": f"JSESSIONID={token}"})
    return token

if __name__ == "__main__":
    token = access_card_login()
    print("Session token:", token)
