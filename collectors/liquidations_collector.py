import aiohttp
from typing import Dict, Any, List
import time

class LiquidationsCollector:
    """Сбор Liquidations с бирж"""
    
    def __init__(self):
        self.session = None
        self.last_timestamps = {}  # храним последний timestamp для каждой биржи
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def fetch_binance_liquidations(self, symbol: str) -> List[Dict[str, Any]]:
        """Binance Liquidations"""
        url = 'https://fapi.binance.com/fapi/v1/forceOrders'
        
        # Получаем последние ликвидации
        params = {'symbol': symbol, 'limit': 100}
        
        # Если есть последний timestamp, берем только новые
        key = f"binance_{symbol}"
        if key in self.last_timestamps:
            params['startTime'] = self.last_timestamps[key] + 1
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    max_timestamp = 0
                    
                    for item in data:
                        timestamp = int(item['time'])
                        if timestamp > max_timestamp:
                            max_timestamp = timestamp
                        
                        results.append({
                            'exchange': 'binance',
                            'symbol': symbol,
                            'side': item['side'].lower(),
                            'price': float(item['price']),
                            'quantity': float(item['origQty']),
                            'value': float(item['price']) * float(item['origQty']),
                            'timestamp': timestamp
                        })
                    
                    # Обновляем последний timestamp
                    if max_timestamp > 0:
                        self.last_timestamps[key] = max_timestamp
                    
                    return results
        except Exception as e:
            print(f"✗ Binance Liquidations error: {e}")
        return []
    
    async def fetch_bybit_liquidations(self, symbol: str) -> List[Dict[str, Any]]:
        """Bybit Liquidations"""
        url = 'https://api.bybit.com/v5/market/recent-trade'
        params = {'category': 'linear', 'symbol': symbol, 'limit': 100}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['retCode'] == 0:
                        results = []
                        # Bybit не дает прямого API для liquidations через public endpoint
                        # Нужно использовать WebSocket или другой метод
                        return results
        except Exception as e:
            print(f"✗ Bybit Liquidations error: {e}")
        return []
    
    async def collect_all(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Собрать Liquidations со всех бирж"""
        await self.init_session()
        results = []
        
        for symbol in symbols:
            liqs = await self.fetch_binance_liquidations(symbol)
            if liqs:
                results.extend(liqs)
            
            # liqs = await self.fetch_bybit_liquidations(symbol)
            # if liqs:
            #     results.extend(liqs)
        
        return results