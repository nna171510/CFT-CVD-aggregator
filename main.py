import asyncio
import signal
import time
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
from collectors.oi_collector import OICollector
from collectors.funding_collector import FundingCollector
from collectors.ls_ratio_collector import LSRatioCollector
from collectors.liquidations_collector import LiquidationsCollector
from collectors.large_orders_collector import LargeOrdersCollector

from aggregator import Aggregator
from cvd_calculator import CVDCalculator
import utils

class CVDCollectorApp:
    def __init__(self):
        self.db = Database()
        self.aggregator = Aggregator()
        self.cvd_calc = CVDCalculator()
        self.collectors = []
        self.oi_collector = OICollector()
        self.funding_collector = FundingCollector()
        self.ls_ratio_collector = LSRatioCollector()
        self.liquidations_collector = LiquidationsCollector()
        self.large_orders_collector = LargeOrdersCollector(price_step=config.LARGE_ORDERS_PRICE_STEP)
        self.last_orderbook_collection = 0
        self.running = False
        self.shutdown_event = asyncio.Event()
        
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
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"✗ Collection error: {result}")
            else:
                all_trades.extend(result)
        
        if all_trades:
            self.db.insert_trades(all_trades)
            utils.print_trade_summary(all_trades)
        
        return len(all_trades)
    
    async def collect_metrics_once(self):
        """Собрать метрики (OI, Funding, Liquidations)"""
        # Open Interest
        if config.COLLECT_OI:
            oi_data = await self.oi_collector.collect_all(config.SYMBOLS)
            if oi_data:
                self.db.insert_open_interest(oi_data)
                print(f"✓ Collected OI: {len(oi_data)} records")
        
        # Funding Rate
        if config.COLLECT_FUNDING:
            funding_data = await self.funding_collector.collect_all(config.SYMBOLS)
            if funding_data:
                self.db.insert_funding_rate(funding_data)
                print(f"✓ Collected Funding: {len(funding_data)} records")
                
        # Liquidations (real-time)
        if config.COLLECT_LIQUIDATIONS:
            liq_data = await self.liquidations_collector.collect_all(config.SYMBOLS)
            if liq_data:
                self.db.insert_liquidations(liq_data)
                print(f"✓ Collected Liquidations: {len(liq_data)} records")

        # Long/Short Ratio (hourly)
        if config.COLLECT_LONG_SHORT_RATIO:
            ls_data = await self.ls_ratio_collector.collect_all(config.SYMBOLS)
            if ls_data:
                self.db.insert_long_short_ratio(ls_data)
                print(f"✓ Collected LS Ratio: {len(ls_data)} records")
    
    async def collection_loop(self):
        """Основной цикл сбора данных"""
        print(f"{'='*80}")
        print(f"Starting collection loop (interval: {config.COLLECTION_INTERVAL}s)")
        print(f"{'='*80}\n")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Собираем сделки
                trades_count = await self.collect_trades_once()                
                # Собираем метрики
                await self.collect_metrics_once()
                # Собираем orderbook
                await self.collect_orderbook_once()
                
                execution_time = asyncio.get_event_loop().time() - start_time
                wait_time = max(0, config.COLLECTION_INTERVAL - execution_time)
                
                if wait_time > 0:
                    print(f"⏰ Next collection in {wait_time:.1f}s (collected {trades_count} trades in {execution_time:.1f}s)\n")
                    try:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(), 
                            timeout=wait_time
                        )
                        break
                    except asyncio.TimeoutError:
                        pass
               
            except asyncio.CancelledError:
                print("Collection loop cancelled")
                break
            except Exception as e:
                print(f"✗ Error in collection loop: {e}")
                await asyncio.sleep(5)

    async def collect_orderbook_once(self):
        """Собрать orderbook (раз в минуту)"""
        current_time = time.time()
        if current_time - self.last_orderbook_collection < config.LARGE_ORDERS_INTERVAL:
            return
        
        self.last_orderbook_collection = current_time
        orders_data = await self.large_orders_collector.collect_all(config.SYMBOLS)
        if orders_data:
            self.db.insert_large_orders(orders_data)
            print(f"✓ Collected Order Book: {len(orders_data)} price levels")
    
    async def start(self):
        """Запустить приложение"""
        print(f"\n{'='*80}")
        print(f"CVD Collector Starting - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Configuration: BTC only, 5-minute aggregation")
        print(f"{'='*80}\n")
        
        if not utils.validate_config():
            return
        
        self.initialize_collectors()
        
        if not self.collectors:
            print("✗ No collectors initialized. Check your .env configuration.")
            return
        
        self.running = True
        
        collection_task = asyncio.create_task(self.collection_loop())
        aggregation_task = asyncio.create_task(self.aggregator.run_periodic_aggregation())
        
        self.aggregator.shutdown_event = self.shutdown_event
        
        try:
            await asyncio.gather(collection_task, aggregation_task)
        except asyncio.CancelledError:
            print("\nShutdown initiated...")
        finally:
            print("\nClosing collectors...")
            for collector, _ in self.collectors:
                await collector.close_session()
            await self.oi_collector.close_session()
            await self.funding_collector.close_session()
            await self.ls_ratio_collector.close_session()
            await self.liquidations_collector.close_session()
            await self.large_orders_collector.close_session()
            print("✓ All collectors closed")
    
    def stop(self):
        """Остановить приложение"""
        self.running = False
        self.shutdown_event.set()


app = None

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    print("\n\n⚠️  Received interrupt signal, shutting down gracefully...")
    if app:
        app.stop()

async def main():
    """Главная функция"""
    global app
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app = CVDCollectorApp()
    
    try:
        await app.start()
    except KeyboardInterrupt:
        app.stop()
    finally:
        print("\n✓ Application stopped cleanly")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Shutdown complete")