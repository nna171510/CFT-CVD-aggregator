import asyncio
import websockets
import json
from typing import Dict, Any, Callable
from datetime import datetime

class BinanceWSCollector:
    def __init__(self, market_type: str, config: Dict):
        self.exchange = 'binance'
        self.market_type = market_type
        self.config = config
        self.websocket = None
        self.running = False
        self.on_trade_callback = None
        
        # WebSocket URLs
        if market_type == 'spot':
            self.ws_url = "wss://stream.binance.com:9443/ws"
        elif market_type == 'futures':
            self.ws_url = "wss://fstream.binance.com/ws"
        else:
            raise ValueError(f"Unknown market type: {market_type}")
    
    def set_trade_callback(self, callback: Callable):
        """Установить callback для обработки трейдов"""
        self.on_trade_callback = callback
    
    async def connect(self, symbol: str):
        """Подключиться к WebSocket для символа"""
        stream = f"{symbol.lower()}@aggTrade"
        url = f"{self.ws_url}/{stream}"
        
        print(f"🔌 Connecting to {self.exchange} {self.market_type} WebSocket: {symbol}")
        
        self.running = True
        reconnect_delay = 1
        
        while self.running:
            try:
                async with websockets.connect(url) as websocket:
                    print(f"✓ Connected to {self.exchange} {self.market_type} {symbol}")
                    reconnect_delay = 1  # Сброс задержки при успешном подключении
                    
                    while self.running:
                        try:
                            message = await asyncio.wait_for(
                                websocket.recv(), 
                                timeout=30
                            )
                            
                            data = json.loads(message)
                            trade = self.normalize_trade(data, symbol)
                            
                            # Вызываем callback если установлен
                            if self.on_trade_callback:
                                await self.on_trade_callback(trade)
                                
                        except asyncio.TimeoutError:
                            # Ping-pong для поддержания соединения
                            await websocket.ping()
                            
            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    print(f"⚠️  Connection closed for {self.exchange} {self.market_type} {symbol}, reconnecting in {reconnect_delay}s...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 60)  # Exponential backoff
            except Exception as e:
                if self.running:
                    print(f"✗ Error in WebSocket {self.exchange} {self.market_type} {symbol}: {e}")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 60)
    
    def normalize_trade(self, data: Dict, symbol: str) -> Dict[str, Any]:
        """
        Binance WebSocket aggTrade format:
        {
            "e": "aggTrade",
            "E": 1672515782136,
            "s": "BTCUSDT",
            "a": 12345,
            "p": "50000.00",
            "q": "0.05",
            "f": 100,
            "l": 105,
            "T": 1672515782136,
            "m": true
        }
        """
        return {
            'exchange': self.exchange,
            'market_type': self.market_type,
            'symbol': symbol,
            'trade_id': str(data['a']),
            'price': float(data['p']),
            'quantity': float(data['q']),
            'side': 'sell' if data['m'] else 'buy',
            'timestamp': int(data['T'])
        }
    
    async def stop(self):
        """Остановить WebSocket"""
        print(f"🔌 Stopping {self.exchange} {self.market_type} WebSocket")
        self.running = False