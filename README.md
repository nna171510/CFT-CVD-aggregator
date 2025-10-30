# CVD (Cumulative Volume Delta) Collector

Система для сбора, агрегации и расчета Cumulative Volume Delta с криптовалютных бирж.

## Поддерживаемые биржи

- Binance (Spot + Futures)
- Bybit (Spot + Futures)  
- OKX (Spot + Futures)
- Coinbase (Spot)

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте `.env` файл по образцу выше

3. Создайте таблицы в Supabase (SQL будет показан при запуске)

4. Запустите приложение:
```bash
python main.py
```

## Просмотр данных
```bash
# Просмотр CVD для Binance Spot BTC за последние 24 часа
python view_cvd.py binance spot BTCUSDT 24

# Просмотр CVD для Bybit Futures ETH за последние 48 часов
python view_cvd.py bybit futures ETHUSDT 48
```

## Как это работает

1. **Сбор данных** - каждые 30 секунд собираются сделки со всех бирж
2. **Агрегация** - каждый час данные агрегируются (buy volume, sell volume, delta)
3. **CVD расчет** - кумулятивная сумма дельты по всем часам

## Структура БД

- `trades` - сырые сделки
- `volume_delta_1h` - агрегированные данные по часам
- `cvd_1h` - кумулятивная дельта

## Конфигурация

Все настройки в файле `.env`:
- Учетные данные Supabase
- Интервалы сбора и агрегации
- Включение/отключение бирж
- Список символов для отслеживания