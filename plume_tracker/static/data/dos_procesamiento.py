import aiohttp
import asyncio
import json
import os
import random
import time
from datetime import datetime

INPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data2/plume_wallets.json"
OUTPUT_FILE = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data2/plume_wallets_enriched.json"

PLUME_STATS_API = "https://portal-api.plume.org/api/v1/stats/wallet"
PLUME_EXPLORER_API = "https://explorer.plume.org/api"

MAX_CONCURRENT_REQUESTS = 300
BATCH_SIZE = 500
RETRY_LIMIT = 5
RETRY_BACKOFF = [1, 2, 5, 10] 


async def fetch_json(session, url, params=None, retries=0):
    """Realiza request con reintentos y backoff."""
    try:
        async with session.get(url, params=params, timeout=20) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            return await response.json()
    except Exception as e:
        if retries < RETRY_LIMIT:
            wait_time = RETRY_BACKOFF[min(retries, len(RETRY_BACKOFF)-1)]
            print(f"⚠️ Error fetch_json {url}: {e}. Reintentando en {wait_time}s...")
            await asyncio.sleep(wait_time + random.random())
            return await fetch_json(session, url, params, retries + 1)
        else:
            print(f"❌ Error permanente {url}: {e}")
            return None


async def fetch_wallet_stats(session, wallet):
    """Obtiene stats de Plume para una wallet."""
    url = f"{PLUME_STATS_API}?walletAddress={wallet}"
    data = await fetch_json(session, url)
    if not data:
        return None

    stats = data.get("data", {}).get("stats", {})
    if not stats:
        return None

    referred_by_user = stats.get("referredByUser")
    if referred_by_user and isinstance(referred_by_user, dict):
        referred_by_user = referred_by_user.get("walletAddress")
    else:
        referred_by_user = None

    return {
        "walletAddress": stats.get("walletAddress"),
        "totalXp": stats.get("totalXp", 0),
        "referrals": stats.get("referrals", 0),
        "referredByUser": referred_by_user,
        "protectorOfPlumePoints": stats.get("protectorsOfPlumePoints", 0)
    }


async def fetch_transactions(session, wallet):
    """Obtiene transacciones de la wallet desde Explorer."""
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': wallet
    }
    data = await fetch_json(session, PLUME_EXPLORER_API, params=params)
    if data and data.get("message") == "OK":
        return data.get("result", [])
    return []


async def get_activity_stats(session, wallet):
    """Procesa actividad de la wallet (txn y días activos)."""
    transactions = await fetch_transactions(session, wallet)
    if not transactions:
        return {"txn": 0, "activeDays": 0}

    daily_counts = {}
    for tx in transactions:
        try:
            tx_date = datetime.fromtimestamp(int(tx['timeStamp'])).date()
            daily_counts[tx_date] = daily_counts.get(tx_date, 0) + 1
        except:
            continue

    return {
        "txn": len(transactions),
        "activeDays": len(daily_counts)
    }


def evaluate_sybil(stats):
    """Evalúa si una wallet es Sybil, sospechosa o legítima."""
    total_xp = stats.get("totalXp", 0) or 0
    protector = stats.get("protectorOfPlumePoints", 0) or 0
    txn = stats.get("txn", 0)
    active_days = stats.get("activeDays", 0)

    if total_xp == protector or (protector / total_xp > 0.8 if total_xp > 0 else False):
        return "true"
    if total_xp > 0 and 0.4 <= protector / total_xp <= 0.8:
        return "suspicious"
    if protector == 0 and txn == 0 and total_xp > 1000:
        return "true"
    if txn < 20 or active_days < 10:
        return "true"
    if total_xp > 0 and txn == 0:
        return "true"
    return "false"

async def process_wallet(session, wallet, sem):
    async with sem:
        stats = await fetch_wallet_stats(session, wallet)
        if not stats:
            return None

        activity = await get_activity_stats(session, wallet)
        result = {**stats, **activity}
        result["sybilFlag"] = evaluate_sybil(result)
        return result


async def main():
    with open(INPUT_FILE, "r") as f:
        wallets_data = json.load(f)
    wallets = [w["walletAddress"] for w in wallets_data]

    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    results = []

    async with aiohttp.ClientSession() as session:
        tasks = [process_wallet(session, w, sem) for w in wallets]
        for i, future in enumerate(asyncio.as_completed(tasks), start=1):
            res = await future
            if res:
                results.append(res)

            if i % BATCH_SIZE == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"💾 Progreso guardado: {i}/{len(wallets)} wallets procesadas...")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Procesadas {len(results)} wallets. Archivo en {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
