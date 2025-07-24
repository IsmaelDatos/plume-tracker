from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import asyncio
import aiohttp
import pandas as pd

class handler(BaseHTTPRequestHandler):
    async def process_request(self):
        LEADERBOARD_URL = "https://portal-api.plume.org/api/v1/stats/leaderboard"
        PP_TOTALS_URL = "https://portal-api.plume.org/api/v1/stats/pp-totals"
        HEADERS = {"User-Agent": "plume-fast-scan/1.0"}
        
        # Tu lógica original adaptada
        async def fetch_leaderboard_wallets():
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
                        wallets.extend([(row["walletAddress"].lower(), row["totalXp"]) for row in page if row["totalXp"] > 0])
                        if len(page) < 10000:
                            break
                        offset += 10000
            return wallets

        sem = asyncio.Semaphore(30)

        async def fetch_xp_delta(session, wallet):
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

        leaderboard = await fetch_leaderboard_wallets()
        sorted_lb = sorted(leaderboard, key=lambda x: x[1], reverse=True)
        leaderboard_rank = {wallet: rank + 1 for rank, (wallet, _) in enumerate(sorted_lb)}

        results = []
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            tasks = [fetch_xp_delta(session, wallet) for wallet, _ in sorted_lb]
            for fut in asyncio.as_completed(tasks):
                wallet, active, delta = await fut
                results.append({
                    "wallet": wallet,
                    "rank": leaderboard_rank[wallet],
                    "totalXp": active,
                    "gain": delta
                })
                if len(results) >= 20:  # Solo top 20
                    break

        return {
            'statusCode': 200,
            'body': json.dumps(results[:20]),
            'headers': {
                'Content-Type': 'application/json',
            },
        }

    def do_GET(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.process_request())
        
        self.send_response(result['statusCode'])
        for key, value in result['headers'].items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(result['body'].encode())
        return