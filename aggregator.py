import asyncio
import time
from datetime import datetime, timezone
from database import Database
import config

class Aggregator:
    def __init__(self):
        self.db = Database()
        self.shutdown_event = None
        self.interval_ms = config.AGGREGATION_INTERVAL * 1000  # 60 сек → 60000 мс
        self.interval_sec = config.AGGREGATION_INTERVAL  # 60 сек
    
    def get_boundaries(self, timestamp_ms: int = None):
        """Получить границы текущего интервала"""
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)
        
        interval_start = (timestamp_ms // self.interval_ms) * self.interval_ms
        interval_end = interval_start + self.interval_ms
        
        return interval_start, interval_end
    
    async def aggregate_all(self):
        """Агрегировать данные для всех бирж и символов"""
        print(f"\n{'='*60}")
        print(f"Starting aggregation at {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*60}")
        
        # Получаем границы предыдущих 5 минут (завершенных)
        current_time = int(time.time() * 1000)
        prev_interval_end = (current_time // self.interval_ms) * self.interval_ms
        prev_interval_start = prev_interval_end - self.interval_ms
        
        print(f"Aggregating period: {datetime.fromtimestamp(prev_interval_start/1000, tz=timezone.utc)} to {datetime.fromtimestamp(prev_interval_end/1000, tz=timezone.utc)}")
        
        # Используем единый нормализованный символ для всех бирж
        normalized_symbol = 'BTCUSDT'
        
        # Проходим по всем биржам
        for exchange_name, markets in config.EXCHANGES_CONFIG.items():
            for market_type, market_config in markets.items():
                if not market_config.get('enabled', False):
                    continue
                
                # Проверяем shutdown event
                if self.shutdown_event and self.shutdown_event.is_set():
                    print("Aggregation cancelled by shutdown")
                    return
                
                try:
                    success = self.db.aggregate_delta(
                        exchange=exchange_name,
                        market_type=market_type,
                        symbol=normalized_symbol,  # Используем нормализованный символ
                        start_time=prev_interval_start,
                        end_time=prev_interval_end
                    )
                    
                    if success:
                        # После агрегации пересчитываем CVD
                        self.db.calculate_cvd(exchange_name, market_type, normalized_symbol)
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"✗ Error aggregating {exchange_name} {market_type} {normalized_symbol}: {e}")
        
        print(f"{'='*60}")
        print(f"Aggregation completed")
        print(f"{'='*60}\n")
    
    async def run_periodic_aggregation(self):
        """Запустить периодическую агрегацию каждые n минут"""
        while True:
            try:
                # Проверяем shutdown event
                if self.shutdown_event and self.shutdown_event.is_set():
                    print("Aggregation loop stopped")
                    break
                
                # Ждем до следующих 5 минут
                current_time = int(time.time())
                seconds_until_next_interval = self.interval_sec - (current_time % self.interval_sec)
                
                # Добавляем небольшую задержку после начала интервала (5 секунд)
                wait_time = seconds_until_next_interval + 5
                
                print(f"⏰ Next aggregation in {wait_time} seconds ({wait_time//60}m {wait_time%60}s)")
                
                # Используем wait_for для возможности прерывания
                try:
                    if self.shutdown_event:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(),
                            timeout=wait_time
                        )
                        break
                    else:
                        await asyncio.sleep(wait_time)
                except asyncio.TimeoutError:
                    pass
                
                # Запускаем агрегацию
                await self.aggregate_all()
                
            except asyncio.CancelledError:
                print("Aggregation cancelled")
                break
            except Exception as e:
                print(f"✗ Error in periodic aggregation: {e}")
                await asyncio.sleep(30)