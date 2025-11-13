import requests
from typing import List, Dict, Any
import config
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        
        # Создаем session с retry механизмом
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def insert_trades(self, trades: List[Dict[str, Any]]) -> bool:
        """Вставка сделок в БД"""
        try:
            if not trades:
                return True
            
            upsert_headers = self.headers.copy()
            upsert_headers['Prefer'] = 'resolution=merge-duplicates,return=representation'  # изменено
            
            response = self.session.post(
                f"{self.url}/rest/v1/trades",
                json=trades,
                headers=upsert_headers,
                timeout=30
            )
            
            if response.status_code in [200, 201, 204]:
                inserted = len(response.json()) if response.text else 0
                duplicates = len(trades) - inserted
                print(f"✓ Processed {len(trades)} trades ({inserted} new, {duplicates} duplicates)")
                return True
            elif response.status_code == 409:
                print(f"✓ Processed {len(trades)} trades (0 new, {len(trades)} duplicates)")
                return True
            else:
                print(f"✗ Error inserting trades: {response.status_code} - {response.text}")
                return False
            
        except requests.exceptions.SSLError as e:
            print(f"✗ SSL Error inserting trades (will retry next cycle): {e}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Network error inserting trades: {e}")
            return False
        except Exception as e:
            print(f"✗ Error inserting trades: {e}")
            return False
    
    def get_last_trade_timestamp(self, exchange: str, market_type: str, symbol: str) -> int:
        """Получить timestamp последней сделки"""
        try:
            response = self.session.get(
                f"{self.url}/rest/v1/trades",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'select': 'timestamp',
                    'order': 'timestamp.desc',
                    'limit': 1
                },
                timeout=10
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
            # Получаем сделки за период
            response = self.session.get(
                f"{self.url}/rest/v1/trades",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'timestamp': f'gte.{start_time}',
                    'timestamp': f'lt.{end_time}',
                    'select': '*'
                },
                timeout=30
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
                'buy_volume': str(buy_volume),
                'sell_volume': str(sell_volume),
                'delta': str(delta),
                'total_volume': str(total_volume),
                'trades_count': len(trades)
            }
            
            upsert_headers = self.headers.copy()
            upsert_headers['Prefer'] = 'resolution=merge-duplicates,return=minimal'
            
            response = self.session.post(
                f"{self.url}/rest/v1/volume_delta_5m",
                json=agg_data,
                headers=upsert_headers,
                timeout=30
            )
            
            if response.status_code in [200, 201, 204, 409]:
                print(f"✓ Aggregated {len(trades)} trades for {exchange} {market_type} {symbol}")
                return True
            else:
                print(f"✗ Error aggregating: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            print(f"✗ Error aggregating: {e}")
            return False
    
    def calculate_cvd(self, exchange: str, market_type: str, symbol: str) -> bool:
        """
        Расчет CVD - инкрементально добавляет новые записи
        """
        try:
            print(f"🔄 Starting CVD calculation for {exchange} {market_type} {symbol}")
            
            # Получаем последнюю CVD запись для этой биржи
            last_cvd_response = self.session.get(
                f"{self.url}/rest/v1/cvd_5m",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'select': 'timestamp,cvd',
                    'order': 'timestamp.desc',
                    'limit': 1
                },
                timeout=30
            )
            
            last_cvd = 0
            last_timestamp = 0
            
            if last_cvd_response.status_code == 200:
                last_data = last_cvd_response.json()
                if last_data:
                    last_cvd = float(last_data[0]['cvd'])
                    last_timestamp = int(last_data[0]['timestamp'])
                    print(f"📊 Last CVD: {last_cvd:.4f} at timestamp {last_timestamp}")
            
            # Получаем все дельты ПОСЛЕ последнего обработанного timestamp
            response = self.session.get(
                f"{self.url}/rest/v1/volume_delta_5m",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'timestamp': f'gt.{last_timestamp}',  # больше чем последний
                    'select': 'timestamp,delta',
                    'order': 'timestamp.asc'
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"✗ Error fetching deltas: {response.status_code}")
                return True
            
            new_deltas = response.json()
            
            if not new_deltas:
                print(f"✓ No new deltas to process for {exchange} {market_type} {symbol}")
                return True
            
            print(f"📊 Found {len(new_deltas)} new delta records to process")
            
            # Считаем новые CVD записи инкрементально
            cvd = last_cvd
            new_cvd_records = []
            
            for row in new_deltas:
                cvd += float(row['delta'])
                new_cvd_records.append({
                    'exchange': exchange,
                    'market_type': market_type,
                    'symbol': symbol,
                    'timestamp': row['timestamp'],
                    'cvd': str(cvd),
                    'delta': str(row['delta'])
                })
            
            print(f"📈 Calculated {len(new_cvd_records)} new CVD records, current CVD: {cvd:.4f}")
            
            # Вставляем новые CVD записи батчами по 100
            if new_cvd_records:
                batch_size = 100
                total_inserted = 0
                
                for i in range(0, len(new_cvd_records), batch_size):
                    batch = new_cvd_records[i:i+batch_size]
                    
                    # Используем обычный INSERT
                    insert_headers = self.headers.copy()
                    insert_headers['Prefer'] = 'return=minimal'
                    
                    try:
                        response = self.session.post(
                            f"{self.url}/rest/v1/cvd_5m",
                            json=batch,
                            headers=insert_headers,
                            timeout=30
                        )
                        
                        if response.status_code in [200, 201, 204]:
                            total_inserted += len(batch)
                            print(f"  ✓ Batch {i//batch_size + 1}: inserted {len(batch)} records")
                        elif response.status_code == 409:
                            # Конфликт - записи уже существуют
                            print(f"  ⚠️  Batch {i//batch_size + 1}: records already exist (skipped)")
                            total_inserted += len(batch)
                        else:
                            print(f"  ✗ Batch {i//batch_size + 1} error: {response.status_code} - {response.text}")
                            
                    except Exception as e:
                        print(f"  ✗ Batch {i//batch_size + 1} exception: {e}")
                        continue
                
                print(f"✓ CVD calculation complete: {total_inserted}/{len(new_cvd_records)} records inserted")
            
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
            response = self.session.get(
                f"{self.url}/rest/v1/cvd_5m",
                headers=self.headers,
                params={
                    'exchange': f'eq.{exchange}',
                    'market_type': f'eq.{market_type}',
                    'symbol': f'eq.{symbol}',
                    'select': '*',
                    'order': 'timestamp.desc',
                    'limit': limit
                },
                timeout=30
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
                volume_response = self.session.get(
                    f"{self.url}/rest/v1/volume_delta_5m",
                    headers=self.headers,
                    params={
                        'exchange': f'eq.{exchange}',
                        'market_type': f'eq.{market_type}',
                        'symbol': f'eq.{symbol}',
                        'timestamp': f'eq.{cvd_row["timestamp"]}',
                        'select': 'buy_volume,sell_volume,total_volume,trades_count',
                        'limit': 1
                    },
                    timeout=10
                )
                
                if volume_response.status_code == 200:
                    volume_data = volume_response.json()
                    if volume_data:
                        cvd_row['volume_delta_5m'] = volume_data[0]
                        result.append(cvd_row)
            
            return result
            
        except Exception as e:
            print(f"✗ Error getting CVD data: {e}")
            return []
