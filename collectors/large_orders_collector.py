import aiohttp
from typing import Dict, Any, List
import time
from decimal import Decimal, ROUND_DOWN
import config

class LargeOrdersCollector:
    """Сбор крупных лимитных ордеров из Order Book"""
    
    def __init__(self, price_step: float = 50.0):
        self.session = None
        self.price_step = price_step
        self.price_filter_pct = config.LARGE_ORDERS_PRICE_FILTER_PCT
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    def aggregate_by_price_step(self, orders: List[tuple], side: str) -> List[Dict[str, Any]]:
        """
        Агрегировать ордера по шагу цены
        orders: [(price, quantity), ...]
        """
        aggregated = {}
        
        for price, qty in orders:
            # Округляем цену до ближайшего шага
            price_level = (int(price / self.price_step) * self.price_step)
            
            if price_level not in aggregated:
                aggregated[price_level] = {'qty': 0, 'count': 0}
            
            aggregated[price_level]['qty'] += qty
            aggregated[price_level]['count'] += 1
        
        results = []
        for price_level, data in aggregated.items():
            results.append({
                'side': side,
                'price_level': price_level,
                'total_quantity': data['qty'],
                'total_value': price_level * data['qty'],
                'orders_count': data['count']
            })
        
        return results
    
    def filter_orders_by_price(self, orders: List[tuple], mid_price: float) -> List[tuple]:
        """Фильтр ордеров по диапазону цен"""
        min_price = mid_price * (1 - self.price_filter_pct)
        max_price = mid_price * (1 + self.price_filter_pct)
        return [(p, q) for p, q in orders if min_price <= p <= max_price]
    
    async def fetch_binance_orderbook(self, symbol: str) -> List[Dict[str, Any]]:
        """Binance Order Book"""
        url = 'https://fapi.binance.com/fapi/v1/depth'
        params = {'symbol': symbol, 'limit': 1000}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    timestamp = int(time.time() * 1000)
                    
                    raw_bids = [(float(p), float(q)) for p, q in data['bids']]
                    raw_asks = [(float(p), float(q)) for p, q in data['asks']]
                    
                    if not raw_bids or not raw_asks:
                        return []
                    
                    mid_price = (raw_bids[0][0] + raw_asks[0][0]) / 2
                    
                    bids = self.filter_orders_by_price(raw_bids, mid_price)
                    asks = self.filter_orders_by_price(raw_asks, mid_price)
                    
                    bids_agg = self.aggregate_by_price_step(bids, 'buy')
                    asks_agg = self.aggregate_by_price_step(asks, 'sell')
                    
                    results = []
                    for order in bids_agg + asks_agg:
                        results.append({
                            'exchange': 'binance',
                            'symbol': symbol,
                            'side': order['side'],
                            'price_level': order['price_level'],
                            'total_quantity': order['total_quantity'],
                            'total_value': order['total_value'],
                            'orders_count': order['orders_count'],
                            'timestamp': timestamp
                        })
                    
                    return results
        except Exception as e:
            print(f"✗ Binance Orderbook error: {e}")
        return []
    
    async def fetch_bybit_orderbook(self, symbol: str) -> List[Dict[str, Any]]:
        """Bybit Order Book"""
        url = 'https://api.bybit.com/v5/market/orderbook'
        params = {'category': 'linear', 'symbol': symbol, 'limit': 200}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['retCode'] == 0:
                        result = data['result']
                        timestamp = int(result['ts'])
                        
                        raw_bids = [(float(p), float(q)) for p, q in result['b']]
                        raw_asks = [(float(p), float(q)) for p, q in result['a']]
                        
                        if not raw_bids or not raw_asks:
                            return []
                        
                        mid_price = (raw_bids[0][0] + raw_asks[0][0]) / 2
                        
                        bids = self.filter_orders_by_price(raw_bids, mid_price)
                        asks = self.filter_orders_by_price(raw_asks, mid_price)
                        
                        bids_agg = self.aggregate_by_price_step(bids, 'buy')
                        asks_agg = self.aggregate_by_price_step(asks, 'sell')
                        
                        results = []
                        for order in bids_agg + asks_agg:
                            results.append({
                                'exchange': 'bybit',
                                'symbol': symbol,
                                'side': order['side'],
                                'price_level': order['price_level'],
                                'total_quantity': order['total_quantity'],
                                'total_value': order['total_value'],
                                'orders_count': order['orders_count'],
                                'timestamp': timestamp
                            })
                        
                        return results
        except Exception as e:
            print(f"✗ Bybit Orderbook error: {e}")
        return []
    
    async def fetch_coinbase_orderbook(self, symbol: str) -> List[Dict[str, Any]]:
        """Coinbase Order Book"""
        url = f'https://api.exchange.coinbase.com/products/{symbol}/book'
        params = {'level': 2}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    timestamp = int(time.time() * 1000)
                    
                    raw_bids = data.get('bids', [])
                    raw_asks = data.get('asks', [])
                    
                    if not raw_bids or not raw_asks:
                        return []
                    
                    best_bid = float(raw_bids[0][0])
                    best_ask = float(raw_asks[0][0])
                    mid_price = (best_bid + best_ask) / 2
                    
                    bids = self.filter_orders_by_price(
                        [(float(item[0]), float(item[1])) for item in raw_bids],
                        mid_price
                    )
                    
                    asks = self.filter_orders_by_price(
                        [(float(item[0]), float(item[1])) for item in raw_asks],
                        mid_price
                    )
                    
                    bids_agg = self.aggregate_by_price_step(bids, 'buy')
                    asks_agg = self.aggregate_by_price_step(asks, 'sell')
                    
                    results = []
                    for order in bids_agg + asks_agg:
                        results.append({
                            'exchange': 'coinbase',
                            'symbol': 'BTCUSDT',
                            'side': order['side'],
                            'price_level': order['price_level'],
                            'total_quantity': order['total_quantity'],
                            'total_value': order['total_value'],
                            'orders_count': order['orders_count'],
                            'timestamp': timestamp
                        })
                    
                    return results
        except Exception as e:
            print(f"✗ Coinbase Orderbook error: {e}")
        return []