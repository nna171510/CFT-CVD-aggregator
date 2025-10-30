from .base_collector import BaseCollector
from typing import List, Dict, Any
import json

class HyperliquidCollector(BaseCollector):
    def __init__(self, market_type: str, config: Dict):
        super().__init__('hyperliquid', market_type)
        self.url = config['url']
        self.config = config
    
    async def fetch_trades(self, symbol: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Получить сделки с Hyperliquid
        Hyperliquid использует WebSocket для real-time данных,
        но мы попробуем через их REST API
        """
        # Hyperliquid требует POST запрос
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol,
                "interval": "1m",
                "startTime": None,  # последние данные
                "endTime": None
            }
        }
        
        try:
            # Попробуем получить свечи и экстраполировать trades
            async with self.session.post(
                self.url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._convert_candles_to_trades(data, symbol)
                else:
                    # Если не работает, пробуем альтернативный endpoint
                    return await self._fetch_via_websocket_snapshot(symbol)
        except Exception as e:
            print(f"Hyperliquid API error: {e}")
            return []
    
    def _convert_candles_to_trades(self, data: List, symbol: str) -> List[Dict[str, Any]]:
        """
        Конвертируем свечи в псевдо-сделки
        Это упрощение, но лучше чем ничего
        """
        trades = []
        
        if not data:
            return trades
        
        for candle in data[-10:]:  # Берем последние 10 свечей
            # Candle format: [timestamp, open, high, low, close, volume]
            timestamp = candle['t'] if isinstance(candle, dict) else candle[0]
            close_price = candle['c'] if isinstance(candle, dict) else candle[4]
            volume = candle['v'] if isinstance(candle, dict) else candle[5]
            open_price = candle['o'] if isinstance(candle, dict) else candle[1]
            
            # Определяем направление по свече
            side = 'buy' if float(close_price) > float(open_price) else 'sell'
            
            trades.append({
                'timestamp': int(timestamp),
                'price': float(close_price),
                'size': float(volume),
                'side': side,
                'trade_id': f"{timestamp}_{symbol}"
            })
        
        return trades
    
    async def _fetch_via_websocket_snapshot(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Альтернативный метод через websocket snapshot
        """
        payload = {
            "type": "l2Book",
            "coin": symbol
        }
        
        try:
            async with self.session.post(
                self.url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Обрабатываем orderbook snapshot
                    return self._process_orderbook_snapshot(data, symbol)
                return []
        except Exception as e:
            print(f"Hyperliquid websocket snapshot error: {e}")
            return []
    
    def _process_orderbook_snapshot(self, data: Dict, symbol: str) -> List[Dict[str, Any]]:
        """
        Обработка orderbook для получения псевдо-сделок
        """
        trades = []
        
        if 'levels' not in data:
            return trades
        
        # Берем топ бид/аск как индикатор последней сделки
        bids = data['levels'][0] if len(data['levels']) > 0 else []
        asks = data['levels'][1] if len(data['levels']) > 1 else []
        
        import time
        current_time = int(time.time() * 1000)
        
        if bids and asks:
            # Создаем синтетическую сделку на mid-price
            bid_price = float(bids[0]['px']) if bids else 0
            ask_price = float(asks[0]['px']) if asks else 0
            mid_price = (bid_price + ask_price) / 2
            
            trades.append({
                'timestamp': current_time,
                'price': mid_price,
                'size': 0.1,  # Символический объем
                'side': 'buy',
                'trade_id': f"{current_time}_{symbol}_synthetic"
            })
        
        return trades
    
    def normalize_trade(self, trade: Dict, symbol: str) -> Dict[str, Any]:
        """
        Нормализовать формат сделки Hyperliquid
        """
        return {
            'exchange': self.exchange,
            'market_type': self.market_type,
            'symbol': 'BTCUSDT',  # Нормализуем к общему формату
            'trade_id': trade.get('trade_id', str(trade['timestamp'])),
            'price': float(trade['price']),
            'quantity': float(trade['size']),
            'side': trade['side'].lower(),
            'timestamp': int(trade['timestamp'])
        }