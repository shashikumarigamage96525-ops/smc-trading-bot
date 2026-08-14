import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ============================================================
# ⚡ ULTIMATE INSTITUTIONAL TRADING TERMINAL V3.1
# ERROR-SAFE VERSION
# ============================================================

st.set_page_config(
    page_title="Institutional Trading Terminal V3.1",
    page_icon="⚡",
    layout="wide"
)

# ------------------------------------------------------------
# AUTO REFRESH
# ------------------------------------------------------------
st_autorefresh(
    interval=5000,
    limit=None,
    key="terminal_refresh"
)

# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
if "signal_history" not in st.session_state:
    st.session_state.signal_history = []

if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None


# ============================================================
# CONFIG
# ============================================================

BINANCE_API = "https://api.binance.com"
BINANCE_VISION = "https://data-api.binance.vision"

TIMEFRAMES = [
    "5m",
    "15m",
    "1h",
    "4h"
]

FALLBACK_COINS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "SUI/USDT",
    "PEPE/USDT",
    "1000RATS/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "NEAR/USDT",
    "RENDER/USDT",
    "FET/USDT",
    "INJ/USDT",
    "OP/USDT",
    "ARB/USDT",
    "DOT/USDT",
    "SHIB/USDT",
    "UNI/USDT",
    "APT/USDT"
]


# ============================================================
# SAFE API
# ============================================================

def safe_get(url, params=None, timeout=8):

    try:

        response = requests.get(
            url,
            params=params,
            timeout=timeout
        )

        if response.status_code == 200:
            return response.json()

    except Exception:
        return None

    return None


# ============================================================
# SAFE NUMBER
# ============================================================

def num(value, default=0.0):

    try:

        value = float(value)

        if np.isfinite(value):
            return value

    except Exception:
        pass

    return default


# ============================================================
# PRICE FORMAT
# ============================================================

def price_format(value):

    value = num(value)

    if value >= 1000:
        return f"{value:,.2f}"

    if value >= 1:
        return f"{value:,.4f}"

    if value >= 0.01:
        return f"{value:,.5f}"

    return f"{value:,.8f}"


# ============================================================
# COIN FETCHER
# ============================================================

@st.cache_data(ttl=3600)
def get_coins():

    data = safe_get(
        f"{BINANCE_API}/api/v3/exchangeInfo"
    )

    if isinstance(data, dict):

        result = []

        for item in data.get("symbols", []):

            try:

                if (
                    item.get("quoteAsset") == "USDT"
                    and item.get("status") == "TRADING"
                ):

                    symbol = item.get("symbol", "")

                    if symbol.endswith("USDT"):

                        result.append(
                            symbol[:-4] + "/USDT"
                        )

            except Exception:
                continue

        if result:
            return sorted(set(result))

    return sorted(FALLBACK_COINS)


# ============================================================
# OHLC DATA
# ============================================================

@st.cache_data(ttl=5)
def get_ohlcv(symbol, interval="15m", limit=500):

    clean_symbol = symbol.replace("/", "")

    params = {
        "symbol": clean_symbol,
        "interval": interval,
        "limit": int(limit)
    }

    data = safe_get(
        f"{BINANCE_API}/api/v3/klines",
        params=params
    )

    if not isinstance(data, list):

        data = safe_get(
            f"{BINANCE_VISION}/api/v3/klines",
            params=params
        )

    if not isinstance(data, list):
        return pd.DataFrame()

    if len(data) == 0:
        return pd.DataFrame()

    try:

        columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore"
        ]

        df = pd.DataFrame(
            data,
            columns=columns
        )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms",
            errors="coerce"
        )

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote"
        ]

        for column in numeric_columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        return df.reset_index(drop=True)

    except Exception:
        return pd.DataFrame()


# ============================================================
# INDICATORS
# ============================================================

def indicators(df):

    if df.empty:
        return df

    df = df.copy()

    # EMA
    df["EMA20"] = (
        df["close"]
        .ewm(span=20, adjust=False)
        .mean()
    )

    df["EMA50"] = (
        df["close"]
        .ewm(span=50, adjust=False)
        .mean()
    )

    df["EMA200"] = (
        df["close"]
        .ewm(span=200, adjust=False)
        .mean()
    )

    # True Range
    previous_close = df["close"].shift(1)

    tr1 = (
        df["high"] -
        df["low"]
    )

    tr2 = (
        df["high"] -
        previous_close
    ).abs()

    tr3 = (
        df["low"] -
        previous_close
    ).abs()

    df["TR"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["ATR"] = (
        df["TR"]
        .rolling(14, min_periods=1)
        .mean()
    )

    # RSI
    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = (
        gain
        .rolling(14, min_periods=14)
        .mean()
    )

    avg_loss = (
        loss
        .rolling(14, min_periods=14)
        .mean()
    )

    rs = (
        avg_gain /
        avg_loss.replace(0, np.nan)
    )

    df["RSI"] = (
        100 -
        (100 / (1 + rs))
    )

    df["RSI"] = (
        df["RSI"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(50)
    )

    # Relative Volume
    volume_ma = (
        df["volume"]
        .rolling(20, min_periods=1)
        .mean()
    )

    df["RVOL"] = (
        df["volume"] /
        volume_ma.replace(0, np.nan)
    )

    df["RVOL"] = (
        df["RVOL"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(1)
    )

    # Buy/Sell volume
    df["BUY_VOL"] = df["taker_buy_base"]

    df["SELL_VOL"] = (
        df["volume"] -
        df["taker_buy_base"]
    )

    return df


# ============================================================
# TREND
# ============================================================

def get_trend(df):

    if df.empty:
        return "UNKNOWN"

    df = indicators(df)

    if len(df) < 20:
        return "UNKNOWN"

    price = num(df["close"].iloc[-1])
    ema50 = num(df["EMA50"].iloc[-1])
    ema200 = num(df["EMA200"].iloc[-1])

    if price > ema50 and ema50 > ema200:
        return "BULLISH"

    if price < ema50 and ema50 < ema200:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# SWING POINTS
# ============================================================

def find_swings(df, window=3):

    if df.empty:
        return df

    df = df.copy()

    df["SWING_HIGH"] = False
    df["SWING_LOW"] = False

    if len(df) < (window * 2 + 1):
        return df

    for i in range(
        window,
        len(df) - window
    ):

        high_slice = df["high"].iloc[
            i - window:
            i + window + 1
        ]

        low_slice = df["low"].iloc[
            i - window:
            i + window + 1
        ]

        if df["high"].iloc[i] >= high_slice.max():
            df.loc[df.index[i], "SWING_HIGH"] = True

        if df["low"].iloc[i] <= low_slice.min():
            df.loc[df.index[i], "SWING_LOW"] = True

    return df


# ============================================================
# MARKET STRUCTURE
# ============================================================

def market_structure(df):

    result = {
        "event": "NONE",
        "direction": "NEUTRAL",
        "level": 0.0
    }

    if df.empty:
        return result

    df = find_swings(df)

    swing_highs = df[
        df["SWING_HIGH"]
    ]

    swing_lows = df[
        df["SWING_LOW"]
    ]

    current = num(
        df["close"].iloc[-1]
    )

    if not swing_highs.empty:

        level = num(
            swing_highs["high"].iloc[-1]
        )

        if current > level:

            return {
                "event": "BULLISH BOS",
                "direction": "BULLISH",
                "level": level
            }

    if not swing_lows.empty:

        level = num(
            swing_lows["low"].iloc[-1]
        )

        if current < level:

            return {
                "event": "BEARISH BOS",
                "direction": "BEARISH",
                "level": level
            }

    return result


# ============================================================
# LIQUIDITY SWEEP
# ============================================================

def liquidity_sweep(df):

    result = {
        "type": "NONE",
        "level": 0.0
    }

    if df.empty or len(df) < 15:
        return result

    previous = df.iloc[-2]

    high_level = num(
        df["high"].iloc[-12:-2].max()
    )

    low_level = num(
        df["low"].iloc[-12:-2].min()
    )

    if (
        previous["high"] > high_level
        and previous["close"] < high_level
    ):

        return {
            "type": "BUY-SIDE SWEEP",
            "level": high_level
        }

    if (
        previous["low"] < low_level
        and previous["close"] > low_level
    ):

        return {
            "type": "SELL-SIDE SWEEP",
            "level": low_level
        }

    return result


# ============================================================
# FVG
# ============================================================

def get_fvgs(df):

    bullish = []
    bearish = []

    if df.empty or len(df) < 3:
        return bullish, bearish

    for i in range(
        1,
        len(df) - 1
    ):

        left_high = num(
            df["high"].iloc[i - 1]
        )

        left_low = num(
            df["low"].iloc[i - 1]
        )

        right_high = num(
            df["high"].iloc[i + 1]
        )

        right_low = num(
            df["low"].iloc[i + 1]
        )

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
# ORDER BLOCK
# ============================================================

def get_order_blocks(df):

    bullish = []
    bearish = []

    if df.empty or len(df) < 5:
        return bullish, bearish

    for i in range(
        1,
        len(df) - 1
    ):

        current = df.iloc[i]
        nxt = df.iloc[i + 1]

        # Bullish OB
        if (
            current["close"] < current["open"]
            and nxt["close"] > current["high"]
        ):

            bullish.append({
                "type": "Bullish OB",
                "low": num(current["low"]),
                "high": num(current["open"]),
                "time": current["timestamp"]
            })

        # Bearish OB
        if (
            current["close"] > current["open"]
            and nxt["close"] < current["low"]
        ):

            bearish.append({
                "type": "Bearish OB",
                "low": num(current["open"]),
                "high": num(current["high"]),
                "time": current["timestamp"]
            })

    return bullish, bearish


# ============================================================
# ORDER BOOK
# ============================================================

def order_book(symbol):

    clean = symbol.replace("/", "")

    data = safe_get(
        f"{BINANCE_API}/api/v3/depth",
        params={
            "symbol": clean,
            "limit": 100
        }
    )

    default = {
        "bid": 50.0,
        "ask": 50.0,
        "imbalance": 0.0
    }

    if not isinstance(data, dict):
        return default

    try:

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if not bids or not asks:
            return default

        bid_total = 0.0
        ask_total = 0.0

        for index, item in enumerate(bids):

            quantity = num(
                item[1] if len(item) > 1 else 0
            )

            weight = 1 / (
                1 + index * 0.05
            )

            bid_total += (
                quantity *
                weight
            )

        for index, item in enumerate(asks):

            quantity = num(
                item[1] if len(item) > 1 else 0
            )

            weight = 1 / (
                1 + index * 0.05
            )

            ask_total += (
                quantity *
                weight
            )

        total = (
            bid_total +
            ask_total
        )

        if total <= 0:
            return default

        bid = (
            bid_total /
            total *
           
