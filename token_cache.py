import os, json, time

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".token_cache.json")

def save_token(token: str, expires_in: int = None):
    """
    Save token and optional expiration time (epoch seconds).
    """
    data = {"token": token}
    if expires_in:
        data["expires_at"] = int(time.time()) + expires_in
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def load_token():
    """
    Load token from cache if valid.
    """
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        if "expires_at" in data and time.time() >= data["expires_at"]:
            return None
        return data.get("token")
    except Exception:
        return None

def clear_token():
    """
    Remove token cache file.
    """
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
