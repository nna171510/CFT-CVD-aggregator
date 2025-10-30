from .base_collector import BaseCollector
from typing import List, Dict, Any

class BybitCollector(BaseCollector):
    def __init__(self, market_type: str, config: Dict):
        super().__init__('bybit', market_type)
        self.url = config['url']
        self.config = config
    
    async def fetch_trades(self, symbol: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получить сделки с Bybit"""
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000),
            'category': self.config['params']['category']
        }
        
        async with self.session.get(self.url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data['result']['list'] if 'result' in data else []
            else:
                raise Exception(f"HTTP {response.status}: {await response.text()}")
    
    def normalize_trade(self, trade: Dict, symbol: str) -> Dict[str, Any]:
        """
        Bybit format:
        {
            "execId": "123456789",
            "symbol": "BTCUSDT",
            "price": "50000.00",
            "size": "0.05",
            "side": "Buy",  # Buy or Sell
            "time": "1699564800000"
        }
        """
        return {
            'exchange': self.exchange,
            'market_type': self.market_type,
            'symbol': symbol,
            'trade_id': trade['execId'],
            'price': float(trade['price']),
            'quantity': float(trade['size']),
            'side': trade['side'].lower(),
            'timestamp': int(trade['time'])
        }