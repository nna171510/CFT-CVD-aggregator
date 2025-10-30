import time
from datetime import datetime, timezone
from typing import Dict, Any

def get_current_timestamp_ms() -> int:
    """Получить текущий timestamp в миллисекундах"""
    return int(time.time() * 1000)

def timestamp_to_datetime(timestamp_ms: int) -> str:
    """Конвертировать timestamp в читаемую дату"""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def format_volume(volume: float) -> str:
    """Форматировать объем для удобного отображения"""
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:.2f}M"
    elif volume >= 1_000:
        return f"{volume / 1_000:.2f}K"
    else:
        return f"{volume:.2f}"

def print_trade_summary(trades: list) -> None:
    """Вывести краткую информацию о собранных сделках"""
    if not trades:
        print("No trades collected")
        return
    
    by_exchange = {}
    for trade in trades:
        key = f"{trade['exchange']}_{trade['market_type']}"
        if key not in by_exchange:
            by_exchange[key] = []
        by_exchange[key].append(trade)
    
    print(f"\n{'='*80}")
    print(f"Trade Collection Summary - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*80}")
    
    for key, trade_list in by_exchange.items():
        exchange, market_type = key.split('_')
        buy_volume = sum(t['quantity'] for t in trade_list if t['side'] == 'buy')
        sell_volume = sum(t['quantity'] for t in trade_list if t['side'] == 'sell')
        delta = buy_volume - sell_volume
        
        print(f"{exchange:12} {market_type:10} BTC | "
              f"Trades: {len(trade_list):4} | "
              f"Buy: {format_volume(buy_volume):8} | "
              f"Sell: {format_volume(sell_volume):8} | "
              f"Delta: {format_volume(delta):8}")
    
    print(f"{'='*80}\n")

def validate_config() -> bool:
    """Проверить корректность конфигурации"""
    import config
    
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        print("✗ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False
    
    if not config.SYMBOLS:
        print("✗ Error: No symbols configured")
        return False
    
    print("✓ Configuration validated")
    print(f"  - Symbols: {', '.join(config.SYMBOLS)}")
    print(f"  - Collection interval: {config.COLLECTION_INTERVAL}s")
    print(f"  - Aggregation interval: {config.AGGREGATION_INTERVAL}s (5 minutes)")
    return True

def create_supabase_tables_sql() -> str:
    """Вернуть SQL для создания таблиц в Supabase (5-минутные интервалы)"""
    return """
-- Таблица для сырых сделок
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(20) NOT NULL,
    market_type VARCHAR(10) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    trade_id VARCHAR(50),
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    side VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(exchange, market_type, symbol, trade_id)
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades(exchange, market_type, symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);

-- Таблица для агрегированных данных (5 минут)
CREATE TABLE IF NOT EXISTS volume_delta_5m (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(20) NOT NULL,
    market_type VARCHAR(10) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    buy_volume DECIMAL(20, 8) NOT NULL,
    sell_volume DECIMAL(20, 8) NOT NULL,
    delta DECIMAL(20, 8) NOT NULL,
    total_volume DECIMAL(20, 8) NOT NULL,
    trades_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(exchange, market_type, symbol, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_delta_5m_symbol_time ON volume_delta_5m(exchange, market_type, symbol, timestamp);

-- Таблица для CVD (кумулятивная дельта, 5-минутные интервалы)
CREATE TABLE IF NOT EXISTS cvd_5m (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(20) NOT NULL,
    market_type VARCHAR(10) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    cvd DECIMAL(20, 8) NOT NULL,
    delta DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(exchange, market_type, symbol, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_cvd_5m_symbol_time ON cvd_5m(exchange, market_type, symbol, timestamp);
"""