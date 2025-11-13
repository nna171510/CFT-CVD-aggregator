import aiohttp
from typing import Dict, Any, Optional, List
import time

class LSRatioCollector:
    """Сбор Long/Short Ratio с бирж"""
    
    def __init__(self):
        self.session = None
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def fetch_binance_ls_ratio(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Binance Long/Short Ratio (топ трейдеры)"""
        url = 'https://fapi.binance.com/futures/data/topLongShortAccountRatio'
        params = {'symbol': symbol, 'period': '5m', 'limit': 1}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        item = data[0]
                        long_ratio = float(item['longAccount'])
                        short_ratio = float(item['shortAccount'])
                        return {
                            'exchange': 'binance',
                            'symbol': symbol,
                            'long_ratio': long_ratio,
                            'short_ratio': short_ratio,
                            'long_short_ratio': long_ratio / short_ratio if short_ratio > 0 else 0,
                            'timestamp': int(item['timestamp'])
                        }
        except Exception as e:
            print(f"✗ Binance LS Ratio error: {e}")
        return None
    
    async def fetch_bybit_ls_ratio(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Bybit Long/Short Ratio"""
        url = 'https://api.bybit.com/v5/market/account-ratio'
        params = {'category': 'linear', 'symbol': symbol, 'period': '5min', 'limit': 1}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['retCode'] == 0 and data['result']['list']:
                        item = data['result']['list'][0]
                        long_ratio = float(item['buyRatio'])
                        short_ratio = float(item['sellRatio'])
                        return {
                            'exchange': 'bybit',
                            'symbol': symbol,
                            'long_ratio': long_ratio,
                            'short_ratio': short_ratio,
                            'long_short_ratio': long_ratio / short_ratio if short_ratio > 0 else 0,
                            'timestamp': int(item['timestamp'])
                        }
        except Exception as e:
            print(f"✗ Bybit LS Ratio error: {e}")
        return None
    
    async def collect_all(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Собрать LS Ratio со всех бирж"""
        await self.init_session()
        results = []
        
        for symbol in symbols:
            ratio = await self.fetch_binance_ls_ratio(symbol)
            if ratio:
                results.append(ratio)
            
            # ratio = await self.fetch_bybit_ls_ratio(symbol)
            # if ratio:
            #     results.append(ratio)
        
        return results