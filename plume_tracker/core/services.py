import aiohttp
import asyncio
import pandas as pd
import nest_asyncio
import json
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
import concurrent.futures
import time
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