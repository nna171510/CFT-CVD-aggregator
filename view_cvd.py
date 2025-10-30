#!/usr/bin/env python3
"""
Скрипт для быстрого просмотра CVD данных (5-минутные интервалы)
"""

import sys
from cvd_calculator import CVDCalculator
import json

def main():
    calc = CVDCalculator()
    
    # Параметры по умолчанию
    exchange = sys.argv[1] if len(sys.argv) > 1 else 'binance'
    market_type = sys.argv[2] if len(sys.argv) > 2 else 'spot'
    symbol = 'BTCUSDT'  # Только BTC
    intervals = int(sys.argv[3]) if len(sys.argv) > 3 else 288  # 24 часа = 288 интервалов по 5 минут
    
    print(f"\n{'='*80}")
    print(f"CVD Data Viewer (5-minute intervals)")
    print(f"{'='*80}")
    print(f"Exchange: {exchange}")
    print(f"Market Type: {market_type}")
    print(f"Symbol: {symbol}")
    print(f"Intervals: {intervals} (= {intervals*5/60:.1f} hours)")
    print(f"{'='*80}\n")
    
    # Получаем данные
    data = calc.get_cvd_chart_data(exchange, market_type, symbol, intervals)
    
    if 'error' in data:
        print(f"✗ {data['error']}")
        return
    
    # Выводим статистику
    print("Statistics:")
    print(f"  Latest CVD: {data['stats']['latest_cvd']:,.2f}")
    print(f"  CVD Change 24h: {data['stats']['cvd_change_24h']:,.2f}")
    print(f"  CVD Change 1h: {data['stats']['cvd_change_1h']:,.2f}")
    print(f"  Total Buy Volume 24h: {data['stats']['total_buy_volume_24h']:,.2f} BTC")
    print(f"  Total Sell Volume 24h: {data['stats']['total_sell_volume_24h']:,.2f} BTC")
    print(f"  Average Delta: {data['stats']['avg_delta']:,.2f}")
    print(f"  Max CVD: {data['stats']['max_cvd']:,.2f}")
    print(f"  Min CVD: {data['stats']['min_cvd']:,.2f}")
    print(f"  Data Points: {data['stats']['data_points']}")
    
    print(f"\n{'='*80}")
    print("Recent CVD values (last 20 intervals = ~100 minutes):")
    print(f"{'='*80}")
    
    # Выводим последние 20 значений
    display_count = min(20, len(data['data']['timestamps']))
    for i in range(display_count):
        idx = -(i+1)
        print(f"{data['data']['timestamps'][idx]:20} | "
              f"CVD: {data['data']['cvd'][idx]:12,.2f} | "
              f"Delta: {data['data']['delta'][idx]:10,.4f} | "
              f"Volume: {data['data']['total_volume'][idx]:10,.4f}")
    
    print(f"{'='*80}\n")
    
    # Ищем дивергенции
    print("Checking for signals...")
    signals = calc.get_divergence_signals(exchange, market_type, symbol, intervals)
    
    if signals:
        print(f"\n{'='*80}")
        print(f"Found {len(signals)} signals:")
        print(f"{'='*80}")
        for signal in signals[-10:]:  # Последние 10 сигналов
            print(f"{signal['datetime']:20} | "
                  f"Type: {signal['type']:20} | "
                  f"Delta: {signal['delta']:12,.4f} | "
                  f"Change: {signal['delta_change']*100:6.1f}%")
        print(f"{'='*80}\n")
    else:
        print("No significant signals found.\n")
    
    # Сравнение бирж
    print(f"\n{'='*80}")
    print("Comparing exchanges for BTC:")
    print(f"{'='*80}")
    comparison = calc.compare_exchanges('BTCUSDT', market_type)
    
    for exch, stats in comparison['comparison'].items():
        print(f"\n{exch.upper()}:")
        print(f"  Latest CVD: {stats['latest_cvd']:,.2f}")
        print(f"  24h Change: {stats['cvd_change_24h']:,.2f}")
        print(f"  1h Change: {stats['cvd_change_1h']:,.2f}")
        print(f"  Buy Volume 24h: {stats['buy_volume_24h']:,.2f} BTC")
        print(f"  Sell Volume 24h: {stats['sell_volume_24h']:,.2f} BTC")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()