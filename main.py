import asyncio
import signal
import sys
from typing import List
from datetime import datetime, timezone

import config
from database import Database
from collectors import (
    BinanceCollector, 
    BybitCollector, 
    OKXCollector, 
    CoinbaseCollector,
    HyperliquidCollector
)
from aggregator import Aggregator
from cvd_calculator import CVDCalculator
import utils

class CVDCollectorApp:
    def __init__(self):
        self.db = Database()
        self.aggregator = Aggregator()
        self.cvd_calc = CVDCalculator()
        self.collectors = []
        self.running = False
        
    def initialize_collectors(self):
        """Инициализировать коллекторы для всех включенных бирж"""
        print("Initializing collectors...")
        
        for exchange_name, markets in config.EXCHANGES_CONFIG.items():
            for market_type, market_config in markets.items():
                if not market_config.get('enabled', False):
                    continue
                
                try:
                    if exchange_name == 'binance':
                        collector = BinanceCollector(market_type, market_config)
                    elif exchange_name == 'bybit':
                        collector = BybitCollector(market_type, market_config)
                    elif exchange_name == 'okx':
                        collector = OKXCollector(market_type, market_config)
                    elif exchange_name == 'coinbase':
                        collector = CoinbaseCollector(market_type, market_config)
                    elif exchange_name == 'hyperliquid':
                        collector = HyperliquidCollector(market_type, market_config)
                    else:
                        continue
                    
                    self.collectors.append((collector, market_config['symbols']))
                    print(f"✓ Initialized {exchange_name} {market_type} collector")
                    
                except Exception as e:
                    print(f"✗ Failed to initialize {exchange_name} {market_type}: {e}")
        
        print(f"Total collectors initialized: {len(self.collectors)}\n")
    
    async def collect_trades_once(self):
        """Собрать сделки один раз со всех бирж"""
        all_trades = []
        
        tasks = []
        for collector, symbols in self.collectors:
            tasks.append(collector.collect(symbols))
        
        # Собираем параллельно со всех бирж
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"✗ Collection error: {result}")
            else:
                all_trades.extend(result)
        
        # Сохраняем в БД
        if all_trades:
            self.db.insert_trades(all_trades)
            utils.print_trade_summary(all_trades)
        
        return len(all_trades)
    
    async def collection_loop(self):
        """Основной цикл сбора данных"""
        print(f"{'='*80}")
        print(f"Starting collection loop (interval: {config.COLLECTION_INTERVAL}s)")
        print(f"{'='*80}\n")
        
        while self.running:
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Собираем сделки
                trades_count = await self.collect_trades_once()
                
                # Вычисляем время выполнения
                execution_time = asyncio.get_event_loop().time() - start_time
                
                # Ждем до следующего цикла
                wait_time = max(0, config.COLLECTION_INTERVAL - execution_time)
                
                if wait_time > 0:
                    print(f"⏰ Next collection in {wait_time:.1f}s (collected {trades_count} trades in {execution_time:.1f}s)\n")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                print(f"✗ Error in collection loop: {e}")
                await asyncio.sleep(5)
    
    async def start(self):
        """Запустить приложение"""
        print(f"\n{'='*80}")
        print(f"CVD Collector Starting - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Configuration: BTC only, 5-minute aggregation")
        print(f"{'='*80}\n")
        
        # Проверяем конфигурацию
        if not utils.validate_config():
            return
        
        # Инициализируем коллекторы
        self.initialize_collectors()
        
        if not self.collectors:
            print("✗ No collectors initialized. Check your .env configuration.")
            return
        
        self.running = True
        
        # Запускаем два параллельных процесса:
        # 1. Сбор сделок (каждые 30 секунд)
        # 2. Агрегация и расчет CVD (каждые 5 минут)
        try:
            await asyncio.gather(
                self.collection_loop(),
                self.aggregator.run_periodic_aggregation()
            )
        except asyncio.CancelledError:
            print("\n\nShutting down gracefully...")
        finally:
            # Закрываем все HTTP сессии
            for collector, _ in self.collectors:
                await collector.close_session()
            
            print("✓ All collectors closed")
    
    def stop(self):
        """Остановить приложение"""
        self.running = False

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    print("\n\n⚠️  Received interrupt signal, shutting down...")
    sys.exit(0)

async def main():
    """Главная функция"""
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Создаем и запускаем приложение
    app = CVDCollectorApp()
    
    try:
        await app.start()
    except KeyboardInterrupt:
        app.stop()
        print("\n✓ Application stopped")

if __name__ == "__main__":
    # Выводим SQL для создания таблиц
    print("\n" + "="*80)
    print("SUPABASE TABLE SETUP")
    print("="*80)
    print("\nRun this SQL in your Supabase SQL Editor:\n")
    print(utils.create_supabase_tables_sql())
    print("="*80 + "\n")
    
    input("Press Enter after creating tables in Supabase to continue...")
    
    # Запускаем приложение
    asyncio.run(main())