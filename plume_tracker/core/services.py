import aiohttp
import asyncio
import pandas as pd
import nest_asyncio
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

nest_asyncio.apply()

class PlumeService:
    def __init__(self):
        self.leaderboard_url = "https://portal-api.plume.org/api/v1/stats/leaderboard"
        self.pp_totals_url = "https://portal-api.plume.org/api/v1/stats/pp-totals"
        self.headers = {"User-Agent": "plume-fast-scan/1.0"}
        
    async def get_top_earners(self):
        wallets = await self._fetch_leaderboard()
        if not wallets:
            return []
            
        sorted_wallets = sorted(wallets, key=lambda x: x[1], reverse=True)
        rankings = {wallet: i+1 for i, (wallet, _) in enumerate(sorted_wallets)}
        
        results = []
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = [self._fetch_xp(session, wallet) for wallet, _ in sorted_wallets[:500]]  # Limit for demo
            for future in asyncio.as_completed(tasks):
                wallet, active, delta = await future
                results.append({
                    "wallet": wallet,
                    "Rank leaderboard": rankings[wallet],
                    "PP total": active,
                    "Ganancia": delta
                })
                if len(results) >= 20:
                    break

        return sorted(results, key=lambda x: x["Ganancia"], reverse=True)[:20]
    
    async def _fetch_leaderboard(self):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(self.leaderboard_url, timeout=30) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                leaderboard = data.get('data', {}).get('leaderboard', [])
                return [(entry.get('walletAddress'), entry.get('totalXp', 0)) for entry in leaderboard]
        
    async def _fetch_xp(self, session, wallet):
        url = f"https://portal-api.plume.org/api/v1/stats/wallet?walletAddress={wallet}"
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    return wallet, 0, 0
                data = await resp.json()
                stats = data.get('data', {}).get('stats', {})
                active = stats.get('totalXp', 0)
                delta = stats.get('deltaXp', 0)
                return wallet, active, delta
        except:
            return wallet, 0, 0

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

    @classmethod
    async def get_s2_stats(cls):
        try:
            # Obtener datos del leaderboard
            stats = await cls._fetch_leaderboard_stats()
            
            # Obtener precio de PLUME
            plume_price = await cls._fetch_plume_price()
            
            # Calcular métricas
            stats['plume_per_pp'] = cls.PLUME_SUPPLY_S2 / stats['total_xp'] if stats['total_xp'] else 0
            stats['plume_price'] = plume_price
            stats['supply_s2'] = cls.PLUME_SUPPLY_S2
            
            return stats
        except Exception as e:
            logging.error(f"Error getting S2 stats: {str(e)}")
            return None

    @classmethod
    async def _fetch_leaderboard_stats(cls):
        offset = 0
        count_per_page = 2000
        unique_wallets = set()
        total_xp = 0
        
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    "offset": offset,
                    "count": count_per_page,
                    "overrideDay1Override": "false",
                    "preview": "false"
                }
                
                async with session.get(cls.LEADERBOARD_URL, params=params) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    leaderboard = data.get('data', {}).get('leaderboard', [])
                    
                    if not leaderboard:
                        break
                        
                    for entry in leaderboard:
                        wallet = entry.get('walletAddress')
                        xp = entry.get('totalXp', 0)
                        
                        if wallet and xp > 0:
                            unique_wallets.add(wallet)
                            total_xp += xp
                    
                    offset += count_per_page
        
        return {
            'total_wallets': len(unique_wallets),
            'total_xp': total_xp,
            'avg_pp': total_xp / len(unique_wallets) if unique_wallets else 0
        }

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