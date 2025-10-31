import requests
from typing import List, Dict, Any
import config

class Database:
    def __init__(self):
        self.url = config.SUPABASE_URL
        self.key = config.SUPABASE_KEY
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
    
    def insert_trades(self, trades: List[Dict[str, Any]]) -> bool:
        """Вставка сделок в БД"""
        try:
            if not trades:
                return True
            
            # Supabase upsert через POST с заголовком resolution=merge-duplicates
            upsert_headers = self.headers.copy()
            upsert_headers['Prefer'] = 'resolution=merge-duplicates'
            
            response = requests.post(
                f"{self.url}/rest/v1/trades",
                json=trades,
                headers=upsert_headers
            )
            
            if response.status_code in [200, 201, 204]:
                print(f"✓ Inserted {len(trades)} trades")
                return True
            else:
                print(f"✗ Error inserting trades: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Error inserting trades: {e}")
            return False
    
    def get_last_trade_timestamp(self, exchange: str, market_type: str, symbol: str) -> int:
        """Получить timestamp последней сделки"""
        try:
            response = requests.get(
                f"{self.url}/rest/v1/trades",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'select': 'timestamp',
                    'order': 'timestamp.desc',
                    'limit': 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]['timestamp']
            return 0
        except Exception as e:
            print(f"✗ Error getting last timestamp: {e}")
            return 0
    
    def aggregate_5min_delta(self, exchange: str, market_type: str, symbol: str, 
                             start_time: int, end_time: int) -> bool:
        """Агрегация дельты за 5 минут"""
        try:
            # Получаем сделки за период - нужно использовать два параметра с разными операторами
            response = requests.get(
                f"{self.url}/rest/v1/trades",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'timestamp': f'gte.{start_time}',
                    'timestamp': f'lt.{end_time}',
                    'select': '*'
                }
            )
            
            if response.status_code != 200:
                print(f"✗ Error fetching trades: {response.status_code}")
                return True
            
            trades = response.json()
            
            if not trades:
                return True
            
            buy_volume = sum(float(t['quantity']) for t in trades if t['side'] == 'buy')
            sell_volume = sum(float(t['quantity']) for t in trades if t['side'] == 'sell')
            delta = buy_volume - sell_volume
            total_volume = buy_volume + sell_volume
            
            # Округляем timestamp до начала 5-минутки
            interval_timestamp = (start_time // 300000) * 300000
            
            # Вставляем агрегированные данные
            agg_data = {
                'exchange': exchange,
                'market_type': market_type,
                'symbol': symbol,
                'timestamp': interval_timestamp,
                'buy_volume': str(buy_volume),  # Конвертируем в строку для DECIMAL
                'sell_volume': str(sell_volume),
                'delta': str(delta),
                'total_volume': str(total_volume),
                'trades_count': len(trades)
            }
            
            upsert_headers = self.headers.copy()
            upsert_headers['Prefer'] = 'resolution=merge-duplicates'
            
            response = requests.post(
                f"{self.url}/rest/v1/volume_delta_5m",
                json=agg_data,
                headers=upsert_headers
            )
            
            if response.status_code in [200, 201, 204]:
                print(f"✓ Aggregated {len(trades)} trades for {exchange} {market_type} {symbol}")
                return True
            else:
                print(f"✗ Error aggregating: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            print(f"✗ Error aggregating: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def calculate_cvd(self, exchange: str, market_type: str, symbol: str) -> bool:
        """Расчет CVD"""
        try:
            # Получаем все дельты по порядку
            response = requests.get(
                f"{self.url}/rest/v1/volume_delta_5m",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'select': 'timestamp,delta',
                    'order': 'timestamp.asc'
                }
            )
            
            if response.status_code != 200:
                print(f"✗ Error fetching deltas: {response.status_code}")
                return True
            
            data = response.json()
            
            if not data:
                return True
            
            # Считаем кумулятивную сумму
            cvd = 0
            cvd_records = []
            
            for row in data:
                cvd += float(row['delta'])
                cvd_records.append({
                    'exchange': exchange,
                    'market_type': market_type,
                    'symbol': symbol,
                    'timestamp': row['timestamp'],
                    'cvd': str(cvd),  # Конвертируем в строку для DECIMAL
                    'delta': str(row['delta'])
                })
            
            # Вставляем CVD батчами по 100 записей
            if cvd_records:
                batch_size = 100
                for i in range(0, len(cvd_records), batch_size):
                    batch = cvd_records[i:i+batch_size]
                    
                    upsert_headers = self.headers.copy()
                    upsert_headers['Prefer'] = 'resolution=merge-duplicates'
                    
                    response = requests.post(
                        f"{self.url}/rest/v1/cvd_5m",
                        json=batch,
                        headers=upsert_headers
                    )
                    
                    if response.status_code not in [200, 201, 204]:
                        print(f"✗ Error calculating CVD batch: {response.status_code} - {response.text}")
                        return False
                
                print(f"✓ Calculated CVD for {exchange} {market_type} {symbol}: {cvd:.2f}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error calculating CVD: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_cvd_data(self, exchange: str, market_type: str, symbol: str, 
                     limit: int = 288) -> List[Dict]:
        """
        Получить данные CVD для графика
        limit=288 = последние 24 часа (24*60/5 = 288 интервалов по 5 минут)
        """
        try:
            # Получаем CVD данные
            response = requests.get(
                f"{self.url}/rest/v1/cvd_5m",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'select': '*',
                    'order': 'timestamp.desc',
                    'limit': limit
                }
            )
            
            if response.status_code != 200:
                print(f"✗ Error fetching CVD: {response.status_code}")
                return []
            
            cvd_data = response.json()
            
            if not cvd_data:
                return []
            
            # Для каждой записи получаем соответствующие volume_delta
            result = []
            for cvd_row in cvd_data:
                volume_response = requests.get(
                    f"{self.url}/rest/v1/volume_delta_5m",
                    headers=self.headers,
                    params={
                        'exchange': f'eq.{exchange}',
                        'market_type': f'eq.{market_type}',
                        'symbol': f'eq.{symbol}',
                        'timestamp': f'eq.{cvd_row["timestamp"]}',
                        'select': 'buy_volume,sell_volume,total_volume,trades_count',
                        'limit': 1
                    }
                )
                
                if volume_response.status_code == 200:
                    volume_data = volume_response.json()
                    if volume_data:
                        cvd_row['volume_delta_5m'] = volume_data[0]
                        result.append(cvd_row)
            
            return result
            
        except Exception as e:
            print(f"✗ Error getting CVD data: {e}")
            import traceback
            traceback.print_exc()
            return []