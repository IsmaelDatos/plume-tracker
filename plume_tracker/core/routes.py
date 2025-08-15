import datetime
import logging
import requests
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, Response
from .services import PlumeService, S2StatsService, ActivityService
import asyncio

bp = Blueprint('core', __name__, url_prefix='/')
service = PlumeService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLUME_API_BASE = "https://portal-api.plume.org/api/v1/stats"
HEADERS = {"User-Agent": "plume-tracker/1.0"}
TIMEOUT = 30

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

@bp.route('/api/top-earners/stream')
def top_earners_stream():
    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def run():
            async for message in service.stream_top_earners():
                yield f"data: {message}\n\n"
        for chunk in loop.run_until_complete(_collect(run())):
            yield chunk

    return Response(generate(), mimetype='text/event-stream')

async def _collect(agen):
    """Convierte un async generator en lista para streaming en WSGI."""
    items = []
    async for x in agen:
        items.append(x)
    return items

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
                'pointsDifference': 0,
                'userSelfXp': item.get('userSelfXp', 0),
                'referralBonusXp': item.get('referralBonusXp', 0),
                'currentPlumeStakingTotalTokens': item.get('currentPlumeStakingTotalTokens', 0)
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
        CMC_API_KEY = "47ac6248-576d-4347-b387-8f2ab39de057"
        CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        
        cmc_params = {'symbol': 'PLUME', 'convert': 'USD'}
        cmc_headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
        
        price_response = requests.get(CMC_URL, headers=cmc_headers, params=cmc_params, timeout=10)
        price_response.raise_for_status()
        plume_price = float(price_response.json().get('data', {}).get('PLUME', {}).get('quote', {}).get('USD', {}).get('price', 0))
        
        balance_url = f"https://portal-api.plume.org/api/v1/wallet-balance?walletAddress={wallet_address}"
        balance_response = requests.get(balance_url, headers={"User-Agent": "plume-tracker/1.0"}, timeout=30)
        balance_response.raise_for_status()
        balance_data = balance_response.json()

        stats_url = f"https://portal-api.plume.org/api/v1/stats/wallet?walletAddress={wallet_address}"
        stats_response_api = requests.get(stats_url, headers={"User-Agent": "plume-tracker/1.0"}, timeout=30)
        stats_response_api.raise_for_status()
        stats_data_api = stats_response_api.json()

        def safe_float(value, default=0.0):
            try:
                return float(value) if value is not None else default
            except (TypeError, ValueError):
                return default

        tokens = []

        for token_info in balance_data.get('walletTokenBalanceInfoArr', []):
            token = token_info.get('token', {})
            holdings = token_info.get('holdings', {})
            
            symbol = str(token.get('symbol', '?')).upper()
            balance = safe_float(holdings.get('tokenBalance'))
            
            price = safe_float(token.get('priceUSD'))
            if price <= 0 and balance > 0:
                price = safe_float(holdings.get('valueUSD')) / balance
            
            if symbol in ['PLUME', 'WPLUME']:
                price = plume_price
            
            value_usd = safe_float(holdings.get('valueUSD', balance * price))
            
            tokens.append({
                'name': str(token.get('name', 'Unknown')),
                'symbol': symbol,
                'balance': balance,
                'price': price,
                'value_usd': value_usd,
                'type': 'token',
                'logo': str(token.get('imageSmallUrl', ''))
            })

        plume_staked = safe_float(stats_data_api.get('data', {}).get('stats', {}).get('plumeStaked'))
        if plume_staked > 0:
            tokens.append({
                'name': 'Plume Staked',
                'symbol': 'PLUME-staked',
                'balance': plume_staked,
                'price': plume_price,
                'value_usd': plume_staked * plume_price,
                'type': 'staking',
                'logo': ''
            })

        total_value = max(sum(t['value_usd'] for t in tokens), 0.01)
        for token in tokens:
            token['percentage'] = (token['value_usd'] / total_value) * 100

        tokens.sort(key=lambda x: x['value_usd'], reverse=True)
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
            datetime=datetime,
            tokens=tokens,
            total_value=total_value,
            plume_price=plume_price,
            error=None
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

        
@bp.route('/sybil-analysis')
def sybil_analysis():
    return render_template('sybil_analysis.html')