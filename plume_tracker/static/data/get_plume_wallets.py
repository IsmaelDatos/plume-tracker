import requests
import csv
import os

# Configuración
API_URL = "https://portal-api.plume.org/api/v1/stats/leaderboard"
OUTPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/plume_wallets.csv"
COUNT = 10000  # número de wallets a pedir en cada request

def fetch_wallets():
    offset = 0
    wallets = []

    while True:
        params = {
            "offset": offset,
            "count": COUNT,
            "walletAddress": "undefined",
            "overrideDay1Override": "false",
            "preview": "false"
        }

        response = requests.get(API_URL, params=params, timeout=30)

        if response.status_code != 200:
            print(f"Error en la API: {response.status_code}")
            break

        data = response.json().get("data", {}).get("leaderboard", [])
        if not data:
            break

        stop = False
        for entry in data:
            wallet = entry.get("walletAddress")
            total_xp = entry.get("totalXp", 0)

            if total_xp and total_xp > 0:
                wallets.append(wallet)
            else:
                stop = True
                break

        if stop:
            break

        offset += COUNT

    return wallets

def save_to_csv(wallets):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["walletAddress"])
        for w in wallets:
            writer.writerow([w])

if __name__ == "__main__":
    wallets = fetch_wallets()
    save_to_csv(wallets)
    print(f"Se guardaron {len(wallets)} wallets en {OUTPUT_FILE}")
