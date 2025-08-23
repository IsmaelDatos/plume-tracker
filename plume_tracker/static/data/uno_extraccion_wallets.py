import requests
import json
import os

BASE_URL = "https://portal-api.plume.org/api/v1/stats/leaderboard"
COUNT_PER_PAGE = 2000
TIMEOUT_SECONDS = 30

OUTPUT_FOLDER = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data2"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "plume_wallets.json")

def obtener_wallets_unicas_y_guardar():
    offset = 0
    wallets_unicas = set()

    while True:
        params = {
            "offset": offset,
            "count": COUNT_PER_PAGE,
            "walletAddress": "undefined",
            "overrideDay1Override": "false",
            "preview": "false",
        }

        respuesta = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
        respuesta.raise_for_status()
        datos_pagina = respuesta.json().get("data", {}).get("leaderboard", [])

        if not datos_pagina:
            break

        for entrada in datos_pagina:
            wallet = entrada.get("walletAddress")
            xp = entrada.get("totalXp", 0)

            if xp == 0:
                datos_pagina = []
                break

            wallets_unicas.add(wallet)

        offset += COUNT_PER_PAGE
        if not datos_pagina:
            break
    wallets_lista = [{"walletAddress": w} for w in wallets_unicas]

    with open(OUTPUT_FILE, "w") as f:
        json.dump(wallets_lista, f, indent=2)

    print(f"✅ Guardadas {len(wallets_unicas):,} wallets en {OUTPUT_FILE}")
    return len(wallets_unicas)

if __name__ == "__main__":
    cantidad_wallets = obtener_wallets_unicas_y_guardar()
    print(f"🔹 Total wallets únicas en leaderboard: {cantidad_wallets:,}")
