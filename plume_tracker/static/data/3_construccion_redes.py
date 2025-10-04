import json
from collections import defaultdict

INPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/2_plume_wallets_enriched.json"
OUTPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/3_plume_networks.json"


def build_wallet_dict(wallets):
    """Crea un índice {walletAddress: wallet} con estructura base"""
    wallet_dict = {}
    for w in wallets:
        wallet = w.copy()
        wallet["referredWallets"] = []
        wallet["referralCount"] = 0
        wallet_dict[wallet["walletAddress"]] = wallet
    return wallet_dict


def build_referral_tree(wallet_dict):
    """Construye relaciones de referidos (árboles)"""
    roots = []

    for wallet in wallet_dict.values():
        parent_addr = wallet.get("referredByUser")
        if parent_addr and parent_addr in wallet_dict:
            wallet_dict[parent_addr]["referredWallets"].append(wallet)
        else:
            roots.append(wallet)

    return roots


def compute_referral_counts(wallet):
    """Recursivamente cuenta los descendientes"""
    count = len(wallet["referredWallets"])
    for child in wallet["referredWallets"]:
        count += compute_referral_counts(child)
    wallet["referralCount"] = count
    return count


def build_networks(wallets):
    """Pipeline completo"""
    wallet_dict = build_wallet_dict(wallets)
    roots = build_referral_tree(wallet_dict)

    for root in roots:
        compute_referral_counts(root)

    return roots


def main():
    with open(INPUT_FILE, "r") as f:
        wallets = json.load(f)

    networks = build_networks(wallets)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(networks, f, indent=2)

    print(f"✅ Redes construidas y guardadas en {OUTPUT_FILE}")
    print(f"🔹 Total redes: {len(networks)}")


if __name__ == "__main__":
    main()
