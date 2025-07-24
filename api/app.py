from http.server import BaseHTTPRequestHandler
import json
import asyncio
import aiohttp
import pandas as pd

class handler(BaseHTTPRequestHandler):
    async def get_top_earners(self):
        LEADERBOARD_URL = "https://portal-api.plume.org/api/v1/stats/leaderboard"
        PP_TOTALS_URL = "https://portal-api.plume.org/api/v1/stats/pp-totals"
        HEADERS = {"User-Agent": "plume-fast-scan/1.0"}
        CONCURRENCY = 10
        BATCH_SIZE = 50
        
        async def fetch_leaderboard():
            wallets = []
            offset = 0
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                while True:
                    params = {
                        "offset": offset,
                        "count": 10000,
                        "overrideDay1Override": "false",
                        "preview": "false",
                    }
                    async with session.get(LEADERBOARD_URL, params=params) as r:
                        data = await r.json()
                        page = data.get("data", {}).get("leaderboard", [])
                        if not page:
                            break
                        
                        batch = [(row["walletAddress"].lower(), row["totalXp"]) 
                               for row in page if row["totalXp"] > 0]
                        if not batch:
                            break
                            
                        wallets.extend(batch)
                        if len(page) < 10000:
                            break
                        offset += 10000
            return wallets

        sem = asyncio.Semaphore(CONCURRENCY)

        async def fetch_xp(session, wallet):
            url = f"{PP_TOTALS_URL}?walletAddress={wallet}"
            try:
                async with sem, session.get(url) as resp:
                    js = await resp.json()
                    data = js.get("data", {}).get("ppScores", {})
                    active = data.get("activeXp", {}).get("totalXp", 0)
                    prev = data.get("prevXp", {}).get("totalXp", 0)
                    return wallet, active, active - prev
            except:
                return wallet, 0, 0

        wallets = await fetch_leaderboard()
        if not wallets:
            return {"error": "No wallets found"}, 404

        # Ordenar por XP para ranking
        sorted_wallets = sorted(wallets, key=lambda x: x[1], reverse=True)
        rankings = {wallet: i+1 for i, (wallet, _) in enumerate(sorted_wallets)}

        results = []
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            tasks = [fetch_xp(session, wallet) for wallet, _ in sorted_wallets[:500]]  # Limitar a 500 para demo
            for future in asyncio.as_completed(tasks):
                wallet, active, delta = await future
                results.append({
                    "wallet": wallet,
                    "rank": rankings[wallet],
                    "totalXp": active,
                    "gain": delta
                })
                if len(results) >= 20:
                    break

        return sorted(results, key=lambda x: x["gain"], reverse=True)[:20]

    def do_GET(self):
        async def run():
            return await self.get_top_earners()
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run())
            
            if isinstance(result, tuple):  # Error case
                body, status = result
            else:
                body, status = result, 200
                
            self.send_response(status)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())
        finally:
            loop.close()