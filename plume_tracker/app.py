from flask import Flask, render_template, jsonify, request, Response, redirect, url_for
import os
import requests
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import aiohttp
from functools import wraps
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
PLUME_API_BASE = "https://portal-api.plume.org/api/v1/stats"
HEADERS = {"User-Agent": "plume-tracker/1.0"}
TIMEOUT = 30

def create_app():
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

    app = Flask(__name__,
               template_folder=template_dir,
               static_folder=static_dir)
    
    app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True
    executor = ThreadPoolExecutor(max_workers=4)

    def async_route(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(f(*args, **kwargs))
            finally:
                loop.close()
        return wrapper

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/search', methods=['POST'])
    def search_wallet():
        wallet_address = request.form.get('wallet-search', '').strip().lower()
        if not wallet_address:
            return redirect(url_for('home'))
        
        if not wallet_address.startswith('0x') or len(wallet_address) != 42:
            return render_template('index.html', 
                                search_error="Invalid wallet address format (should start with 0x and be 42 characters)")

        return redirect(url_for('wallet_details', wallet_address=wallet_address))

    @app.route('/wallet/<wallet_address>')
    def wallet_details(wallet_address):
        try:
            wallet_url = f"{PLUME_API_BASE}/wallet?walletAddress={wallet_address}"
            wallet_response = requests.get(wallet_url, headers=HEADERS, timeout=TIMEOUT)
            
            if wallet_response.status_code != 200:
                logger.error(f"API Wallet Error: {wallet_response.status_code} - {wallet_response.text}")
                return render_template('wallet.html',
                                    wallet=wallet_address,
                                    error="Could not fetch wallet data from Plume API")
            
            wallet_data = wallet_response.json()
            stats = wallet_data.get('data', {}).get('stats', {})
            
            if not stats:
                return render_template('wallet.html',
                                    wallet=wallet_address,
                                    error="No stats data available for this wallet")

            xp_rank = stats.get('xpRank')
            total_xp = stats.get('totalXp', 0)

            if xp_rank is None:
                return render_template('wallet.html',
                                    wallet=wallet_address,
                                    error="This wallet doesn't have an XP ranking")

            offset = max(xp_rank - 11, 0)
            count = 21
            
            leaderboard_url = (
                f"{PLUME_API_BASE}/leaderboard?"
                f"offset={offset}&count={count}&"
                "overrideDay1Override=false&preview=false"
            )
            
            lb_response = requests.get(leaderboard_url, headers=HEADERS, timeout=TIMEOUT)
            
            if lb_response.status_code != 200:
                logger.error(f"API Leaderboard Error: {lb_response.status_code} - {lb_response.text}")
                return render_template('wallet.html',
                                    wallet=wallet_address,
                                    xp_rank=xp_rank,
                                    total_xp=total_xp,
                                    error="Could not fetch leaderboard data")

            leaderboard_data = lb_response.json()
            leaderboard = leaderboard_data.get('data', {}).get('leaderboard', [])
            
            if not leaderboard:
                return render_template('wallet.html',
                                    wallet=wallet_address,
                                    xp_rank=xp_rank,
                                    total_xp=total_xp,
                                    error="Empty leaderboard response")

            processed_leaderboard = []
            target_wallet_data = None

            for item in leaderboard:
                wallet_data = {
                    'walletAddress': item.get('walletAddress', ''),
                    'xpRank': item.get('xpRank', 0),
                    'totalXp': item.get('totalXp', 0),
                    'TVL': item.get('realTvlUsd', item.get('tvlTotalUsd', 0)),
                    'protocolsUsed': item.get('protocolsUsed', 0),
                    'pointsDifference': 0 
                }
                
                if wallet_data['walletAddress'].lower() == wallet_address.lower():
                    target_wallet_data = wallet_data
                processed_leaderboard.append(wallet_data)
            if target_wallet_data:
                for item in processed_leaderboard:
                    item['pointsDifference'] = item['totalXp'] - target_wallet_data['totalXp']
            from .core.services import ActivityService
            activity_data = ActivityService.process_activity_data(wallet_address)

            if activity_data is None:
                heatmap_data = None
                month_labels = []
                total_contributions = 0
            else:
                heatmap_data = activity_data['heatmap_data']
                month_labels = activity_data['month_labels']
                total_contributions = activity_data['total_contributions']

            return render_template(
                'wallet.html',
                wallet=wallet_address,
                leaderboard=processed_leaderboard,
                xp_rank=xp_rank,
                total_xp=total_xp,
                current_offset=offset,
                target_wallet=target_wallet_data,
                heatmap_data=heatmap_data,
                month_labels=month_labels,
                total_contributions=total_contributions,
                mainnet_launch=ActivityService.MAINNET_LAUNCH,
                datetime=datetime
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request Exception: {str(e)}")
            return render_template('wallet.html',
                                wallet=wallet_address,
                                error="Network error when contacting Plume API")
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}", exc_info=True)
            return render_template('wallet.html',
                                wallet=wallet_address,
                                error="An unexpected error occurred")

    return app
