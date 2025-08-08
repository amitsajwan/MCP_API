import requests
import logging
from token_cache import save_token, load_token

logging.basicConfig(level=logging.INFO)

session = requests.Session()
proxies = {}
api_key_header_name = "X-API-KEY"
api_key_header_value = None


def access_card_login(load_balancer_url, login_alias, password):
    """
    Multi-step access card login.
    Uses cached token if available.
    """
    global api_key_header_value

    # Check cache first
    cached_token = load_token()
    if cached_token:
        logging.info("Using cached token.")
        api_key_header_value = cached_token
        return api_key_header_value

    logging.info("Performing login flow...")
    
    # Step 1: Redirect
    resp = session.get(load_balancer_url, allow_redirects=False, proxies=proxies)
    resp.raise_for_status()
    location = resp.headers.get("Location")
    if not location:
        raise RuntimeError("Missing Location header in redirect.")
    direct_url = location.split("/global")[0]

    # Step 2: Init
    resp = session.get(direct_url, proxies=proxies)
    resp.raise_for_status()

    # Step 3: Alias
    send_user_url = f"{direct_url}/global/login?loginInitiationType=accessCard&loginalias={login_alias}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = session.post(send_user_url, headers=headers, data={}, proxies=proxies)
    resp.raise_for_status()

    # Step 4: Challenge
    if len(password) != 8:
        raise ValueError("ACCESS CARD PASSWORD must be exactly 8 characters.")
    challenge_parts = [password[i:i+2] for i in range(0, 8, 2)]
    challenge_payload = (
        f"loginalias_check={login_alias}&lastRequestAuthMethod=authenticate"
        f"&loginMethodSelect=accessCard&response1={challenge_parts[0]}"
        f"&response2={challenge_parts[1]}&response3={challenge_parts[2]}"
        f"&response4={challenge_parts[3]}&Submit=Log in"
    )
    challenge_url = f"{direct_url}/global/login/login"
    resp = session.post(challenge_url, headers=headers, data=challenge_payload, proxies=proxies)
    resp.raise_for_status()

    # Step 5: Final
    application_login_url = f"{direct_url}/api/login"
    final_headers = {"Accept": "application/json"}
    resp = session.post(application_login_url, headers=final_headers, proxies=proxies)
    resp.raise_for_status()

    api_key_header_value = resp.headers.get(api_key_header_name) or resp.json().get("token")
    if not api_key_header_value:
        raise RuntimeError("Failed to obtain API key.")

    # Optional: if your API returns expires_in in seconds
    expires_in = resp.json().get("expires_in") if resp.headers.get("Content-Type") == "application/json" else None
    save_token(api_key_header_value, expires_in)

    logging.info("Login successful, token cached.")
    return api_key_header_value
