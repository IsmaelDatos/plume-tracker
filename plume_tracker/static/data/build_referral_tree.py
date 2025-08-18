import json
import os

# Archivos
INPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/plume_wallets_details.json"
OUTPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/plume_wallets_with_referrals.json"

def main():
    # Cargar todas las wallets
    with open(INPUT_FILE, "r") as f:
        wallets = json.load(f)

    # Crear un diccionario rápido de walletAddress a wallet para búsqueda
    wallet_dict = {w["walletAddress"]: w for w in wallets}

    # Recorrer cada wallet
    for w in wallets:
        referredWallets = []

        # Si no tiene referidos, dejamos el arreglo vacío
        if w.get("referrals", 0) == 0:
            w["referredWallets"] = referredWallets
            continue

        # Buscar todas las wallets que tienen "referredByUser" igual a la wallet actual
        for other in wallets:
            if other.get("referredByUser") == w["walletAddress"]:
                referredWallets.append(other["walletAddress"])

        w["referredWallets"] = referredWallets

    # Guardar el JSON actualizado
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(wallets, f, indent=2)

    print(f"✅ Se actualizaron {len(wallets)} wallets con sus referredWallets en {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
