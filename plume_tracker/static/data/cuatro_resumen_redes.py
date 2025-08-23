import json

INPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data2/plume_networks.json"
OUTPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data2/plume_networks_summary.json"

def traverse_wallets(wallet):
    """Recorre recursivamente un árbol de referidos y devuelve lista plana de wallets"""
    wallets = [wallet]
    for child in wallet.get("referredWallets", []):
        wallets.extend(traverse_wallets(child))
    return wallets


def summarize_network(root_wallet):
    """Genera resumen para una red"""
    wallets = traverse_wallets(root_wallet)

    wallet_count = len(wallets)
    total_xp = sum(w.get("totalXp", 0) for w in wallets)
    sybil_count = sum(1 for w in wallets if str(w.get("sybilFlag")).lower() == "true")

    sybil_percent = round((sybil_count / wallet_count) * 100, 2) if wallet_count > 0 else 0.0

    return {
        "rootWalletAddress": root_wallet["walletAddress"],
        "walletCount": wallet_count,
        "totalXp": total_xp,
        "sybilPercent": sybil_percent
    }

def main():
    # Cargar redes
    with open(INPUT_FILE, "r") as f:
        networks = json.load(f)

    summaries = [summarize_network(root) for root in networks]

    summaries.sort(key=lambda x: x["walletCount"], reverse=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(summaries, f, indent=2)

    print(f"✅ Resumen de redes guardado en {OUTPUT_FILE}")
    print(f"🔹 Total redes: {len(summaries)}")


if __name__ == "__main__":
    main()
