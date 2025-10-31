import asyncio
import time
from datetime import datetime, timezone
from database import Database
import config

class Aggregator:
    def __init__(self):
        self.db = Database()
        self.shutdown_event = None  # Будет установлено из main.py
    
    def get_5min_boundaries(self, timestamp_ms: int = None):
        """Получить границы текущих 5 минут"""
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)
        
        # Округляем до начала 5-минутки (300000 ms = 5 минут)
        interval_start = (timestamp_ms // 300000) * 300000
        interval_end = interval_start + 300000
        
        return interval_start, interval_end
    
    async def aggregate_all(self):
        """Агрегировать данные для всех бирж и символов"""
        print(f"\n{'='*60}")
        print(f"Starting aggregation at {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*60}")
        
        # Получаем границы предыдущих 5 минут (завершенных)
        current_time = int(time.time() * 1000)
        prev_interval_end = (current_time // 300000) * 300000
        prev_interval_start = prev_interval_end - 300000
        
        print(f"Aggregating period: {datetime.fromtimestamp(prev_interval_start/1000, tz=timezone.utc)} to {datetime.fromtimestamp(prev_interval_end/1000, tz=timezone.utc)}")
        
        # Проходим по всем биржам
        for exchange_name, markets in config.EXCHANGES_CONFIG.items():
            for market_type, market_config in markets.items():
                if not market_config.get('enabled', False):
                    continue
                
                # Проверяем shutdown event
                if self.shutdown_event and self.shutdown_event.is_set():
                    print("Aggregation cancelled by shutdown")
                    return
                
                # Проходим по всем символам (только BTC)
                for symbol in market_config['symbols']:
                    # Нормализуем символ к формату BTCUSDT
                    normalized_symbol = 'BTCUSDT'
                    
                    try:
                        success = self.db.aggregate_5min_delta(
                            exchange=exchange_name,
                            market_type=market_type,
                            symbol=normalized_symbol,
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
        """Запустить периодическую агрегацию каждые 5 минут"""
        while True:
            try:
                # Проверяем shutdown event
                if self.shutdown_event and self.shutdown_event.is_set():
                    print("Aggregation loop stopped")
                    break
                
                # Ждем до следующих 5 минут
                current_time = int(time.time())
                seconds_until_next_interval = 300 - (current_time % 300)
                
                # Добавляем небольшую задержку после начала интервала (10 секунд)
                wait_time = seconds_until_next_interval + 10
                
                print(f"⏰ Next aggregation in {wait_time} seconds ({wait_time//60}m {wait_time%60}s)")
                
                # Используем wait_for для возможности прерывания
                try:
                    if self.shutdown_event:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(),
                            timeout=wait_time
                        )
                        break  # Shutdown requested
                    else:
                        await asyncio.sleep(wait_time)
                except asyncio.TimeoutError:
                    pass  # Continue with aggregation
                
                # Запускаем агрегацию
                await self.aggregate_all()
                
            except asyncio.CancelledError:
                print("Aggregation cancelled")
                break
            except Exception as e:
                print(f"✗ Error in periodic aggregation: {e}")
                await asyncio.sleep(30)