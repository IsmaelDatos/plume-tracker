from flask import Flask, render_template, jsonify, request, Response
import aiohttp
import asyncio
import pandas as pd
import json
import time
import nest_asyncio
from concurrent.futures import ThreadPoolExecutor

nest_asyncio.apply()

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=4)

# Configuración actualizada según el código original que funciona
LEADERBOARD_URL = "https://portal-api.plume.org/api/v1/stats/leaderboard"
PP_TOTALS_URL = "https://portal-api.plume.org/api/v1/stats/pp-totals"
HEADERS = {"User-Agent": "plume-fast-scan/1.0"}
LB_BATCH_SIZE = 10000
CONCURRENCY = 30  # Aumentamos la concurrencia
TIMEOUT_SECS = 30

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
    async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)) as session:
        while True:
            params = {
                "offset": offset,
                "count": LB_BATCH_SIZE,
                "overrideDay1Override": "false",
                "preview": "false",
            }
            async with session.get(LEADERBOARD_URL, params=params) as r:
                data = await r.json()
                page = data.get("data", {}).get("leaderboard", [])
                if not page:
                    break
                
                # Filtramos wallets con XP > 0 como en el código original
                batch_wallets = [(row["walletAddress"].lower(), row["totalXp"]) for row in page if row["totalXp"] > 0]
                wallets.extend(batch_wallets)
                
                if len(page) < LB_BATCH_SIZE:
                    break
                offset += LB_BATCH_SIZE
    return wallets

sem = asyncio.Semaphore(CONCURRENCY)

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

async def process_data(streamer):
    try:
        start_time = time.time()

        # Obtener wallets como en el código original
        leaderboard = await fetch_leaderboard_wallets()
        if not leaderboard:
            await streamer.queue.put(f"data: {json.dumps({'type': 'error', 'message': 'No se encontraron wallets con XP > 0'})}\n\n")
            return

        total_wallets = len(leaderboard)
        await streamer.queue.put(f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': total_wallets, 'message': f'Encontradas {total_wallets} wallets con XP > 0'})}\n\n")

        # Ordenar por XP para calcular ranking
        sorted_lb = sorted(leaderboard, key=lambda x: x[1], reverse=True)
        leaderboard_rank = {wallet: rank + 1 for rank, (wallet, _) in enumerate(sorted_lb)}

        # Procesar con semáforo como en el código original
        results = []
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)) as session:
            tasks = [fetch_xp_delta(session, wallet) for wallet, _ in sorted_lb]
            
            for i, fut in enumerate(asyncio.as_completed(tasks)):
                wallet, active, delta = await fut
                results.append({
                    "wallet": wallet,
                    "Rank leaderboard": leaderboard_rank[wallet],
                    "PP total": active,
                    "Ganancia": delta
                })
                
                # Actualizar progreso cada 100 wallets
                if i % 100 == 0 or i == len(tasks) - 1:
                    await streamer.queue.put(f"data: {json.dumps({'type': 'progress', 'current': i + 1, 'total': total_wallets, 'message': f'Procesando wallet {i + 1} de {total_wallets}'})}\n\n")

        # Generar resultados finales
        df = pd.DataFrame(results)
        df_top20 = df.sort_values("Ganancia", ascending=False).head(20)
        processing_time = f"{time.time() - start_time:.2f} segundos"

        await streamer.queue.put(f"data: {json.dumps({'type': 'complete', 'results': df_top20.to_dict(orient='records'), 'processing_time': processing_time, 'total_wallets': total_wallets})}\n\n")

    except Exception as e:
        print(f"Error en process_data: {str(e)}")
        await streamer.queue.put(f"data: {json.dumps({'type': 'error', 'message': f'Error en el servidor: {str(e)}'})}\n\n")
    finally:
        streamer.done = True

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@app.route('/api/top-earners-stream')
def stream_top_earners():
    def generate():
        streamer = SSEStreamer()
        executor.submit(lambda: asyncio.run(process_data(streamer)))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while True:
                try:
                    item = loop.run_until_complete(asyncio.wait_for(streamer.queue.get(), timeout=5.0))
                    yield item
                except asyncio.TimeoutError:
                    if streamer.done:
                        break
                    continue
        finally:
            loop.close()
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)