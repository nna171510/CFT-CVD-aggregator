from supabase import create_client, Client
from typing import List, Dict, Any
import config

class Database:
    def __init__(self):
        self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    def insert_trades(self, trades: List[Dict[str, Any]]) -> bool:
        """Вставка сделок в БД"""
        try:
            if not trades:
                return True
            
            response = self.client.table('trades').upsert(
                trades,
                on_conflict='exchange,market_type,symbol,trade_id'
            ).execute()
            
            print(f"✓ Inserted {len(trades)} trades")
            return True
        except Exception as e:
            print(f"✗ Error inserting trades: {e}")
            return False
    
    def get_last_trade_timestamp(self, exchange: str, market_type: str, symbol: str) -> int:
        """Получить timestamp последней сделки"""
        try:
            response = self.client.table('trades')\
                .select('timestamp')\
                .eq('exchange', exchange)\
                .eq('market_type', market_type)\
                .eq('symbol', symbol)\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                return response.data[0]['timestamp']
            return 0
        except Exception as e:
            print(f"✗ Error getting last timestamp: {e}")
            return 0
    
    def aggregate_5min_delta(self, exchange: str, market_type: str, symbol: str, 
                             start_time: int, end_time: int) -> bool:
        """Агрегация дельты за 5 минут"""
        try:
            # Получаем сделки за период
            response = self.client.table('trades')\
                .select('*')\
                .eq('exchange', exchange)\
                .eq('market_type', market_type)\
                .eq('symbol', symbol)\
                .gte('timestamp', start_time)\
                .lt('timestamp', end_time)\
                .execute()
            
            if not response.data:
                return True
            
            trades = response.data
            buy_volume = sum(float(t['quantity']) for t in trades if t['side'] == 'buy')
            sell_volume = sum(float(t['quantity']) for t in trades if t['side'] == 'sell')
            delta = buy_volume - sell_volume
            total_volume = buy_volume + sell_volume
            
            # Округляем timestamp до начала 5-минутки
            interval_timestamp = (start_time // 300000) * 300000  # 300000ms = 5 минут
            
            # Вставляем агрегированные данные
            agg_data = {
                'exchange': exchange,
                'market_type': market_type,
                'symbol': symbol,
                'timestamp': interval_timestamp,
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'delta': delta,
                'total_volume': total_volume,
                'trades_count': len(trades)
            }
            
            self.client.table('volume_delta_5m').upsert(
                agg_data,
                on_conflict='exchange,market_type,symbol,timestamp'
            ).execute()
            
            print(f"✓ Aggregated {len(trades)} trades for {exchange} {market_type} {symbol}")
            return True
            
        except Exception as e:
            print(f"✗ Error aggregating: {e}")
            return False
    
    def calculate_cvd(self, exchange: str, market_type: str, symbol: str) -> bool:
        """Расчет CVD"""
        try:
            # Получаем все дельты по порядку
            response = self.client.table('volume_delta_5m')\
                .select('timestamp, delta')\
                .eq('exchange', exchange)\
                .eq('market_type', market_type)\
                .eq('symbol', symbol)\
                .order('timestamp', desc=False)\
                .execute()
            
            if not response.data:
                return True
            
            # Считаем кумулятивную сумму
            cvd = 0
            cvd_records = []
            
            for row in response.data:
                cvd += float(row['delta'])
                cvd_records.append({
                    'exchange': exchange,
                    'market_type': market_type,
                    'symbol': symbol,
                    'timestamp': row['timestamp'],
                    'cvd': cvd,
                    'delta': row['delta']
                })
            
            # Вставляем CVD
            if cvd_records:
                self.client.table('cvd_5m').upsert(
                    cvd_records,
                    on_conflict='exchange,market_type,symbol,timestamp'
                ).execute()
                
                print(f"✓ Calculated CVD for {exchange} {market_type} {symbol}: {cvd:.2f}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error calculating CVD: {e}")
            return False
    
    def get_cvd_data(self, exchange: str, market_type: str, symbol: str, 
                     limit: int = 288) -> List[Dict]:
        """
        Получить данные CVD для графика
        limit=288 = последние 24 часа (24*60/5 = 288 интервалов по 5 минут)
        """
        try:
            response = self.client.table('cvd_5m')\
                .select('*, volume_delta_5m!inner(buy_volume, sell_volume, total_volume, trades_count)')\
                .eq('exchange', exchange)\
                .eq('market_type', market_type)\
                .eq('symbol', symbol)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            print(f"✗ Error getting CVD data: {e}")
            return []