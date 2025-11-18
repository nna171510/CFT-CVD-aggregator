import aiohttp
import asyncio
from typing import List, Dict, Any
from abc import ABC, abstractmethod

class BaseCollector(ABC):
    def __init__(self, exchange: str, market_type: str):
        self.exchange = exchange
        self.market_type = market_type
        self.session = None
        self.db = None
    
    async def init_session(self):
        """Инициализация HTTP сессии"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not self.db:
            from database import Database
            self.db = Database()
    
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
    
    def get_last_timestamp(self, symbol: str) -> int:
        """Получить timestamp последней сделки из БД"""
        if self.db:
            return self.db.get_last_trade_timestamp(self.exchange, self.market_type, symbol)
        return 0
    
    @abstractmethod
    async def fetch_trades(self, symbol: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получить сделки с биржи"""
        pass
    
    @abstractmethod
    def normalize_trade(self, trade: Dict, symbol: str) -> Dict[str, Any]:
        """Нормализовать формат сделки"""
        pass
    
    async def collect(self, symbols: List[str], limit: int = 1000) -> List[Dict[str, Any]]:
        """Собрать сделки для всех символов"""
        await self.init_session()
        
        all_trades = []
        for symbol in symbols:
            try:
                trades = await self.fetch_trades(symbol, limit)
                normalized = [self.normalize_trade(t, symbol) for t in trades]
                all_trades.extend(normalized)
                print(f"✓ Collected {len(normalized)} trades from {self.exchange} {self.market_type} {symbol}")
            except Exception as e:
                print(f"✗ Error collecting {self.exchange} {self.market_type} {symbol}: {e}")
        
        return all_trades