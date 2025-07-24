from flask import Flask, render_template, jsonify, request, Response
import aiohttp
import asyncio
import pandas as pd
import json
import time
import nest_asyncio
from functools import wraps

# Aplicar parche para asyncio en Flask
nest_asyncio.apply()

app = Flask(__name__)

# Configuración
LEADERBOARD_URL = "https://portal-api.plume.org/api/v1/stats/leaderboard"
PP_TOTALS_URL = "https://portal-api.plume.org/api/v1/stats/pp-totals"
HEADERS = {"User-Agent": "plume-fast-scan/1.0"}
LB_BATCH_SIZE = 10000
CONCURRENCY = 10
TIMEOUT_SECS = 30
BATCH_SIZE = 50

class SSEStreamer:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.done = False

    async def generate(self):
        while not self.done or not self.queue.empty():
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                yield item
            except asyncio.TimeoutError:
                continue

    def __aiter__(self):
        return self.generate()

async def fetch_leaderboard_wallets():
    wallets = []
    offset = 0
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            try:
                params = {
                    "offset": offset,
                    "count": LB_BATCH_SIZE,
                    "walletAddress": "undefined",
                    "overrideDay1Override": "false",
                    "preview": "false",
                }
                async with session.get(LEADERBOARD_URL, params=params, timeout=TIMEOUT_SECS) as r:
                    data = await r.json()
                    page = data["data"]["leaderboard"]
                    if not page:
                        break

                    for row in page:
                        if row["totalXp"] == 0:
                            return wallets
                        wallets.append({
                            "wallet": row["walletAddress"].lower(),
                            "rank": offset + len(wallets) + 1,
                            "totalXp": row["totalXp"]
                        })

                    offset += LB_BATCH_SIZE

            except Exception as e:
                print(f"Error fetching leaderboard: {str(e)}")
                break
    return wallets

async def fetch_pp_gain(session, wallet):
    try:
        url = f"{PP_TOTALS_URL}?walletAddress={wallet}"
        async with session.get(url, timeout=TIMEOUT_SECS) as resp:
            js = await resp.json()
            data = js.get("data", {}).get("ppScores", {})
            active = data.get("activeXp", {}).get("totalXp", 0)
            prev = data.get("prevXp", {}).get("totalXp", 0)
            return active, prev
    except Exception as e:
        print(f"Error fetching PP for {wallet}: {str(e)}")
        return 0, 0

async def process_data(streamer):
    try:
        start_time = time.time()

        wallets_data = await fetch_leaderboard_wallets()
        if not wallets_data:
            await streamer.queue.put(f"data: {json.dumps({'type': 'error', 'message': 'No se encontraron wallets con XP > 0'})}\n\n")
            return

        total_wallets = len(wallets_data)
        await streamer.queue.put(f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': total_wallets, 'message': f'Encontradas {total_wallets} wallets con XP > 0'})}\n\n")

        results = []

        async def process_batch(batch):
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                tasks = [fetch_pp_gain(session, item["wallet"]) for item in batch]
                pp_gains = await asyncio.gather(*tasks)
                for i, (active, prev) in enumerate(pp_gains):
                    results.append({
                        "wallet": batch[i]["wallet"],
                        "Rank leaderboard": batch[i]["rank"],
                        "PP total": batch[i]["totalXp"],
                        "Ganancia": active - prev
                    })
                await streamer.queue.put(f"data: {json.dumps({'type': 'progress', 'current': min(batch[-1]['rank'], total_wallets), 'total': total_wallets, 'message': f'Procesando wallets {batch[0]["rank"]}-{batch[-1]["rank"]} de {total_wallets}'})}\n\n")

        for i in range(0, len(wallets_data), BATCH_SIZE):
            batch = wallets_data[i:i + BATCH_SIZE]
            await process_batch(batch)

        df = pd.DataFrame(results)
        df_top20 = df.sort_values("Ganancia", ascending=False).head(20)
        processing_time = f"{time.time() - start_time:.2f} segundos"

        await streamer.queue.put(f"data: {json.dumps({'type': 'complete', 'results': df_top20.to_dict(orient='records'), 'processing_time': processing_time, 'total_wallets': total_wallets})}\n\n")

    except Exception as e:
        print(f"Error en process_data: {str(e)}")
        await streamer.queue.put(f"data: {json.dumps({'type': 'error', 'message': f'Error en el servidor: {str(e)}'})}\n\n")
    finally:
        streamer.done = True

@app.route('/api/top-earners-stream')
async def stream_top_earners():
    streamer = SSEStreamer()
    asyncio.create_task(process_data(streamer))
    
    async def generate():
        async for chunk in streamer:
            yield chunk
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_plume_data():
    try:
        import requests
        wallet = request.args.get('wallet')
        params = {
            "offset": 0,
            "count": 100,
            "walletAddress": wallet if wallet else "undefined",
            "overrideDay1Override": "false",
            "preview": "false"
        }
        response = requests.get(LEADERBOARD_URL, params=params, headers=HEADERS, timeout=30)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True)