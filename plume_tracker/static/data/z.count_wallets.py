#!/usr/bin/env python3
"""
count_wallets.py

Cuenta walletAddress en 3 archivos JSON y muestra una tabla resumen.

Archivos por defecto (ajusta si es necesario):
- /home/ismael/Desktop/plume-tracker/plume_tracker/static/data/2_plume_wallets_enriched.json
- /home/ismael/Desktop/plume-tracker/plume_tracker/static/data/3_plume_networks.json
- /home/ismael/Desktop/plume-tracker/plume_tracker/static/data/5_wallet_search_sybil.json
- /home/ismael/Desktop/plume-tracker/plume_tracker/static/data/1_plume_wallets.json
- /home/ismael/Desktop/plume-tracker/plume_tracker/static/data/4_plume_networks_summary.json
"""

import json
from pathlib import Path

FILES = {
    "2_plume_wallets_enriched.json": Path("/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/2_plume_wallets_enriched.json"),
    "3_plume_networks.json": Path("/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/3_plume_networks.json"),
    "5_wallet_search_sybil.json": Path("/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/5_wallet_search_sybil.json"),
    "1_plume_wallets.json": Path("/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/1_plume_wallets.json"),
    "4_plume_networks_summary.json": Path("/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/4_plume_networks_summary.json"),
}

def load_json(path):
    """Carga JSON desde path, devolviendo lista (si es array) o None en error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"Warning: {path} no contiene un array JSON en el nivel superior. Encontrado: {type(data)}")
        return data
    except FileNotFoundError:
        print(f"Error: archivo no encontrado: {path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: JSON inválido en {path}: {e}")
        return None

def analyze_list(data):
    """Devuelve (total_items, items_with_walletAddress, unique_wallet_count)."""
    if not isinstance(data, list):
        return (0, 0, 0)
    total = len(data)
    addrs = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # Revisa ambas posibles claves
        for key in ("walletAddress", "rootWalletAddress"):
            if key in item and item[key] not in (None, ""):
                addrs.append(item[key])
    unique = len(set(addrs))
    with_key = len(addrs)
    return (total, with_key, unique)

def print_table(rows):
    """Imprime tabla bonita sin dependencias externas."""
    headers = ["archivo", "total_objetos", "objetos_con_walletAddress", "walletAddress_unicas"]
    col_widths = [max(len(str(r[i])) for r in ([headers] + rows)) for i in range(len(headers))]
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(sep)
    for r in rows:
        print(" | ".join(str(r[i]).ljust(col_widths[i]) for i in range(len(r))))

def main():
    rows = []
    for name, path in FILES.items():
        data = load_json(path)
        if data is None:
            rows.append((name, "ERROR", "ERROR", "ERROR"))
            continue
        total, with_key, unique = analyze_list(data)
        rows.append((name, total, with_key, unique))

    print("\nResumen de walletAddress por archivo:\n")
    print_table(rows)
    print("\nNotas:")
    print("- 'total_objetos' = número de elementos en el array JSON de nivel superior.")
    print("- 'objetos_con_walletAddress' = cuántos elementos contienen la clave 'walletAddress' o 'rootWalletAddress' y no están vacíos.")
    print("- 'walletAddress_unicas' = cuentas únicas de direcciones encontradas en ese archivo.\n")

if __name__ == "__main__":
    main()
