import requests
import logging
from token_cache import save_token, load_token

logging.basicConfig(level=logging.INFO)

session = requests.Session()
proxies = {}
api_key_header_name = "X-API-KEY"
api_key_header_value = None

import requests

def access_card_login():
    try:
        session = requests.Session()

        # Step 1: Redirect handling
        response = session.get(load_balancer_url, allow_redirects=False, proxies=proxies)
        response.raise_for_status()
        location = response.headers.get("Location")
        if not location:
            raise ValueError("Missing Location header in redirect response.")
        direct_url = location.split("/global")[0]

        # Step 2: Initial GET
        response_init = session.get(direct_url, proxies=proxies)
        response_init.raise_for_status()

        # Step 3: Send user
        send_user_url = f"{direct_url}/global/loginLogin&legitimationtype=accessCard&loginalias={login_alias}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response_user = session.post(send_user_url, headers=headers, data={}, proxies=proxies)
        response_user.raise_for_status()

        # Step 4: Challenge step
        if len(password) != 8:
            raise ValueError("ACCESS_CARD_PASSWORD must be exactly 8 characters.")
        challenge_parts = [password[i:i+2] for i in range(0, 8, 2)]
        challenge_payload = (
            f"loginalias_check={login_alias}&lastRequestAuthMethod=authenticate"
            f"&loginMethodSelect=accessCard&response1={challenge_parts[0]}"
            f"&response2={challenge_parts[1]}&response3={challenge_parts[2]}"
            f"&response4={challenge_parts[3]}&submit=Log in"
        )
        challenge_url = f"{direct_url}/global/login/login"
        response_challenge = session.post(challenge_url, headers=headers, data=challenge_payload, proxies=proxies)
        response_challenge.raise_for_status()

        # Step 5: Final application login
        application_login_url = f"{direct_url}/{schema_url}{login_endpoint}"
        final_headers = {
            "Accept": "application/json",
            api_key_header_name: api_key_header_value
        }
        response_final = session.post(application_login_url, headers=final_headers, proxies=proxies)
        response_final.raise_for_status()

        print(f"Final login status: {response_final.status_code}")
        print(f"Response body: {response_final.text}")

        # Step 6: Extract and show JSESSIONID
        jsessionid = session.cookies.get("JSESSIONID")
        if jsessionid:
            print(f"JSESSIONID: {jsessionid}")
        else:
            print("No JSESSIONID found in cookies.")

        return session

    except Exception as e:
        print(f"Login failed: {e}")
        return None
