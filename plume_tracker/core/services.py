import aiohttp
import asyncio
import pandas as pd
import nest_asyncio
import json
import requests
import datetime as dt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import concurrent.futures
import time
import threading
import os
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

class PlumeService:
    def __init__(self):
        self.leaderboard_url = "https://portal-api.plume.org/api/v1/stats/leaderboard"
        self.pp_totals_batch_url = "https://portal-api.plume.org/api/v1/stats/pp-totals"  # Usaremos el endpoint normal
        self.headers = {"User-Agent": "plume-fast-scan/1.0"}
        self.batch_size = 10000
        self.concurrency = 50
        self.timeout_secs = 30
        self.retry_attempts = 2
        self.retry_delay = 1
        self.logger = logging.getLogger(__name__)

    async def stream_top_earners(self):
        """Versión optimizada"""
        try:
            wallets = await self._fetch_leaderboard_range(0, 500)
            
            if not wallets:
                yield {"type": "error", "message": "No se pudieron obtener wallets"}
                return
            sorted_wallets = sorted(wallets, key=lambda x: x[1], reverse=True)[:100000]
            total_wallets = len(sorted_wallets)
            batch_size = 15000
            results = []
            
            for i in range(0, total_wallets, batch_size):
                batch = sorted_wallets[i:i + batch_size]
                batch_results = await self._fetch_xp_delta_batch(batch)
                results.extend(batch_results)
                progress = min(100, int((i + batch_size) / total_wallets * 100))
                yield {
                    "type": "progress",
                    "progress": progress,
                    "completed": min(i + batch_size, total_wallets),
                    "total": total_wallets
                }
            valid_results = [r for r in results if r is not None]
            top_20 = sorted(valid_results, key=lambda x: x["Ganancia"], reverse=True)[:20]
            
            yield {"type": "completed", "data": top_20}

        except Exception as e:
            self.logger.error(f"Error in stream: {e}")
            yield {"type": "error", "message": str(e)}

    async def _fetch_xp_delta_batch(self, wallet_batch):
        """Fetch XP delta for a batch of wallets"""
        if not wallet_batch:
            return []
            
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                return await self._fetch_individual_parallel(session, wallet_batch)
                
        except Exception as e:
            self.logger.error(f"Batch fetch error: {e}") 
            return []

    async def _fetch_individual_parallel(self, session, wallet_batch):
        """Requests individuales en paralelo"""
        sem = asyncio.Semaphore(self.concurrency)
        tasks = []
        
        for wallet, xp in wallet_batch:
            task = self._fetch_xp_delta_single(session, wallet, sem)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = []
        for result in results:
            if isinstance(result, dict) and result is not None:
                valid_results.append(result)
            elif isinstance(result, Exception):
                self.logger.debug(f"Request failed: {result}")
        
        return valid_results

    async def _fetch_xp_delta_single(self, session, wallet, sem):
        """Fetch individual con mejor manejo de errores"""
        url = f"https://portal-api.plume.org/api/v1/stats/pp-totals?walletAddress={wallet}"
        
        try:
            async with sem, session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    js = await resp.json()
                    data = js.get("data", {}).get("ppScores", {})
                    active = data.get("activeXp", {}).get("totalXp", 0)
                    prev = data.get("prevXp", {}).get("totalXp", 0)
                    delta = active - prev
                    
                    return {
                        "wallet": wallet,
                        "Rank leaderboard": 0,
                        "Ganancia": delta
                    }
                else:
                    self.logger.debug(f"HTTP {resp.status} for wallet {wallet}")
                    return None
        except asyncio.TimeoutError:
            self.logger.debug(f"Timeout for wallet {wallet}")
            return None
        except Exception as e:
            self.logger.debug(f"Error for wallet {wallet}: {e}")
            return None

    async def _fetch_leaderboard_range(self, start_offset, end_offset):
        """Fetch leaderboard range (sin cambios)"""
        wallets = []
        offset = start_offset
        async with aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(total=self.timeout_secs)) as session:
            while offset < end_offset:
                params = {
                    "offset": offset,
                    "count": self.batch_size,
                    "overrideDay1Override": "false",
                    "preview": "false"
                }
                try:
                    async with session.get(self.leaderboard_url, params=params) as r:
                        data = await r.json()
                        page = data.get("data", {}).get("leaderboard", [])
                        if not page:
                            break
                        wallets.extend([
                            (row["walletAddress"].lower(), row["totalXp"])
                            for row in page if row["totalXp"] > 0
                        ])
                        if len(page) < self.batch_size:
                            break
                        offset += self.batch_size
                except Exception as e:
                    self.logger.error(f"Error fetching leaderboard: {e}")
                    break
        return wallets

class ActivityService:
    PLUME_EXPLORER_URL = "https://explorer.plume.org/api"
    MAINNET_LAUNCH = "2025-06-05"
    
    @staticmethod
    def fetch_transactions(wallet_address):
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': wallet_address
        }
        try:
            response = requests.get(ActivityService.PLUME_EXPLORER_URL, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('message') == 'OK':
                    return data.get('result', [])
            return []
        except:
            return []
    
    @staticmethod
    def process_activity_data(wallet_address):
        transactions = ActivityService.fetch_transactions(wallet_address)
        if not transactions:
            return None
        
        daily_counts = {}
        start_date = datetime.strptime(ActivityService.MAINNET_LAUNCH, "%Y-%m-%d").date()
        end_date = datetime.now().date()
        
        current_date = start_date
        while current_date <= end_date:
            daily_counts[current_date] = 0
            current_date += timedelta(days=1)
        
        for tx in transactions:
            try:
                tx_date = datetime.fromtimestamp(int(tx['timeStamp'])).date()
                if tx_date in daily_counts:
                    daily_counts[tx_date] += 1
            except:
                continue
        
        heatmap_data = {}
        current_date = start_date - timedelta(days=start_date.weekday() + 1)
        
        month_labels = []
        prev_month = None
        
        week_count = 0
        while current_date <= end_date:
            week_key = f"Week {week_count}"
            heatmap_data[week_key] = {}
            
            current_month = current_date.strftime("%b")
            if current_month != prev_month:
                month_labels.append({
                    'name': current_month,
                    'position': week_count,
                    'width': 1
                })
                prev_month = current_month
            else:
                month_labels[-1]['width'] += 1
            
            for weekday in range(7):
                date_key = current_date + timedelta(days=weekday)
                count = daily_counts.get(date_key, 0)
                heatmap_data[week_key][weekday] = {
                    'date': date_key.strftime("%Y-%m-%d"),
                    'count': count,
                    'color': ActivityService.get_color_for_count(count)
                }
            
            current_date += timedelta(days=7)
            week_count += 1
        
        return {
            'heatmap_data': heatmap_data,
            'month_labels': month_labels,
            'total_contributions': sum(daily_counts.values())
        }

    
    @staticmethod
    def get_color_for_count(count):
        if count == 0:
            return '#F9F9F9'
        elif count == 1:
            return '#FFC38B'
        elif 2 <= count <= 5:
            return '#FFA05A'
        elif 6 <= count <= 10:
            return '#FF8130'
        elif 11 <= count <= 20:
            return '#FF5E00'
        elif 21 <= count <= 50:
            return '#FF3200'
        else:
            return '#D10000'

class S2StatsService:
    PLUME_SUPPLY_S2 = 150_000_000
    CMC_API_KEY = "47ac6248-576d-4347-b387-8f2ab39de057"
    LEADERBOARD_URL = "https://portal-api.plume.org/api/v1/stats/leaderboard"
    CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    
    COUNT_PER_PAGE = 10000
    TIMEOUT_SECONDS = 30
    MIN_WALLETS = 240000
    BATCH_SIZE = 20000
    MAX_WORKERS = 8

    @classmethod
    def _fetch_wallet_batch(cls, start_offset, count):
        params = {
            "offset": start_offset,
            "count": count,
            "walletAddress": "undefined",
            "overrideDay1Override": "false",
            "preview": "false",
        }
        try:
            r = requests.get(cls.LEADERBOARD_URL, params=params, timeout=cls.TIMEOUT_SECONDS)
            r.raise_for_status()
            return r.json().get("data", {}).get("leaderboard", [])
        except:
            return []

    @classmethod
    def _find_last_active_offset(cls):
        current_offset = cls.MIN_WALLETS
        step = cls.COUNT_PER_PAGE
        last_active = cls.MIN_WALLETS
        
        # Búsqueda lineal por bloques grandes
        while True:
            batch = cls._fetch_wallet_batch(current_offset, 1)
            if not batch or batch[0].get("totalXp", 0) == 0:
                break
            last_active = current_offset
            current_offset += step
        
        # Búsqueda binaria para encontrar el último activo exacto
        low = last_active
        high = last_active + step
        while low <= high:
            mid = (low + high) // 2
            batch = cls._fetch_wallet_batch(mid, 1)
            if batch and batch[0].get("totalXp", 0) > 0:
                low = mid + 1
                last_active = mid
            else:
                high = mid - 1
        
        return last_active

    @classmethod
    def _process_batch(cls, start_offset, count):
        data = cls._fetch_wallet_batch(start_offset, count)
        wallets = set()
        xp_total = 0
        for wallet in data:
            xp = wallet.get("totalXp", 0)
            if xp == 0:
                continue
            address = wallet.get("walletAddress")
            if address not in wallets:
                wallets.add(address)
                xp_total += xp
        return wallets, xp_total

    @classmethod
    def _parallel_process_wallets(cls, total_wallets):
        batches = []
        for start in range(0, total_wallets, cls.BATCH_SIZE):
            end = min(start + cls.BATCH_SIZE, total_wallets)
            batches.append((start, end - start))
        
        all_wallets = set()
        total_xp = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=cls.MAX_WORKERS) as executor:
            futures = [executor.submit(cls._process_batch, start, count) for start, count in batches]
            for future in concurrent.futures.as_completed(futures):
                wallets, xp_sum = future.result()
                all_wallets.update(wallets)
                total_xp += xp_sum
        
        return all_wallets, total_xp

    @classmethod
    async def get_s2_stats(cls):
        try:
            start_time = time.time()
            
            # Encontrar último offset activo
            last_active_offset = cls._find_last_active_offset()
            total_wallets_est = last_active_offset + 1
            
            # Procesar wallets en paralelo
            wallets, total_xp = cls._parallel_process_wallets(total_wallets_est)
            avg_pp = total_xp / len(wallets) if wallets else 0
            
            # Obtener precio de PLUME
            plume_price = await cls._fetch_plume_price()
            
            return {
                'total_wallets': len(wallets),
                'total_xp': total_xp,
                'avg_pp': avg_pp,
                'plume_per_pp': cls.PLUME_SUPPLY_S2 / total_xp if total_xp else 0,
                'plume_price': plume_price,
                'supply_s2': cls.PLUME_SUPPLY_S2
            }
        except Exception as e:
            logging.error(f"Error getting S2 stats: {str(e)}")
            return None

    @classmethod
    async def _fetch_plume_price(cls):
        try:
            params = {"symbol": "PLUME", "convert": "USD"}
            headers = {"X-CMC_PRO_API_KEY": cls.CMC_API_KEY}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(cls.CMC_URL, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["data"]["PLUME"]["quote"]["USD"]["price"]
        except:
            return None
        
class WalletAnalyticsService:
    PLUME_EXPLORER_API = "https://explorer.plume.org/api"
    COINGECKO_API = "https://api.coingecko.com/api/v3/coins/plume/market_chart?vs_currency=usd&days=365"
    MAX_PAGES = 100
    OFFSET_PER_PAGE = 10000
    WORKERS = min(32, (os.cpu_count() or 4) * 4)
    START_DATE = dt.datetime(2025, 6, 5)  # Fecha de lanzamiento

    @staticmethod
    def _setup_session():
        """Crea una sesión requests con alto rendimiento y reintentos"""
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=WalletAnalyticsService.WORKERS * 2,
            pool_maxsize=WalletAnalyticsService.WORKERS * 2,
            max_retries=Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET"])
            ),
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @staticmethod
    def _get_transactions_page(session, wallet_address, page):
        """Descarga una página de transacciones de Plume Explorer"""
        params = {
            "module": "account",
            "action": "txlist",
            "address": wallet_address,
            "page": page,
            "offset": WalletAnalyticsService.OFFSET_PER_PAGE,
            "sort": "asc",
        }
        try:
            r = session.get(WalletAnalyticsService.PLUME_EXPLORER_API, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if data.get("message") == "OK":
                    return data.get("result", []) or []
            return []
        except Exception:
            return []

    @staticmethod
    def _fetch_plume_prices():
        """Descarga precios diarios de PLUME/USD desde CoinGecko"""
        try:
            r = requests.get(WalletAnalyticsService.COINGECKO_API, timeout=15)
            data = r.json()
            prices = data.get("prices", [])
            df = pd.DataFrame(prices, columns=["timestamp", "price_usd"])
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
            df = df.groupby("date", as_index=False)["price_usd"].last()
            return df.set_index("date")["price_usd"]
        except Exception as e:
            logger.error(f"Error fetching PLUME prices: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def _compute_week_index(date):
        delta_days = (date - WalletAnalyticsService.START_DATE.date()).days
        if delta_days < 0:
            return 0
        return int(delta_days // 7 + 1)

    @classmethod
    def analyze_wallet(cls, wallet_address: str):
        """Analiza una wallet completa y devuelve datos JSON listos para graficar."""
        session = cls._setup_session()
        wallet_lower = wallet_address.lower()
        next_page = 1
        stop = False
        lock = threading.Lock()
        txs_out = []

        def worker():
            nonlocal next_page, stop
            local_txs = []
            while True:
                with lock:
                    if stop or next_page > cls.MAX_PAGES:
                        break
                    page = next_page
                    next_page += 1
                txs = cls._get_transactions_page(session, wallet_lower, page)
                if not txs:
                    with lock:
                        stop = True
                    break
                for tx in txs:
                    if tx.get("from", "").lower() == wallet_lower:
                        local_txs.append(tx)
            return local_txs

        with concurrent.futures.ThreadPoolExecutor(max_workers=cls.WORKERS) as ex:
            futures = [ex.submit(worker) for _ in range(cls.WORKERS)]
            for f in concurrent.futures.as_completed(futures):
                txs_out.extend(f.result())

        if not txs_out:
            logger.info(f"No se encontraron transacciones para {wallet_address}")
            return {"wallet": wallet_address, "message": "No transactions found"}

        # Convertir a DataFrame
        df = pd.DataFrame(txs_out)
        df["timeStamp"] = pd.to_datetime(df["timeStamp"].astype(int), unit="s", utc=True)
        df["gasUsed"] = df["gasUsed"].astype(int)
        df["gasPrice"] = df["gasPrice"].astype(int)
        df["fee_plume"] = (df["gasUsed"] * df["gasPrice"]) / 1e18
        df["date"] = df["timeStamp"].dt.date
        df["semana_custom"] = df["date"].apply(cls._compute_week_index)
        df = df[df["semana_custom"] > 0]

        # Obtener precios PLUME/USD
        price_series = cls._fetch_plume_prices()
        df["price_usd"] = df["date"].map(price_series)
        df["fee_usd"] = df["fee_plume"] * df["price_usd"]

        # Agrupar por semana
        weekly_fees = df.groupby("semana_custom")[["fee_plume", "fee_usd"]].sum().reset_index()
        weekly_txn = df.groupby("semana_custom").size().reset_index(name="tx_count")

        # CONVERTIR VALORES NUMPY A TIPOS NATIVOS DE PYTHON
        total_plume = float(weekly_fees["fee_plume"].sum())
        total_usd = float(weekly_fees["fee_usd"].sum())
        total_txn = int(weekly_txn["tx_count"].sum())

        # Último día
        last_tx_time = df["timeStamp"].max()
        last_day_start = dt.datetime.combine(last_tx_time.date(), dt.time(0, 0), tzinfo=dt.timezone.utc)
        last_day_df = df[(df["timeStamp"] >= last_day_start) & (df["timeStamp"] <= last_tx_time)]
        last_day_fee = float(last_day_df["fee_plume"].sum())
        last_day_txn = int(last_day_df.shape[0])

        # Última semana
        last_week = int(df["semana_custom"].max())
        df_last_week = df[df["semana_custom"] == last_week]
        daily_fees = df_last_week.groupby("date")["fee_plume"].sum().reset_index()
        daily_txn = df_last_week.groupby("date").size().reset_index(name="tx_count")

        # Completar días faltantes
        start_of_week = cls.START_DATE + dt.timedelta(weeks=last_week - 1)
        week_days = [start_of_week + dt.timedelta(days=i) for i in range(7)]
        week_dates = [d.date() for d in week_days]
        daily_fees["date"] = pd.to_datetime(daily_fees["date"]).dt.date
        daily_txn["date"] = pd.to_datetime(daily_txn["date"]).dt.date
        week_df = pd.DataFrame({"date": week_dates})
        daily_fees = week_df.merge(daily_fees, on="date", how="left").fillna(0)
        daily_txn = week_df.merge(daily_txn, on="date", how="left").fillna(0)

        # CONVERTIR DATAFRAMES A DICT CON TIPOS NATIVOS
        def convert_to_native(obj):
            if hasattr(obj, 'item'):
                return obj.item()
            return obj

        weekly_fees_dict = []
        for _, row in weekly_fees.iterrows():
            weekly_fees_dict.append({
                "semana_custom": int(row["semana_custom"]),
                "fee_plume": float(row["fee_plume"]),
                "fee_usd": float(row["fee_usd"])
            })

        weekly_txn_dict = []
        for _, row in weekly_txn.iterrows():
            weekly_txn_dict.append({
                "semana_custom": int(row["semana_custom"]),
                "tx_count": int(row["tx_count"])
            })

        daily_fees_dict = []
        for _, row in daily_fees.iterrows():
            daily_fees_dict.append({
                "date": row["date"].isoformat() if hasattr(row["date"], 'isoformat') else str(row["date"]),
                "fee_plume": float(row["fee_plume"])
            })

        daily_txn_dict = []
        for _, row in daily_txn.iterrows():
            daily_txn_dict.append({
                "date": row["date"].isoformat() if hasattr(row["date"], 'isoformat') else str(row["date"]),
                "tx_count": int(row["tx_count"])
            })

        # Resultado JSON listo para graficar
        return {
            "wallet": wallet_address,
            "total_fees_plume": total_plume,
            "total_fees_usd": total_usd,
            "total_transactions": total_txn,
            "last_day": {
                "fees_plume": last_day_fee,
                "transactions": last_day_txn
            },
            "weekly_fees": weekly_fees_dict,
            "weekly_txn": weekly_txn_dict,
            "daily_fees": daily_fees_dict,
            "daily_txn": daily_txn_dict,
        }