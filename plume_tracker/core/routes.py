import datetime
import logging
import requests
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from .services import PlumeService, S2StatsService, ActivityService

bp = Blueprint('core', __name__, url_prefix='/')
service = PlumeService()

PLUME_API_BASE = "https://portal-api.plume.org/api/v1/stats"
HEADERS = {"User-Agent": "plume-tracker/1.0"}
TIMEOUT = 30

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@bp.route('/')
def home():
    return render_template('index.html')

@bp.route('/s2-stats')
async def s2_stats():
    stats = await S2StatsService.get_s2_stats()
    
    if not stats:
        return render_template(
            's2_stats.html', 
            error="Could not fetch S2 stats at this time. Please try again later."
        )
    
    return render_template(
        's2_stats.html',
        total_wallets=stats['total_wallets'],
        total_xp=stats['total_xp'],
        avg_pp=stats['avg_pp'],
        plume_per_pp=stats['plume_per_pp'],
        plume_price=stats['plume_price'],
        supply_s2=stats['supply_s2'],
        now=datetime.datetime.utcnow()
    )

@bp.route('/api/top-earners')
async def top_earners():
    results = await service.get_top_earners()
    return jsonify(results)

@bp.route('/search', methods=['GET'])
def search_wallet():
    wallet_address = request.args.get('wallet_address', '').strip()
    if not wallet_address:
        return redirect('/')
    
    if not wallet_address.startswith('0x') or len(wallet_address) != 42:
        return render_template('index.html', 
                            search_error="Invalid wallet address format (should start with 0x and be 42 characters)")

    return redirect(f'/wallet/{wallet_address}')


@bp.route('/wallet/<wallet_address>')
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
            wd = {
                'walletAddress': item.get('walletAddress', ''),
                'xpRank': item.get('xpRank', 0),
                'totalXp': item.get('totalXp', 0),
                'TVL': item.get('realTvlUsd', item.get('tvlTotalUsd', 0)),
                'protocolsUsed': item.get('protocolsUsed', 0),
                'pointsDifference': 0
            }
            if wd['walletAddress'].lower() == wallet_address.lower():
                target_wallet_data = wd
            processed_leaderboard.append(wd)

        if target_wallet_data:
            for item in processed_leaderboard:
                item['pointsDifference'] = item['totalXp'] - target_wallet_data['totalXp']

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