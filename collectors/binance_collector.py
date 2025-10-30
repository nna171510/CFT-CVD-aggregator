from .base_collector import BaseCollector
from typing import List, Dict, Any

class BinanceCollector(BaseCollector):
    def __init__(self, market_type: str, config: Dict):
        super().__init__('binance', market_type)
        self.url = config['url']
        self.config = config
    
    async def fetch_trades(self, symbol: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получить сделки с Binance"""
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000)
        }
        
        async with self.session.get(self.url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"HTTP {response.status}: {await response.text()}")
    
    def normalize_trade(self, trade: Dict, symbol: str) -> Dict[str, Any]:
        """
        Binance aggTrades format:
        {
            "a": 123456789,   # Aggregate trade ID
            "p": "50000.00",  # Price
            "q": "0.05",      # Quantity
            "f": 100,         # First trade ID
            "l": 105,         # Last trade ID
            "T": 1699564800000,  # Timestamp
            "m": true,        # Was buyer maker (true = sell, false = buy)
            "M": true
        }
        """
        return {
            'exchange': self.exchange,
            'market_type': self.market_type,
            'symbol': symbol,
            'trade_id': str(trade['a']),
            'price': float(trade['p']),
            'quantity': float(trade['q']),
            'side': 'sell' if trade['m'] else 'buy',  # m=true означает продажу
            'timestamp': int(trade['T'])
        }