import aiohttp
from typing import Dict, Any, Optional, List

class FundingCollector:
    """Сбор Funding Rate с бирж"""
    
    def __init__(self):
        self.session = None
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def fetch_binance_funding(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Binance Funding Rate"""
        url = 'https://fapi.binance.com/fapi/v1/fundingRate'
        params = {'symbol': symbol, 'limit': 1}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        return {
                            'exchange': 'binance',
                            'symbol': symbol,
                            'funding_rate': float(data[0]['fundingRate']),
                            'funding_time': int(data[0]['fundingTime']),
                            'next_funding_time': None
                        }
        except Exception as e:
            print(f"✗ Binance Funding error: {e}")
        return None
    
    async def fetch_bybit_funding(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Bybit Funding Rate"""
        url = 'https://api.bybit.com/v5/market/funding/history'
        params = {'category': 'linear', 'symbol': symbol, 'limit': 1}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['retCode'] == 0 and data['result']['list']:
                        item = data['result']['list'][0]
                        return {
                            'exchange': 'bybit',
                            'symbol': symbol,
                            'funding_rate': float(item['fundingRate']),
                            'funding_time': int(item['fundingRateTimestamp']),
                            'next_funding_time': None
                        }
        except Exception as e:
            print(f"✗ Bybit Funding error: {e}")
        return None
    
    async def collect_all(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Собрать Funding со всех бирж"""
        await self.init_session()
        results = []
        
        for symbol in symbols:
            funding = await self.fetch_binance_funding(symbol)
            if funding:
                results.append(funding)
            
            # funding = await self.fetch_bybit_funding(symbol)
            # if funding:
            #     results.append(funding)
        
        return results