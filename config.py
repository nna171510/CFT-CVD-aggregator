import os
from dotenv import load_dotenv

load_dotenv()

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Settings
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', 30))
AGGREGATION_INTERVAL = int(os.getenv('AGGREGATION_INTERVAL', 300))

# Symbols
SYMBOLS = os.getenv('SYMBOLS', 'BTCUSDT').split(',')

# Метрики
COLLECT_OI = os.getenv('COLLECT_OI', 'true').lower() == 'true'
COLLECT_FUNDING = os.getenv('COLLECT_FUNDING', 'true').lower() == 'true'
COLLECT_LIQUIDATIONS = os.getenv('COLLECT_LIQUIDATIONS', 'true').lower() == 'true'
COLLECT_LONG_SHORT_RATIO = os.getenv('COLLECT_LONG_SHORT_RATIO', 'true').lower() == 'true'
COLLECT_LARGE_ORDERS = os.getenv('COLLECT_LARGE_ORDERS', 'true').lower() == 'true'

# Large Orders settings
LARGE_ORDERS_PRICE_STEP = float(os.getenv('LARGE_ORDERS_PRICE_STEP', '50.0'))
LARGE_ORDERS_INTERVAL = int(os.getenv('LARGE_ORDERS_INTERVAL', '60'))
LARGE_ORDERS_PRICE_FILTER_PCT = float(os.getenv('LARGE_ORDERS_PRICE_FILTER_PCT', '0.1'))

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
    'bybit': {
        'spot': {
            'enabled': os.getenv('COLLECT_BYBIT_SPOT', 'false').lower() == 'true',
            'url': 'https://api.bybit.com/v5/market/recent-trade',
            'symbols': SYMBOLS,
            'params': {'limit': 1000, 'category': 'spot'}
        },
        'futures': {
            'enabled': os.getenv('COLLECT_BYBIT_FUTURES', 'false').lower() == 'true',
            'url': 'https://api.bybit.com/v5/market/recent-trade',
            'symbols': SYMBOLS,
            'params': {'limit': 1000, 'category': 'linear'}
        }
    },
    'okx': {
        'spot': {
            'enabled': os.getenv('COLLECT_OKX_SPOT', 'false').lower() == 'true',
            'url': 'https://www.okx.com/api/v5/market/trades',
            'symbols': ['BTC-USDT'],
            'params': {'limit': 500}
        },
        'futures': {
            'enabled': os.getenv('COLLECT_OKX_FUTURES', 'false').lower() == 'true',
            'url': 'https://www.okx.com/api/v5/market/trades',
            'symbols': ['BTC-USDT-SWAP'],
            'params': {'limit': 500}
        }
    },
    'coinbase': {
        'spot': {
            'enabled': os.getenv('COLLECT_COINBASE_SPOT', 'true').lower() == 'true',
            'url': 'https://api.exchange.coinbase.com/products',
            'symbols': ['BTC-USD'],
            'params': {'limit': 100}
        }
    },
    'hyperliquid': {
        'perpetual': {
            'enabled': os.getenv('COLLECT_HYPERLIQUID', 'false').lower() == 'true',
            'url': 'https://api.hyperliquid.xyz/info',
            'symbols': ['BTC'],
            'params': {}
        }
    }
}