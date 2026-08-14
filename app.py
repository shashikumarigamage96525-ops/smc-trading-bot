import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import time

# ============================================================
# ⚡ ULTIMATE INSTITUTIONAL TRADING TERMINAL V3
# Real Data + MTF + Liquidity + FVG + BOS/MSS + Backtest
# ============================================================

st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal V3",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# AUTO REFRESH
# ------------------------------------------------------------
st_autorefresh(
    interval=5000,
    limit=None,
    key="institutional_live_refresh"
)

# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "signal_history" not in st.session_state:
    st.session_state.signal_history = []

if "backtest_cache" not in st.session_state:
    st.session_state.backtest_cache = {}

# ============================================================
# CONSTANTS
# ============================================================

BINANCE_API = "https://api.binance.com"
BINANCE_VISION = "https://data-api.binance.vision"

STRATEGIES = {
    "Institutional Confluence": "HTF + Structure + Liquidity + FVG + Volume",
    "Liquidity Sweep + MSS": "Liquidity sweep followed by market structure shift",
    "FVG + Order Block": "Fair Value Gap and order-block confluence",
    "Trend Momentum": "EMA structure + RSI + volume confirmation"
}

TIMEFRAMES = ["5m", "15m", "1h", "4h"]

# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except:
        return default


def api_get(url, params=None, timeout=5):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


def format_price(price):
    price = safe_float(price)

    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:,.4f}"
    elif price >= 0.01:
        return f"{price:,.5f}"
    else:
        return f"{price:,.8f}"


# ============================================================
# COIN FETCHER
# ============================================================

@st.cache_data(ttl=3600)
def fetch_available_coins():
    data = api_get(
        f"{BINANCE_API}/api/v3/exchangeInfo",
        timeout=5
    )

    if data:
        symbols = []
        for s in data.get("symbols", []):
            if (
                s.get("quoteAsset") == "USDT"
                and s.get("status") == "TRADING"
                and s.get("isSpotTradingAllowed", True)
            ):
                symbols.append(
                    s["symbol"][:-4] + "/USDT"
                )
        if symbols:
            return sorted(set(symbols))

    return sorted([
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
        "ADA/USDT", "DOGE/USDT", "SUI/USDT", "PEPE/USDT", "1000RATS/USDT",
        "AVAX/USDT", "LINK/USDT", "NEAR/USDT", "RENDER/USDT", "FET/USDT",
        "INJ/USDT", "OP/USDT", "ARB/USDT", "DOT/USDT", "SHIB/USDT",
        "UNI/USDT", "APT/USDT"
    ])


# ============================================================
# TICKERS
# ============================================================

@st.cache_data(ttl=5)
def fetch_watchlist_tickers(symbols):
    data = api_get(
        f"{BINANCE_API}/api/v3/ticker/24hr",
        timeout=5
    )
    output = []
    if data:
        lookup = {
            x["symbol"]: x
            for x in data
        }
        for symbol in symbols:
            clean = symbol.replace("/", "")
            if clean in lookup:
                item = lookup[clean]
                output.append({
                    "Symbol": symbol,
                    "Price": safe_float(item["lastPrice"]),
                    "Change": safe_float(item["priceChangePercent"]),
                    "Volume": safe_float(item["quoteVolume"])
                })
    return output


# ============================================================
# OHLCV
# ============================================================

@st.cache_data(ttl=5)
def fetch_chart_data(symbol, timeframe="15m", limit=500):
    clean_symbol = symbol.replace("/", "")
    params = {
        "symbol": clean_symbol,
        "interval": timeframe,
        "limit": limit
    }

    data = api_get(
        f"{BINANCE_API}/api/v3/klines",
        params=params,
        timeout=8
    )

    if not isinstance(data, list):
        data = api_get(
            f"{BINANCE_VISION}/api/v3/klines",
            params=params,
            timeout=8
        )

    if not isinstance(data, list):
        return pd.DataFrame()

    try:
        df = pd.DataFrame(
            data,
            columns=[
                "timestamp", "open", "high", "low", "close",
                "volume", "close_time", "quote_volume", "trades",
                "taker_buy_base", "taker_buy_quote", "ignore"
            ]
        )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms"
        )

        numeric_cols = [
            "open", "high", "low", "close", "volume",
            "quote_volume", "trades", "taker_buy_base", "taker_buy_quote"
        ]

        for c in numeric_cols:
            df[c] = pd.to_numeric(
                df[c],
                errors="coerce"
            )

        return df.reset_index(drop=True)

    except:
        return pd.DataFrame()


# ============================================================
# INDICATORS
# ============================================================

def add_indicators(df):
    df = df.copy()
    if df.empty:
        return df

    # EMA
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["close"].ewm(span=200, adjust=False).mean()

    # ATR
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - prev_close)
    tr3 = abs(df["low"] - prev_close)

    df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = df["TR"].rolling(14).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(50)

    # Relative Volume
    df["VOL_MA20"] = df["volume"].rolling(20).mean()
    df["RVOL"] = (df["volume"] / df["VOL_MA20"].replace(0, np.nan))
    df["RVOL"] = df["RVOL"].replace([np.inf, -np.inf], np.nan).fillna(1)

    # Buy volume
    df["BUY_VOLUME"] = df["taker_buy_base"]
    df["SELL_VOLUME"] = df["volume"] - df["taker_buy_base"]
    df["BUY_SELL_RATIO"] = (df["BUY_VOLUME"] / df["SELL_VOLUME"].replace(0, np.nan))
    df["BUY_SELL_RATIO"] = df["BUY_SELL_RATIO"].replace([np.inf, -np.inf], np.nan).fillna(1)

    return df


# ============================================================
# SWING STRUCTURE
# ============================================================

def detect_structure(df, lookback=3):
    df = df.copy()
    df["SwingHigh"] = False
    df["SwingLow"] = False

    if len(df) < lookback * 2 + 2:
        return df

    for i in range(lookback, len(df) - lookback):
        high_window = df["high"].iloc[i-lookback:i+lookback+1]
        low_window = df["low"].iloc[i-lookback:i+lookback+1]

        if df["high"].iloc[i] == high_window.max():
            df.loc[df.index[i], "SwingHigh"] = True

        if df["low"].iloc[i] == low_window.min():
            df.loc[df.index[i], "SwingLow"] = True

    return df


# ============================================================
# BOS / MSS
# ============================================================

def detect_bos_mss(df):
    result = {
        "event": "NONE",
        "direction": "NEUTRAL",
        "level": None
    }

    if len(df) < 20:
        return result

    swing_highs = df[df["SwingHigh"]]
    swing_lows = df[df["SwingLow"]]
    current_close = df["close"].iloc[-1]

    if not swing_highs.empty:
        last_high = swing_highs["high"].iloc[-1]
        if current_close > last_high:
            result = {
                "event": "BULLISH BOS",
                "direction": "BULLISH",
                "level": last_high
            }

    if not swing_lows.empty:
        last_low = swing_lows["low"].iloc[-1]
        if current_close < last_low:
            result = {
                "event": "BEARISH BOS",
                "direction": "BEARISH",
                "level": last_low
            }

    # MSS approximation
    recent = df.tail(10)
    if len(recent) >= 5:
        old_close = recent["close"].iloc[0]
        if current_close > old_close and result["direction"] == "BULLISH":
            result["event"] = "BULLISH MSS / BOS"
        elif current_close < old_close and result["direction"] == "BEARISH":
            result["event"] = "BEARISH MSS / BOS"

    return result


# ============================================================
# LIQUIDITY SWEEP
# ============================================================

def detect_liquidity_sweep(df):
    result = {
        "type": "NONE",
        "level": None
    }

    if len(df) < 20:
        return result

    recent = df.iloc[-2]
    previous_high = df["high"].iloc[-12:-2].max()
    previous_low = df["low"].iloc[-12:-2].min()

    if recent["high"] > previous_high and recent["close"] < previous_high:
        return {
            "type": "BUY-SIDE LIQUIDITY SWEEP",
            "level": previous_high
        }

    if recent["low"] < previous_low and recent["close"] > previous_low:
        return {
            "type": "SELL-SIDE LIQUIDITY SWEEP",
            "level": previous_low
        }

    return result


# ============================================================
# FVG DETECTION
# ============================================================

def detect_fvgs(df):
    bullish = []
    bearish = []

    if len(df) < 3:
        return bullish, bearish

    for i in range(1, len(df) - 1):
        left_high = df["high"].iloc[i - 1]
        left_low = df["low"].iloc[i - 1]
        right_high = df["high"].iloc[i + 1]
        right_low = df["low"].iloc[i + 1]

        if right_low > left_high:
            bullish.append({
                "type": "Bullish FVG",
                "low": left_high,
                "high": right_low,
                "index": i,
                "time": df["timestamp"].iloc[i]
            })
        elif right_high < left_low:
            bearish.append({
                "type": "Bearish FVG",
                "low": right_high,
                "high": left_low,
                "index": i,
                "time": df["timestamp"].iloc[i]
            })

    return bullish, bearish


# ============================================================
# ORDER BLOCK APPROXIMATION
# ============================================================

def detect_order_blocks(df):
    bullish_ob = []
    bearish_ob = []

    if len(df) < 10:
        return bullish_ob, bearish_ob

    for i in range(2, len(df) - 2):
        current = df.iloc[i]
        next_candle = df.iloc[i + 1]

        if current["close"] < current["open"] and next_candle["close"] > current["high"]:
            bullish_ob.append({
                "type": "Bullish OB",
                "low": current["low"],
                "high": current["open"],
                "time": current["timestamp"]
            })

        if current["close"] > current["open"] and next_candle["close"] < current["low"]:
            bearish_ob.append({
                "type": "Bearish OB",
                "low": current["open"],
                "high": current["high"],
                "time": current["timestamp"]
            })

    return bullish_ob, bearish_ob


# ============================================================
# VOLUME PROFILE POC
# ============================================================

def calculate_poc(df, bins=30):
    try:
        if df.empty:
            return 0

        price_bins = pd.cut(df["close"], bins=bins)
        profile = df.groupby(price_bins, observed=False)["volume"].sum()

        if profile.empty:
            return float(df["close"].iloc[-1])

        poc_bin = profile.idxmax()
        return (poc_bin.left + poc_bin.right) / 2
    except:
        return float(df["close"].iloc[-1])


# ============================================================
# WEIGHTED ORDER BOOK
# ============================================================

def fetch_order_book(symbol):
    clean_symbol = symbol.replace("/", "")
    data = api_get(
        f"{BINANCE_API}/api/v3/depth",
        params={"symbol": clean_symbol, "limit": 100},
        timeout=5
    )

    if not data:
        return {
            "bid_pressure": 50,
            "ask_pressure": 50,
            "imbalance": 0,
            "best_bid": 0,
            "best_ask": 0
        }

    try:
        bids = np.array([[float(x[0]), float(x[1])] for x in data.get("bids", [])])
        asks = np.array([[float(x[0]), float(x[1])] for x in data.get("asks", [])])

        if len(bids) == 0 or len(asks) == 0:
            raise ValueError

        mid = (bids[0, 0] + asks[0, 0]) / 2
        distances = [0.001, 0.0025, 0.005, 0.01]

        weighted_bid = 0
        weighted_ask = 0

        for distance in distances:
            bid_mask = bids[:, 0] >= mid * (1 - distance)
            ask_mask = asks[:, 0] <= mid * (1 + distance)
            weight = 1 / distance

            weighted_bid += bids[bid_mask, 1].sum() * weight
            weighted_ask += asks[ask_mask, 1].sum() * weight

        total = weighted_bid + weighted_ask

        if total <= 0:
            bid_pressure = 50
            ask_pressure = 50
        else:
            bid_pressure = (weighted_bid / total) * 100
            ask_pressure = (weighted_ask / total) * 100

        return {
            "bid_pressure": bid_pressure,
            "ask_pressure": ask_pressure,
            "imbalance": bid_pressure - ask_pressure,
            "best_bid": bids[0, 0],
            "best_ask": asks[0, 0]
        }
    except:
        return {
            "bid_pressure": 50,
            "ask_pressure": 50,
            "imbalance": 0,
            "best_bid": 0,
            "best_ask": 0
        }


# ============================================================
# TREND
# ============================================================

def get_trend(df):
    if df.empty or len(df) < 50:
        return "NEUTRAL"

    df = add_indicators(df)
    price = df["close"].iloc[-1]
    ema50 = df["EMA50"].iloc[-1]
    ema200 = df["EMA200"].iloc[-1]

    if price > ema50 and ema50 > ema200:
        return "BULLISH"
    if price < ema50 and ema50 < ema200:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# SIGNAL SCORE
# ============================================================

def calculate_signal_score(
    df, trend_15m, trend_1h, trend_4h,
    orderbook, structure, sweep, fvgs, bullish_obs, bearish_obs
):
    if df.empty:
        return {"score": 0, "direction": "WAIT", "reasons": []}

    latest = df.iloc[-1]
    price = latest["close"]
    ema50 = latest["EMA50"]
    ema200 = latest["EMA200"]
    rsi = latest["RSI"]
    rvol = latest["RVOL"]

    long_score = 0
    short_score = 0
    long_reasons = []
    short_reasons = []

    # HTF TREND
    if trend_4h == "BULLISH":
        long_score += 20
        long_reasons.append("4H bullish")
    elif trend_4h == "BEARISH":
        short_score += 20
        short_reasons.append("4H bearish")

    if trend_1h == "BULLISH":
        long_score += 10
        long_reasons.append("1H bullish")
    elif trend_1h == "BEARISH":
        short_score += 10
        short_reasons.append("1H bearish")

    if trend_15m == "BULLISH":
        long_score += 10
    elif trend_15m == "BEARISH":
        short_score += 10

    # EMA
    if price > ema50 > ema200:
        long_score += 10
        long_reasons.append("EMA bullish structure")
    elif price < ema50 < ema200:
        short_score += 10
        short_reasons.append("EMA bearish structure")

    # RSI
    if 45 <= rsi <= 65 and price > ema50:
        long_score += 8
        long_reasons.append("RSI bullish zone")
    if 35 <= rsi <= 55 and price < ema50:
        short_score += 8
        short_reasons.append("RSI bearish zone")

    # VOLUME
    if rvol >= 1.3:
        if price > latest["open"]:
            long_score += 8
            long_reasons.append("Volume expansion")
        elif price < latest["open"]:
            short_score += 8
            short_reasons.append("Volume expansion")

    # ORDER BOOK
    if orderbook["bid_pressure"] >= 55:
        long_score += 7
        long_reasons.append("Bid pressure")
    if orderbook["ask_pressure"] >= 55:
        short_score += 7
        short_reasons.append("Ask pressure")

    # STRUCTURE
    if structure["direction"] == "BULLISH":
        long_score += 12
        long_reasons.append(structure["event"])
    elif structure["direction"] == "BEARISH":
        short_score += 12
        short_reasons.append(structure["event"])

    # LIQUIDITY SWEEP
    if sweep["type"] == "SELL-SIDE LIQUIDITY SWEEP":
        long_score += 10
        long_reasons.append("Sell-side liquidity sweep")
    elif sweep["type"] == "BUY-SIDE LIQUIDITY SWEEP":
        short_score += 10
        short_reasons.append("Buy-side liquidity sweep")

    # FVG
    if fvgs:
        last_fvg = fvgs[-1]
        if last_fvg["type"] == "Bullish FVG":
            long_score += 5
            long_reasons.append("Bullish FVG")
        elif last_fvg["type"] == "Bearish FVG":
            short_score += 5
            short_reasons.append("Bearish FVG")

    # ORDER BLOCK
    if bullish_obs:
        long_score += 5
        long_reasons.append("Bullish OB")
    if bearish_obs:
        short_score += 5
        short_reasons.append("Bearish OB")

    if long_score >= 70 and long_score > short_score:
        return {"score": min(long_score, 100), "direction": "LONG", "reasons": long_reasons}
    if short_score >= 70 and short_score > long_score:
        return {"score": min(short_score, 100), "direction": "SHORT", "reasons": short_reasons}

    if long_score > short_score:
        return {"score": long_score, "direction": "WAIT", "reasons": long_reasons}

    return {"score": short_score, "direction": "WAIT", "reasons": short_reasons}


# ============================================================
# ATR RISK ENGINE
# ============================================================

def calculate_trade_levels(entry, atr, direction, atr_multiplier):
    if atr <= 0:
        atr = entry * 0.01

    risk_distance = atr * atr_multiplier

    if direction == "LONG":
        sl = entry - risk_distance
        tp1 = entry + risk_distance * 1.5
        tp2 = entry + risk_distance * 2.5
        tp3 = entry + risk_distance * 4.0
    else:
        sl = entry + risk_distance
        tp1 = entry - risk_distance * 1.5
        tp2 = entry - risk_distance * 2.5
        tp3 = entry - risk_distance * 4.0

    return sl, tp1, tp2, tp3


# ============================================================
# REALISTIC BACKTEST
# ============================================================

def run_backtest(df, direction_mode="AUTO", risk_reward=1.5, ema_period=50):
    if df.empty or len(df) < 100:
        return {
            "trades": [], "win_rate": 0, "profit_factor": 0,
            "max_drawdown": 0, "net_r": 0, "equity": []
        }

    data = add_indicators(df.copy())
    trades = []
    equity = [0]
    current_r = 0

    for i in range(60, len(data) - 2):
        row = data.iloc[i]
        price = row["close"]
        ema = row["EMA50"]
        rsi = row["RSI"]
        rvol = row["RVOL"]

        direction = None
        if price > ema and 45 <= rsi <= 65 and rvol >= 1:
            direction = "LONG"
        elif price < ema and 35 <= rsi <= 55 and rvol >= 1:
            direction = "SHORT"

        if direction_mode != "AUTO":
            direction = direction_mode

        if direction is None:
            continue

        entry = price
        atr = row["ATR"]
        if pd.isna(atr) or atr <= 0:
            continue

        risk = atr * 1.5

        if direction == "LONG":
            sl = entry - risk
            tp = entry + risk * risk_reward
            future = data.iloc[i + 1:min(i + 21, len(data))]
            outcome = None
            for _, candle in future.iterrows():
                if candle["low"] <= sl:
                    outcome = -1
                    break
                if candle["high"] >= tp:
                    outcome = risk_reward
                    break
        else:
            sl = entry + risk
            tp = entry - risk * risk_reward
            future = data.iloc[i + 1:min(i + 21, len(data))]
            outcome = None
            for _, candle in future.iterrows():
                if candle["high"] >= sl:
                    outcome = -1
                    break
                if candle["low"] <= tp:
                    outcome = risk_reward
                    break

        if outcome is not None:
            current_r += outcome
            trades.append({
                "Time": row["timestamp"],
                "Direction": direction,
                "Entry": entry,
                "Result R": outcome
            })
            equity.append(current_r)

    if not trades:
        return {
            "trades": [], "win_rate": 0, "profit_factor": 0,
            "max_drawdown": 0, "net_r": 0, "equity": equity
        }

    results = [x["Result R"] for x in trades]
    wins = [x for x in results if x > 0]
    losses = [x for x in results if x < 0]

    win_rate = (len(wins) / len(results)) * 100
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    profit_factor = (gross_profit / gross_loss if gross_loss > 0 else 0)

    eq = np.array(equity)
    running_max = np.maximum.accumulate(eq)
    drawdown = eq - running_max
    max_drawdown = drawdown.min() if len(drawdown) else 0

    return {
        "trades": trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "net_r": current_r,
        "equity": equity
    }


# ============================================================
# WHALE / LARGE TRADE TRACKER
# ============================================================

@st.cache_data(ttl=5)
def fetch_large_trades(symbol, percentile=95):
    clean = symbol.replace("/", "")
    data = api_get(
        f"{BINANCE_API}/api/v3/trades",
        params={"symbol": clean, "limit": 500},
        timeout=5
    )

    if not data:
        return pd.DataFrame()

    rows = []
    sizes = []

    for t in data:
        price = safe_float(t.get("price"))
        qty = safe_float(t.get("qty"))
        notional = price * qty
        sizes.append(notional)

    if not sizes:
        return pd.DataFrame()

    threshold = np.percentile(sizes, percentile)

    for t in data:
        price = safe_float(t.get("price"))
        qty = safe_float(t.get("qty"))
        notional = price * qty

        if notional >= threshold:
            side = "SELL 🔴" if t.get("isBuyerMaker") else "BUY 🟢"
            rows.append({
                "Time": pd.to_datetime(t["time"], unit="ms").strftime("%H:%M:%S"),
                "Side": side,
                "Price": price,
                "Quantity": qty,
                "Notional ($)": notional
            })

    return pd.DataFrame(rows)


# ============================================================
# GATEKEEPER
# ============================================================

def gatekeeper(score, rrr, trend_4h, structure, orderbook):
    checks = {}
    checks["Signal Score >= 70"] = score >= 70
    checks["RRR >= 1.5"] = rrr >= 1.5
    checks["4H Trend Confirmed"] = trend_4h != "NEUTRAL"
    checks["Market Structure"] = structure["direction"] != "NEUTRAL"
    checks["Order Book Confirmation"] = abs(orderbook["imbalance"]) >= 5
    return checks


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    try:
        if (
            "telegram" not in st.secrets
            or "token" not in st.secrets["telegram"]
            or "chat_id" not in st.secrets["telegram"]
        ):
            return False

        token = st.secrets["telegram"]["token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": message},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False


# ============================================================
# HEADER
# ============================================================

st.title("⚡ Ultimate Institutional Trading Terminal V3")
st.caption(
    "Real Market Data • MTF Confluence • Liquidity • "
    "BOS/MSS • FVG • Order Blocks • Backtesting • Risk Engine"
)

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("🎛 Institutional Control Center")

all_symbols = fetch_available_coins()
default_symbol = "BTC/USDT" if "BTC/USDT" in all_symbols else all_symbols[0]

selected_coin = st.sidebar.selectbox(
    "🔍 Select Asset",
    all_symbols,
    index=all_symbols.index(default_symbol)
)

timeframe = st.sidebar.selectbox(
    "Execution Timeframe",
    TIMEFRAMES,
    index=1
)

strategy = st.sidebar.selectbox(
    "Strategy",
    list(STRATEGIES.keys())
)

st.sidebar.divider()

# ============================================================
# FETCH MAIN DATA
# ============================================================

df = fetch_chart_data(selected_coin, timeframe, 500)
df = add_indicators(df)
df = detect_structure(df)

if df.empty:
    st.error("❌ Market data unavailable. Please check Binance/API connection.")
    st.stop()

# ============================================================
# CURRENT MARKET
# ============================================================

live_price = df["close"].iloc[-1]
atr = df["ATR"].iloc[-1]

if pd.isna(atr) or atr <= 0:
    atr = live_price * 0.01

rsi = df["RSI"].iloc[-1]
rvol = df["RVOL"].iloc[-1]

ema20 = df["EMA20"].iloc[-1]
ema50 = df["EMA50"].iloc[-1]
ema200 = df["EMA200"].iloc[-1]

# ============================================================
# MTF (Multi-Timeframe Analysis)
# ============================================================

df15 = add_indicators(detect_structure(fetch_chart_data(selected_coin, "15m", 300)))
df1h = add_indicators(detect_structure(fetch_chart_data(selected_coin, "1h", 300)))
df4h = add_indicators(detect_structure(fetch_chart_data(selected_coin, "4h", 300)))

trend_15m = get_trend(df15)
trend_1h = get_trend(df1h)
trend_4h = get_trend(df4h)

orderbook = fetch_order_book(selected_coin)
structure = detect_bos_mss(df)
sweep = detect_liquidity_sweep(df)
fvgs_bull, fvgs_bear = detect_fvgs(df)
obs_bull, obs_bear = detect_order_blocks(df)
poc = calculate_poc(df)

all_fvgs = fvgs_bull + fvgs_bear

signal = calculate_signal_score(
    df, trend_15m, trend_1h, trend_4h,
    orderbook, structure, sweep, all_fvgs, obs_bull, obs_bear
)

# ============================================================
# DASHBOARD LAYOUT & METRICS
# ============================================================

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Live Price", format_price(live_price))
with col2:
    st.metric("RSI (14)", f"{rsi:.1f}")
with col3:
    st.metric("RVOL", f"{rvol:.2f}x")
with col4:
    st.metric("Volume POC", format_price(poc))
with col5:
    st.metric("Signal Score", f"{signal['score']}/100", signal["direction"])

st.divider()

# Main Chart Display
st.subheader(f"📊 {selected_coin} - {timeframe} Institutional Chart")

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df["timestamp"],
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    name="Price"
))

fig.add_trace(go.Scatter(x=df["timestamp"], y=df["EMA20"], line=dict(color="orange", width=1), name="EMA 20"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["EMA50"], line=dict(color="blue", width=1.5), name="EMA 50"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["EMA200"], line=dict(color="purple", width=2), name="EMA 200"))

fig.update_layout(
    height=600,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=10, b=10)
)

st.plotly_chart(fig, use_container_width=True)
