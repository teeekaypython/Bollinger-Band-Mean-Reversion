import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === CONFIG ===
SYMBOLS = ["XAUUSD", "BTCUSD",   "Volatility 75 Index", "Volatility 100 Index", "BTCUSD", "ETHUSD",
    "Jump 25 Index", "Jump 50 Index", "Jump 75 Index", "Jump 100 Index",
    "Boom 500 Index", "Crash 300 Index", "Range Break 100 Index",
    "Volatility 15 (1s) Index", "Volatility 50 (1s) Index",
    "Volatility 100 (1s) Index", "Gold RSI Pullback Index",
    "XPBUSD", "DEX 1500 UP Index", "China H Shares", "Japan 225",
    "Vol over Crash 400", "Vol over Crash 750", "Vol over Boom 400"]
TIMEFRAME = mt5.TIMEFRAME_M15
BARS = 3000
INITIAL_BALANCE = 10000
RISK_PER_TRADE = 0.01
BB_PERIOD = 20
BB_STDDEV = 2

# === INIT ===
if not mt5.initialize():
    raise RuntimeError("MT5 failed to initialize")

# === UTILITY FUNCTIONS ===
def get_data(symbol, timeframe, bars):
    data = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if data is None or len(data) == 0:
        raise RuntimeError(f"No data for {symbol}")
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def add_bollinger_bands(df, period=20, stddev=2):
    df['SMA'] = df['close'].rolling(window=period).mean()
    df['STD'] = df['close'].rolling(window=period).std()
    df['Upper'] = df['SMA'] + stddev * df['STD']
    df['Lower'] = df['SMA'] - stddev * df['STD']
    return df

def backtest_bollinger(df):
    balance = INITIAL_BALANCE
    equity_curve = [balance]
    wins, losses = 0, 0

    for i in range(BB_PERIOD + 1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # Entry conditions
        signal = None
        if prev['close'] < prev['Lower']:
            signal = 'buy'
            entry = row['close']
            sl = row['close'] - (prev['SMA'] - prev['Lower'])  # same as band width
            tp = prev['SMA']
        elif prev['close'] > prev['Upper']:
            signal = 'sell'
            entry = row['close']
            sl = row['close'] + (prev['Upper'] - prev['SMA'])
            tp = prev['SMA']

        if signal:
            # Simulate future bars to check SL or TP hit
            for j in range(i + 1, len(df)):
                h = df['high'].iloc[j]
                l = df['low'].iloc[j]
                c = df['close'].iloc[j]

                if signal == 'buy':
                    if l <= sl:
                        balance -= balance * RISK_PER_TRADE
                        losses += 1
                        break
                    elif c >= tp:
                        balance += balance * RISK_PER_TRADE
                        wins += 1
                        break
                else:  # sell
                    if h >= sl:
                        balance -= balance * RISK_PER_TRADE
                        losses += 1
                        break
                    elif c <= tp:
                        balance += balance * RISK_PER_TRADE
                        wins += 1
                        break

            equity_curve.append(balance)

    total = wins + losses
    winrate = wins / total if total > 0 else 0
    return {
        'equity': equity_curve,
        'final_balance': balance,
        'wins': wins,
        'losses': losses,
        'winrate': winrate
    }

def plot_equity(equity_curve, symbol):
    plt.plot(equity_curve, label=symbol)
    plt.title(f'Equity Curve - {symbol}')
    plt.xlabel('Trades')
    plt.ylabel('Balance')
    plt.grid(True)
    plt.legend()
    plt.show()

# === MAIN LOOP ===
for symbol in SYMBOLS:
    print(f"\nRunning Bollinger Band mean-reversion backtest for {symbol}")
    try:
        df = get_data(symbol, TIMEFRAME, BARS)
        df = add_bollinger_bands(df, BB_PERIOD, BB_STDDEV)
        result = backtest_bollinger(df)

        print(f"Final Balance: ${result['final_balance']:.2f}")
        print(f"Trades: {result['wins'] + result['losses']} | Wins: {result['wins']} | Losses: {result['losses']} | Win Rate: {result['winrate']:.2%}")
        plot_equity(result['equity'], symbol)

    except Exception as e:
        print(f"Error with {symbol}: {e}")

mt5.shutdown()
