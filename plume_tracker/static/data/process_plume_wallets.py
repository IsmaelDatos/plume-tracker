import requests
import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuración
INPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/plume_wallets.csv"
OUTPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/plume_wallets_details.json"
API_URL = "https://portal-api.plume.org/api/v1/stats/wallet"

MAX_WORKERS = 50  # número de hilos en paralelo (ajustable)

def load_wallets():
    wallets = []
    with open(INPUT_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wallets.append(row["walletAddress"])
    return wallets

def fetch_wallet_details(wallet):
    try:
        url = f"{API_URL}?walletAddress={wallet}"
        response = requests.get(url, timeout=20)

        if response.status_code != 200:
            return None

        data = response.json().get("data", {}).get("stats", {})
        if not data:
            return None

        referred_by_user = data.get("referredByUser")
        if referred_by_user and isinstance(referred_by_user, dict):
            referred_by_user = referred_by_user.get("walletAddress")
        else:
            referred_by_user = None

        return {
            "walletAddress": data.get("walletAddress"),
            "totalXp": data.get("totalXp"),
            "referrals": data.get("referrals"),
            "referredByUser": referred_by_user
        }

    except Exception:
        return None

def main():
    wallets = load_wallets()
    print(f"Procesando {len(wallets)} wallets en paralelo con {MAX_WORKERS} hilos...")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_wallet = {executor.submit(fetch_wallet_details, w): w for w in wallets}
        
        for i, future in enumerate(as_completed(future_to_wallet), 1):
            data = future.result()
            if data:
                results.append(data)
            if i % 1000 == 0:
                print(f"{i} wallets procesadas...")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Se guardaron {len(results)} wallets en {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
