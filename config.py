import os
from dotenv import load_dotenv

load_dotenv()

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Settings
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', 30))
AGGREGATION_INTERVAL = int(os.getenv('AGGREGATION_INTERVAL', 300))  # 5 минут

# Symbols - только BTC
SYMBOLS = ['BTCUSDT']

# Exchange configurations
EXCHANGES_CONFIG = {
    'binance': {
        'spot': {
            'enabled': os.getenv('COLLECT_BINANCE_SPOT', 'true').lower() == 'true',
            'url': 'https://api.binance.com/api/v3/aggTrades',
            'symbols': SYMBOLS,
            'params': {'limit': 100}
        },
        'futures': {
            'enabled': os.getenv('COLLECT_BINANCE_FUTURES', 'true').lower() == 'true',
            'url': 'https://fapi.binance.com/fapi/v1/aggTrades',
            'symbols': SYMBOLS,
            'params': {'limit': 100}
        }
    },
    # 'bybit': {
    #     'spot': {
    #         'enabled': os.getenv('COLLECT_BYBIT_SPOT', 'true').lower() == 'true',
    #         'url': 'https://api.bybit.com/v5/market/recent-trade',
    #         'symbols': SYMBOLS,
    #         'params': {'limit': 1000, 'category': 'spot'}
    #     },
    #     'futures': {
    #         'enabled': os.getenv('COLLECT_BYBIT_FUTURES', 'true').lower() == 'true',
    #         'url': 'https://api.bybit.com/v5/market/recent-trade',
    #         'symbols': SYMBOLS,
    #         'params': {'limit': 1000, 'category': 'linear'}
    #     }
    # },
    # 'okx': {
    #     'spot': {
    #         'enabled': os.getenv('COLLECT_OKX_SPOT', 'true').lower() == 'true',
    #         'url': 'https://www.okx.com/api/v5/market/trades',
    #         'symbols': ['BTC-USDT'],  # OKX format
    #         'params': {'limit': 500}
    #     },
    #     'futures': {
    #         'enabled': os.getenv('COLLECT_OKX_FUTURES', 'true').lower() == 'true',
    #         'url': 'https://www.okx.com/api/v5/market/trades',
    #         'symbols': ['BTC-USDT-SWAP'],  # OKX futures format
    #         'params': {'limit': 500}
    #     }
    # },
    'coinbase': {
        'spot': {
            'enabled': os.getenv('COLLECT_COINBASE_SPOT', 'true').lower() == 'true',
            'url': 'https://api.exchange.coinbase.com/products',
            'symbols': ['BTC-USD'],  # Coinbase format
            'params': {'limit': 100}
        }
    }
    # 'hyperliquid': {
    #     'perpetual': {  # Hyperliquid только perpetual futures
    #         'enabled': os.getenv('COLLECT_HYPERLIQUID', 'true').lower() == 'true',
    #         'url': 'https://api.hyperliquid.xyz/info',
    #         'symbols': ['BTC'],  # Hyperliquid format
    #         'params': {}
    #     }
    # }
}