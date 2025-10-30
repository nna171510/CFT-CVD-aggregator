from database import Database
from typing import Dict, List
import pandas as pd

class CVDCalculator:
    def __init__(self):
        self.db = Database()
    
    def get_cvd_chart_data(self, exchange: str, market_type: str, symbol: str, 
                           limit: int = 288) -> Dict:
        """
        Получить данные для графика CVD
        limit=288 = последние 24 часа (24*12 = 288 интервалов по 5 минут)
        limit=2016 = последняя неделя (7*24*12 = 2016)
        """
        data = self.db.get_cvd_data(exchange, market_type, symbol, limit)
        
        if not data:
            return {
                'error': 'No data available',
                'exchange': exchange,
                'market_type': market_type,
                'symbol': symbol
            }
        
        # Преобразуем в более удобный формат
        df = pd.DataFrame(data)
        
        # Сортируем по времени
        df = df.sort_values('timestamp')
        
        # Форматируем timestamp для графика
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Извлекаем вложенные данные
        buy_volumes = []
        sell_volumes = []
        total_volumes = []
        trades_counts = []
        
        for item in df['volume_delta_5m']:
            buy_volumes.append(item['buy_volume'])
            sell_volumes.append(item['sell_volume'])
            total_volumes.append(item['total_volume'])
            trades_counts.append(item['trades_count'])
        
        return {
            'exchange': exchange,
            'market_type': market_type,
            'symbol': symbol,
            'interval': '5m',
            'data': {
                'timestamps': df['datetime'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
                'cvd': df['cvd'].tolist(),
                'delta': df['delta'].tolist(),
                'buy_volume': buy_volumes,
                'sell_volume': sell_volumes,
                'total_volume': total_volumes,
                'trades_count': trades_counts
            },
            'stats': {
                'latest_cvd': float(df['cvd'].iloc[-1]),
                'cvd_change_24h': float(df['cvd'].iloc[-1] - df['cvd'].iloc[-288]) if len(df) >= 288 else 0,
                'cvd_change_1h': float(df['cvd'].iloc[-1] - df['cvd'].iloc[-12]) if len(df) >= 12 else 0,
                'total_buy_volume_24h': sum(buy_volumes[-288:]) if len(buy_volumes) >= 288 else sum(buy_volumes),
                'total_sell_volume_24h': sum(sell_volumes[-288:]) if len(sell_volumes) >= 288 else sum(sell_volumes),
                'avg_delta': float(df['delta'].mean()),
                'max_cvd': float(df['cvd'].max()),
                'min_cvd': float(df['cvd'].min()),
                'data_points': len(df)
            }
        }
    
    def compare_exchanges(self, symbol: str = 'BTCUSDT', market_type: str = 'spot') -> Dict:
        """Сравнить CVD между биржами для BTC"""
        exchanges = ['binance', 'bybit', 'okx', 'coinbase']
        comparison = {}
        
        for exchange in exchanges:
            data = self.get_cvd_chart_data(exchange, market_type, symbol, limit=288)
            if 'error' not in data:
                comparison[exchange] = {
                    'latest_cvd': data['stats']['latest_cvd'],
                    'cvd_change_24h': data['stats']['cvd_change_24h'],
                    'cvd_change_1h': data['stats']['cvd_change_1h'],
                    'buy_volume_24h': data['stats']['total_buy_volume_24h'],
                    'sell_volume_24h': data['stats']['total_sell_volume_24h']
                }
        
        # Добавляем Hyperliquid perpetual
        data = self.get_cvd_chart_data('hyperliquid', 'perpetual', symbol, limit=288)
        if 'error' not in data:
            comparison['hyperliquid_perp'] = {
                'latest_cvd': data['stats']['latest_cvd'],
                'cvd_change_24h': data['stats']['cvd_change_24h'],
                'cvd_change_1h': data['stats']['cvd_change_1h'],
                'buy_volume_24h': data['stats']['total_buy_volume_24h'],
                'sell_volume_24h': data['stats']['total_sell_volume_24h']
            }
        
        return {
            'symbol': symbol,
            'market_type': market_type,
            'comparison': comparison
        }
    
    def get_divergence_signals(self, exchange: str, market_type: str, 
                               symbol: str, intervals: int = 288) -> List[Dict]:
        """
        Найти дивергенции между CVD и ценой
        intervals=288 = последние 24 часа по 5 минут
        """
        data = self.db.get_cvd_data(exchange, market_type, symbol, limit=intervals)
        
        if len(data) < 10:
            return []
        
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp')
        
        signals = []
        
        # Ищем сильные изменения в дельте
        df['delta_change'] = df['delta'].pct_change()
        
        # Сигнал: резкое изменение дельты (>50%)
        strong_changes = df[abs(df['delta_change']) > 0.5]
        
        for idx, row in strong_changes.iterrows():
            signals.append({
                'timestamp': row['timestamp'],
                'datetime': pd.to_datetime(row['timestamp'], unit='ms').strftime('%Y-%m-%d %H:%M'),
                'delta': float(row['delta']),
                'delta_change': float(row['delta_change']),
                'cvd': float(row['cvd']),
                'type': 'strong_buying' if row['delta'] > 0 else 'strong_selling'
            })
        
        return signals