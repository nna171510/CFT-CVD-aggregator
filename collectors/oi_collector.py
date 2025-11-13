import aiohttp
from typing import Dict, Any, Optional

class OICollector:
    """Сбор Open Interest с бирж"""
    
    def __init__(self):
        self.session = None
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def fetch_binance_futures_oi(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Binance Futures OI"""
        url = 'https://fapi.binance.com/fapi/v1/openInterest'
        params = {'symbol': symbol}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'exchange': 'binance',
                        'market_type': 'futures',
                        'symbol': symbol,
                        'open_interest': float(data['openInterest']),
                        'timestamp': int(data['time'])
                    }
        except Exception as e:
            print(f"✗ Binance Futures OI error: {e}")
        return None
    
    async def fetch_bybit_futures_oi(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Bybit Futures OI"""
        url = 'https://api.bybit.com/v5/market/open-interest'
        params = {'category': 'linear', 'symbol': symbol, 'intervalTime': '5min'}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['retCode'] == 0 and data['result']['list']:
                        item = data['result']['list'][0]
                        return {
                            'exchange': 'bybit',
                            'market_type': 'futures',
                            'symbol': symbol,
                            'open_interest': float(item['openInterest']),
                            'timestamp': int(item['timestamp'])
                        }
        except Exception as e:
            print(f"✗ Bybit Futures OI error: {e}")
        return None
    
    async def collect_all(self, symbols: list) -> list:
        """Собрать OI со всех бирж"""
        await self.init_session()
        results = []
        
        for symbol in symbols:
            # Binance Futures
            oi = await self.fetch_binance_futures_oi(symbol)
            if oi:
                results.append(oi)
            
            # Bybit Futures (если включено)
            # oi = await self.fetch_bybit_futures_oi(symbol)
            # if oi:
            #     results.append(oi)
        
        return results