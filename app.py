import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide",
)

# ============================================================
# SESSION STATE
# ============================================================
if "signal_history" not in st.session_state:
    st.session_state.signal_history = []

if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

# ============================================================
# BINANCE API
# ============================================================
BINANCE_API = "https://api.binance.com/api/v3"
VISION_API = "https://data-api.binance.vision/api/v3"


# ============================================================
# SAFE REQUEST FUNCTION
# ============================================================
def safe_get_json(url, params=None, timeout=6):
    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout
        )

        if response.status_code == 200:
            return response.json()

    except requests.RequestException:
        return None

    except Exception:
        return None

    return None


# ============================================================
# FETCH SYMBOLS
# ============================================================
@st.cache_data(ttl=1800)
def fetch_symbols():

    data = safe_get_json(
        f"{BINANCE_API}/exchangeInfo"
    )

    if isinstance(data, dict) and "symbols" in data:

        symbols = []

        for item in data["symbols"]:

            if (
                item.get("quoteAsset") == "USDT"
                and item.get("status") == "TRADING"
                and item.get("isSpotTradingAllowed", True)
            ):

                base = item.get("baseAsset", "")

                if base:
                    symbols.append(
                        f"{base}/USDT"
                    )

        if symbols:
            return sorted(set(symbols))

    # Fallback
    return [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "DOGE/USDT",
        "ADA/USDT",
        "SUI/USDT",
        "PEPE/USDT",
        "AVAX/USDT",
        "LINK/USDT",
        "NEAR/USDT",
        "RENDER/USDT",
        "INJ/USDT",
        "APT/USDT"
    ]


# ============================================================
# FETCH KLINES
# ============================================================
@st.cache_data(ttl=5)
def fetch_klines(symbol, interval, limit=200):

    clean_symbol = symbol.replace("/", "")

    params = {
        "symbol": clean_symbol,
        "interval": interval,
        "limit": limit
    }

    data = safe_get_json(
        f"{BINANCE_API}/klines",
        params=params
    )

    # Binance Vision fallback
    if not isinstance(data, list):
        data = safe_get_json(
            f"{VISION_API}/klines",
            params=params
        )

    if not isinstance(data, list):
        return pd.DataFrame()

    if len(data) < 10:
        return pd.DataFrame()

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

    try:

        df = pd.DataFrame(
            data,
            columns=columns
        )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms"
        )

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        for col in numeric_columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(
            subset=numeric_columns
        )

        df = df.reset_index(drop=True)

        return df

    except Exception:
        return pd.DataFrame()


# ============================================================
# FETCH TICKER
# ============================================================
@st.cache_data(ttl=5)
def fetch_ticker(symbol):

    clean_symbol = symbol.replace("/", "")

    data = safe_get_json(
        f"{BINANCE_API}/ticker/24hr",
        params={
            "symbol": clean_symbol
        },
        timeout=4
    )

    if isinstance(data, dict):

        try:

            return {
                "price": float(
                    data["lastPrice"]
                ),
                "change": float(
                    data.get(
                        "priceChangePercent",
                        0
                    )
                ),
                "volume": float(
                    data.get(
                        "quoteVolume",
                        0
                    )
                )
            }

        except Exception:
            pass

    return {
        "price": 0.0,
        "change": 0.0,
        "volume": 0.0
    }


# ============================================================
# ORDER BOOK
# ============================================================
@st.cache_data(ttl=5)
def fetch_orderbook(symbol):

    clean_symbol = symbol.replace("/", "")

    data = safe_get_json(
        f"{BINANCE_API}/depth",
        params={
            "symbol": clean_symbol,
            "limit": 50
        },
        timeout=4
    )

    if not isinstance(data, dict):
        return 50.0, 50.0

    try:

        bids = sum(
            float(x[1])
            for x in data.get("bids", [])
        )

        asks = sum(
            float(x[1])
            for x in data.get("asks", [])
        )

        total = bids + asks

        if total <= 0:
            return 50.0, 50.0

        bid_pressure = (
            bids / total
        ) * 100

        ask_pressure = (
            asks / total
        ) * 100

        return bid_pressure, ask_pressure

    except Exception:
        return 50.0, 50.0


# ============================================================
# LARGE TRADES
# ============================================================
@st.cache_data(ttl=5)
def fetch_large_trades(
    symbol,
    threshold=5000
):

    clean_symbol = symbol.replace("/", "")

    data = safe_get_json(
        f"{BINANCE_API}/trades",
        params={
            "symbol": clean_symbol,
            "limit": 100
        },
        timeout=4
    )

    rows = []

    if isinstance(data, list):

        for trade in data:

            try:

                price = float(
                    trade["price"]
                )

                qty = float(
                    trade["qty"]
                )

                value = price * qty

                if value >= threshold:

                    if trade.get(
                        "isBuyerMaker"
                    ):
                        side = "SELL 🔴"
                    else:
                        side = "BUY 🟢"

                    rows.append(
                        {
                            "Time": pd.to_datetime(
                                trade["time"],
                                unit="ms"
                            ).strftime(
                                "%H:%M:%S"
                            ),
                            "Side": side,
                            "Price": price,
                            "Qty": qty,
                            "Value ($)": value
                        }
                    )

            except Exception:
                continue

    return pd.DataFrame(rows)


# ============================================================
# INDICATORS
# ============================================================
def add_indicators(df):

    df = df.copy()

    # EMA
    df["EMA50"] = (
        df["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    df["EMA200"] = (
        df["close"]
        .ewm(
            span=200,
            adjust=False
        )
        .mean()
    )

    # ATR
    previous_close = df["close"].shift(1)

    tr1 = (
        df["high"]
        - df["low"]
    )

    tr2 = (
        df["high"]
        - previous_close
    ).abs()

    tr3 = (
        df["low"]
        - previous_close
    ).abs()

    true_range = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1)

    df["ATR"] = (
        true_range
        .rolling(14)
        .mean()
    )

    # RSI
    delta = df["close"].diff()

    gain = (
        delta.clip(lower=0)
        .rolling(14)
        .mean()
    )

    loss = (
        (-delta.clip(upper=0))
        .rolling(14)
        .mean()
    )

    rs = gain / loss.replace(
        0,
        np.nan
    )

    df["RSI"] = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    df["RSI"] = (
        df["RSI"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(50)
    )

    # Volume average
    df["VOL_MA20"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    return df


# ============================================================
# CANDLE PATTERN
# ============================================================
def detect_pattern(df):

    if len(df) < 2:
        return "Neutral"

    previous = df.iloc[-2]
    current = df.iloc[-1]

    # Bullish engulfing
    if (
        current["close"]
        > current["open"]
        and previous["close"]
        < previous["open"]
        and current["close"]
        >= previous["open"]
        and current["open"]
        <= previous["close"]
    ):

        return "Bullish Engulfing 🟢"

    # Bearish engulfing
    if (
        current["close"]
        < current["open"]
        and previous["close"]
        > previous["open"]
        and current["close"]
        <= previous["open"]
        and current["open"]
        >= previous["close"]
    ):

        return "Bearish Engulfing 🔴"

    body = abs(
        current["close"]
        - current["open"]
    )

    candle_range = (
        current["high"]
        - current["low"]
    )

    if candle_range > 0:

        upper_shadow = (
            current["high"]
            - max(
                current["open"],
                current["close"]
            )
        )

        lower_shadow = (
            min(
                current["open"],
                current["close"]
            )
            - current["low"]
        )

        if (
            lower_shadow > body * 2
            and upper_shadow < body
        ):

            return "Hammer 🟢"

        if (
            upper_shadow > body * 2
            and lower_shadow < body
        ):

            return "Shooting Star 🔴"

    return "Neutral"


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================
def find_levels(df):

    recent = df.tail(
        min(80, len(df))
    )

    support = float(
        recent["low"].min()
    )

    resistance = float(
        recent["high"].max()
    )

    return support, resistance


# ============================================================
# VOLUME PROFILE POC
# ============================================================
def volume_poc(
    df,
    bins=25
):

    try:

        if (
            df["close"]
            .nunique()
            < 2
        ):

            return float(
                df["close"].iloc[-1]
            )

        price_bins = pd.cut(
            df["close"],
            bins=bins
        )

        profile = (
            df.groupby(
                price_bins,
                observed=False
            )["volume"]
            .sum()
        )

        if profile.empty:
            return float(
                df["close"].iloc[-1]
            )

        best_bin = profile.idxmax()

        if pd.isna(best_bin):
            return float(
                df["close"].iloc[-1]
            )

        return float(
            (
                best_bin.left
                + best_bin.right
            ) / 2
        )

    except Exception:

        return float(
            df["close"].iloc[-1]
        )


# ============================================================
# FAIR VALUE GAP
# ============================================================
def detect_fvg(df):

    if len(df) < 3:
        return None

    for i in range(
        len(df) - 2,
        0,
        -1
    ):

        left = df.iloc[i - 1]
        right = df.iloc[i + 1]

        # Bullish FVG
        if (
            right["low"]
            > left["high"]
        ):

            return {
                "type": "Bullish FVG",
                "low": float(
                    left["high"]
                ),
                "high": float(
                    right["low"]
                )
            }

        # Bearish FVG
        if (
            right["high"]
            < left["low"]
        ):

            return {
                "type": "Bearish FVG",
                "low": float(
                    right["high"]
                ),
                "high": float(
                    left["low"]
                )
            }

    return None


# ============================================================
# TREND
# ============================================================
def get_trend(df):

    if (
        df.empty
        or len(df) < 50
    ):

        return "UNKNOWN ⚪"

    ema50 = (
        df["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
        .iloc[-1]
    )

    price = df["close"].iloc[-1]

    if price >= ema50:
        return "BULLISH 🟢"

    return "BEARISH 🔴"


# ============================================================
# SIGNAL ENGINE
# ============================================================
def signal_engine(
    price,
    ema50,
    rsi,
    bid,
    ask,
    trend4h,
    rrr
):

    bullish = (
        price > ema50
        and bid > 52
        and "BULLISH" in trend4h
        and 40 <= rsi <= 65
        and rrr >= 1.5
    )

    bearish = (
        price < ema50
        and ask > 52
        and "BEARISH" in trend4h
        and 35 <= rsi <= 60
        and rrr >= 1.5
    )

    if bullish:

        return (
            "LONG 🟢",
            "Bullish confluence confirmed"
        )

    if bearish:

        return (
            "SHORT 🔴",
            "Bearish confluence confirmed"
        )

    return (
        "WAIT ⏳",
        "Market confluence is not strong enough"
    )


# ============================================================
# HEADER
# ============================================================
st.title(
    "⚡ Ultimate Institutional Trading Terminal"
)

st.caption(
    "Binance Public Market Data • "
    "Technical Analysis • "
    "Risk Planning • "
    "Signal Journal"
)


# ============================================================
# REFRESH
# ============================================================
if st.sidebar.button(
    "🔄 Refresh Market Data"
):

    st.cache_data.clear()
    st.rerun()


# ============================================================
# SIDEBAR ASSET
# ============================================================
symbols = fetch_symbols()

if not symbols:

    st.error(
        "No trading symbols available."
    )

    st.stop()


if "BTC/USDT" in symbols:
    default_symbol = "BTC/USDT"
else:
    default_symbol = symbols[0]


selected_coin = st.sidebar.selectbox(
    "🔍 Select Asset",
    symbols,
    index=symbols.index(
        default_symbol
    )
)


timeframe = st.sidebar.selectbox(
    "⏱ Execution Timeframe",
    [
        "5m",
        "15m",
        "1h",
        "4h"
    ],
    index=1
)


# ============================================================
# RISK SETTINGS
# ============================================================
st.sidebar.divider()

st.sidebar.subheader(
    "💰 Risk Management"
)


account_balance = st.sidebar.number_input(
    "Account Balance ($)",
    min_value=10.0,
    value=1000.0,
    step=100.0
)


risk_percentage = st.sidebar.slider(
    "Risk Per Trade (%)",
    min_value=0.5,
    max_value=5.0,
    value=1.0,
    step=0.5
)


trade_direction = st.sidebar.radio(
    "Trade Direction",
    [
        "LONG 🟢",
        "SHORT 🔴"
    ],
    horizontal=True
)


use_atr = st.sidebar.checkbox(
    "Use ATR SL / TP",
    value=True
)


atr_multiplier = st.sidebar.slider(
    "ATR Multiplier",
    min_value=1.0,
    max_value=4.0,
    value=2.0,
    step=0.5
)


# ============================================================
# MAIN DATA
# ============================================================
df = fetch_klines(
    selected_coin,
    timeframe,
    200
)


if df.empty:

    st.error(
        "⚠️ Binance market data could not be loaded."
    )

    st.info(
        "Press 'Refresh Market Data' and try again."
    )

    st.stop()


df = add_indicators(df)


# ============================================================
# CURRENT VALUES
# ============================================================
live_price = float(
    df["close"].iloc[-1]
)

ema50 = float(
    df["EMA50"].iloc[-1]
)

ema200 = float(
    df["EMA200"].iloc[-1]
)

rsi_value = float(
    df["RSI"].iloc[-1]
)

atr_value = float(
    df["ATR"].iloc[-1]
)


if (
    not np.isfinite(atr_value)
    or atr_value <= 0
):

    atr_value = (
        live_price * 0.01
    )


support, resistance = find_levels(df)

poc_price = volume_poc(df)

candle_pattern = detect_pattern(df)

fvg = detect_fvg(df)


# ============================================================
# MTF DATA
# ============================================================
df15 = fetch_klines(
    selected_coin,
    "15m",
    100
)

df1h = fetch_klines(
    selected_coin,
    "1h",
    100
)

df4h = fetch_klines(
    selected_coin,
    "4h",
    100
)


if not df15.empty:
    df15 = add_indicators(df15)

if not df1h.empty:
    df1h = add_indicators(df1h)

if not df4h.empty:
    df4h = add_indicators(df4h)


trend15 = get_trend(df15)

trend1h = get_trend(df1h)

trend4h = get_trend(df4h)


# ============================================================
# ORDER BOOK
# ============================================================
bid_pressure, ask_pressure = fetch_orderbook(
    selected_coin
)


# ============================================================
# TRADE LEVELS
# ============================================================
if "LONG" in trade_direction:

    default_entry = live_price

    default_sl = (
        live_price
        - atr_value * atr_multiplier
    )

    default_tp1 = (
        live_price
        + atr_value
        * atr_multiplier
        * 1.5
    )

    default_tp2 = (
        live_price
        + atr_value
        * atr_multiplier
        * 2.5
    )

    default_tp3 = (
        live_price
        + atr_value
        * atr_multiplier
        * 4.0
    )

else:

    default_entry = live_price

    default_sl = (
        live_price
        + atr_value * atr_multiplier
    )

    default_tp1 = (
        live_price
        - atr_value
        * atr_multiplier
        * 1.5
    )

    default_tp2 = (
        live_price
        - atr_value
        * atr_multiplier
        * 2.5
    )

    default_tp3 = (
        live_price
        - atr_value
        * atr_multiplier
        * 4.0
    )


price_step = (
    0.0001
    if live_price < 10
    else 0.1
)


entry_price = st.sidebar.number_input(
    "Entry Price",
    value=float(default_entry),
    step=float(price_step),
    format="%.6f"
)


if use_atr:

    if "LONG" in trade_direction:

        sl_default = (
            entry_price
            - atr_value * atr_multiplier
        )

        tp1_default = (
            entry_price
            + atr_value
            * atr_multiplier
            * 1.5
        )

        tp2_default = (
            entry_price
            + atr_value
            * atr_multiplier
            * 2.5
        )

        tp3_default = (
            entry_price
            + atr_value
            * atr_multiplier
            * 4.0
        )

    else:

        sl_default = (
            entry_price
            + atr_value * atr_multiplier
        )

        tp1_default = (
            entry_price
            - atr_value
            * atr_multiplier
            * 1.5
        )

        tp2_default = (
            entry_price
            - atr_value
            * atr_multiplier
            * 2.5
        )

        tp3_default = (
            entry_price
            - atr_value
            * atr_multiplier
            * 4.0
        )

else:

    if "LONG" in trade_direction:

        sl_default = (
            entry_price * 0.99
        )

        tp1_default = (
            entry_price * 1.015
        )

        tp2_default = (
            entry_price * 1.03
        )

        tp3_default = (
            entry_price * 1.05
        )

    else:

        sl_default = (
            entry_price * 1.01
        )

        tp1_default = (
            entry_price * 0.985
        )

        tp2_default = (
            entry_price * 0.97
        )

        tp3_default = (
            entry_price * 0.95
        )


sl_price = st.sidebar.number_input(
    "🛑 Stop Loss",
    value=float(sl_default),
    step=float(price_step),
    format="%.6f"
)


tp1_price = st.sidebar.number_input(
    "🎯 TP1",
    value=float(tp1_default),
    step=float(price_step),
    format="%.6f"
)


tp2_price = st.sidebar.number_input(
    "🎯 TP2",
    value=float(tp2_default),
    step=float(price_step),
    format="%.6f"
)


tp3_price = st.sidebar.number_input(
    "🎯 TP3",
    value=float(tp3_default),
    step=float(price_step),
    format="%.6f"
)


# ============================================================
# RISK CALCULATION
# ============================================================
risk_usd = (
    account_balance
    * risk_percentage
    / 100
)


risk_distance = abs(
    entry_price
    - sl_price
)


reward_distance = abs(
    tp1_price
    - entry_price
)


if risk_distance > 0:

    position_size = (
        risk_usd
        / risk_distance
    )

    rrr_ratio = (
        reward_distance
       
