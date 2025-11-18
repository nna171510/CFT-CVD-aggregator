from .base_collector import BaseCollector
from typing import List, Dict, Any

class CoinbaseCollector(BaseCollector):
    def __init__(self, market_type: str, config: Dict):
        super().__init__('coinbase', market_type)
        self.base_url = config['url']
        self.config = config
    
    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить сделки с Coinbase"""
        
        # Coinbase API не поддерживает фильтрацию по времени в /trades
        # Получаем последние и фильтруем локально
        url = f"{self.base_url}/{symbol}/trades"
        params = {'limit': min(limit, 100)}
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                trades = await response.json()
                
                # Фильтруем по последнему timestamp
                last_timestamp = self.get_last_timestamp('BTCUSDT')  # нормализованный символ
                
                if last_timestamp > 0:
                    from dateutil import parser
                    filtered_trades = []
                    for trade in trades:
                        dt = parser.parse(trade['time'])
                        trade_timestamp = int(dt.timestamp() * 1000)
                        if trade_timestamp > last_timestamp:
                            filtered_trades.append(trade)
                    return filtered_trades
                
                return trades
            else:
                text = await response.text()
                raise Exception(f"HTTP {response.status}: {text}")
    
    def normalize_trade(self, trade: Dict, symbol: str) -> Dict[str, Any]:
        """
        Coinbase format:
        {
            "time": "2024-10-29T14:30:00.000000Z",
            "trade_id": 123456789,
            "price": "50000.00",
            "size": "0.05",
            "side": "buy"
        }
        """
        from dateutil import parser
        
        dt = parser.parse(trade['time'])
        timestamp_ms = int(dt.timestamp() * 1000)
        
        return {
            'exchange': self.exchange,
            'market_type': self.market_type,
            'symbol': 'BTCUSDT',
            'trade_id': str(trade['trade_id']),
            'price': float(trade['price']),
            'quantity': float(trade['size']),
            'side': trade['side'],
            'timestamp': timestamp_ms
        }