import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# ============================================================
# ⚡ ULTIMATE INSTITUTIONAL TRADING TERMINAL V4
# ============================================================

st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal V4",
    page_icon="⚡",
    layout="wide",
)

st_autorefresh(
    interval=5000,
    limit=None,
    key="terminal_refresh",
)

BINANCE_API = "https://api.binance.com/api/v3"
BINANCE_BACKUP = "https://data-api.binance.vision/api/v3"


# ============================================================
# SESSION STATE
# ============================================================

if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "last_alert_key" not in st.session_state:
    st.session_state.last_alert_key = ""

if "last_signal" not in st.session_state:
    st.session_state.last_signal = "WAIT"


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def clean_symbol(symbol):
    return symbol.replace("/", "").strip().upper()


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


def binance_get(endpoint, params=None, timeout=7):

    for base in [BINANCE_API, BINANCE_BACKUP]:

        try:
            r = requests.get(
                f"{base}{endpoint}",
                params=params,
                timeout=timeout,
                headers={
                    "User-Agent":
                    "Ultimate-Institutional-Terminal"
                },
            )

            if r.status_code == 200:
                return r.json()

        except Exception:
            continue

    return None


# ============================================================
# COIN LIST
# ============================================================

@st.cache_data(ttl=3600)
def fetch_available_coins():

    data = binance_get(
        "/exchangeInfo",
        timeout=8
    )

    if isinstance(data, dict):

        symbols = []

        for item in data.get("symbols", []):

            if (
                item.get("quoteAsset") == "USDT"
                and item.get("status") == "TRADING"
            ):
                symbols.append(item["symbol"])

        if symbols:

            return sorted(
                [f"{x[:-4]}/USDT" for x in symbols]
            )

    return [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "DOGE/USDT",
        "SUI/USDT",
        "PEPE/USDT",
        "AVAX/USDT",
        "LINK/USDT",
        "NEAR/USDT",
        "RENDER/USDT",
        "FET/USDT",
        "INJ/USDT",
        "OP/USDT",
        "ARB/USDT",
        "ICP/USDT",
        "DOT/USDT",
        "SHIB/USDT",
        "UNI/USDT",
        "APT/USDT",
    ]


# ============================================================
# WATCHLIST
# ============================================================

@st.cache_data(ttl=5)
def fetch_watchlist(symbols):

    data = binance_get(
        "/ticker/24hr",
        timeout=6
    )

    if not isinstance(data, list):
        return []

    lookup = {
        x.get("symbol"): x
        for x in data
    }

    result = []

    for symbol in symbols:

        raw = clean_symbol(symbol)

        if raw in lookup:

            item = lookup[raw]

            result.append({
                "Symbol": symbol,
                "Price": safe_float(
                    item.get("lastPrice")
                ),
                "Change": safe_float(
                    item.get("priceChangePercent")
                ),
                "Volume": safe_float(
                    item.get("quoteVolume")
                ),
            })

    return result


# ============================================================
# OHLCV
# ============================================================

@st.cache_data(ttl=5)
def fetch_chart_data(
    symbol,
    timeframe="15m",
    limit=250
):

    data = binance_get(
        "/klines",
        params={
            "symbol": clean_symbol(symbol),
            "interval": timeframe,
            "limit": limit,
        },
        timeout=8,
    )

    if not isinstance(data, list):
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
        "ignore",
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

        for col in [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

        return df.reset_index(drop=True)

    except Exception:
        return pd.DataFrame()


# ============================================================
# ORDER BOOK
# ============================================================

@st.cache_data(ttl=2)
def fetch_order_book(symbol):

    data = binance_get(
        "/depth",
        params={
            "symbol": clean_symbol(symbol),
            "limit": 100,
        },
        timeout=5,
    )

    if not isinstance(data, dict):
        return 50.0, 50.0, 0.0

    bids = sum(
        safe_float(x[1])
        for x in data.get("bids", [])
        if len(x) >= 2
    )

    asks = sum(
        safe_float(x[1])
        for x in data.get("asks", [])
        if len(x) >= 2
    )

    total = bids + asks

    if total <= 0:
        return 50.0, 50.0, 0.0

    bid = bids / total * 100
    ask = asks / total * 100

    imbalance = (
        (bids - asks) / total
    ) * 100

    return bid, ask, imbalance


# ============================================================
# WHALE TRADES
# ============================================================

@st.cache_data(ttl=3)
def fetch_whales(
    symbol,
    threshold=5000
):

    data = binance_get(
        "/trades",
        params={
            "symbol": clean_symbol(symbol),
            "limit": 1000,
        },
        timeout=6,
    )

    if not isinstance(data, list):
        return pd.DataFrame()

    rows = []

    for trade in data:

        price = safe_float(
            trade.get("price")
        )

        qty = safe_float(
            trade.get("qty")
        )

        usd = price * qty

        if usd >= threshold:

            side = (
                "SELL 🔴"
                if trade.get("isBuyerMaker")
                else "BUY 🟢"
            )

            rows.append({
                "Time":
                    pd.to_datetime(
                        trade.get("time"),
                        unit="ms"
                    ).strftime("%H:%M:%S"),
                "Side": side,
                "Price": price,
                "Amount": qty,
                "Total ($)": usd,
            })

    return pd.DataFrame(rows)


# ============================================================
# INDICATORS
# ============================================================

def add_indicators(df):

    df = df.copy()

    # EMA
    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    df["EMA200"] = df["close"].ewm(
        span=200,
        adjust=False
    ).mean()

    # RSI
    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    df["RSI"] = (
        100 -
        (100 / (1 + rs))
    ).fillna(50)

    # ATR
    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1
    ).max(axis=1)

    df["ATR"] = tr.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    # Volume
    df["VolumeMA"] = df["volume"].rolling(
        20
    ).mean()

    df["VolumeRatio"] = (
        df["volume"] /
        df["VolumeMA"].replace(
            0,
            np.nan
        )
    ).replace(
        [np.inf, -np.inf],
        np.nan
    ).fillna(1)

    return df


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def find_support_resistance(df):

    supports = []
    resistances = []

    if len(df) < 20:
        return supports, resistances

    highs = df["high"].values
    lows = df["low"].values

    for i in range(
        5,
        len(df) -
