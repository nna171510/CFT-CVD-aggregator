from .base_collector import BaseCollector
from typing import List, Dict, Any

class OKXCollector(BaseCollector):
    def __init__(self, market_type: str, config: Dict):
        super().__init__('okx', market_type)
        self.url = config['url']
        self.config = config
    
    async def fetch_trades(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Получить сделки с OKX"""
        params = {
            'instId': symbol,
            'limit': min(limit, 500)
        }
        
        async with self.session.get(self.url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data['data'] if 'data' in data else []
            else:
                raise Exception(f"HTTP {response.status}: {await response.text()}")
    
    def normalize_trade(self, trade: Dict, symbol: str) -> Dict[str, Any]:
        """
        OKX format:
        {
            "instId": "BTC-USDT",
            "tradeId": "123456789",
            "px": "50000.00",
            "sz": "0.05",
            "side": "buy",  # buy or sell
            "ts": "1699564800000"
        }
        """
        return {
            'exchange': self.exchange,
            'market_type': self.market_type,
            'symbol': symbol,
            'trade_id': trade['tradeId'],
            'price': float(trade['px']),
            'quantity': float(trade['sz']),
            'side': trade['side'],
            'timestamp': int(trade['ts'])
        }