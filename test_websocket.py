#!/usr/bin/env python3
"""
Простой тест WebSocket для Binance Futures
Запуск: python test_websocket.py
Остановка: Ctrl+C
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_binance_websocket():
    """Подключение к Binance Futures WebSocket и вывод трейдов"""
    
    # WebSocket URL для aggTrades BTC/USDT Futures
    url = "wss://fstream.binance.com/ws/btcusdt@aggTrade"
    
    print("="*60)
    print("Connecting to Binance Futures WebSocket...")
    print("Symbol: BTCUSDT")
    print("Stream: aggTrade (aggregated trades)")
    print("="*60)
    print()
    
    trade_count = 0
    start_time = asyncio.get_event_loop().time()
    
    try:
        async with websockets.connect(url) as websocket:
            print("✓ Connected! Receiving trades...\n")
            
            while True:
                # Получаем сообщение
                message = await websocket.recv()
                data = json.loads(message)
                
                trade_count += 1
                
                # Парсим данные
                price = float(data['p'])
                quantity = float(data['q'])
                side = 'SELL' if data['m'] else 'BUY'
                timestamp = data['T']
                
                # Время
                dt = datetime.fromtimestamp(timestamp / 1000)
                time_str = dt.strftime('%H:%M:%S.%f')[:-3]
                
                # Выводим каждый 10-й трейд для читаемости
                if trade_count % 10 == 0:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    rate = trade_count / elapsed if elapsed > 0 else 0
                    
                    print(f"[{time_str}] #{trade_count:5d} | "
                          f"{side:4} | Price: ${price:,.2f} | "
                          f"Qty: {quantity:8.5f} BTC | "
                          f"Rate: {rate:.1f} trades/sec")
                
    except websockets.exceptions.ConnectionClosed:
        print("\n✗ Connection closed")
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
        elapsed = asyncio.get_event_loop().time() - start_time
        print(f"\nStatistics:")
        print(f"  Total trades: {trade_count}")
        print(f"  Duration: {elapsed:.1f} seconds")
        print(f"  Average rate: {trade_count/elapsed:.1f} trades/sec")
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_binance_websocket())
