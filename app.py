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

# Auto refresh
st_autorefresh(
    interval=5000,
    limit=None,
    key="terminal_refresh"
)

BINANCE_API = "https://api.binance.com/api/v3"
BINANCE_BACKUP = "https://data-api.binance.vision/api/v3"


# ============================================================
# SESSION STATE
# ============================================================

if "journal" not in st.session_state:
    st.session_state.journal = []

if "last_alert_key" not in st.session_state:
    st.session_state.last_alert_key = ""


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def clean_symbol(symbol):
    return symbol.replace("/", "")


def format_price(price):
    price = safe_float(price)

    if price >= 1000:
        return f"{price:,.2f}"

    if price >= 1:
        return f"{price:,.4f}"

    if price >= 0.01:
        return f"{price:,.5f}"

    return f"{price:,.8f}"


def binance_get(endpoint, params=None, timeout=6):

    for base_url in [BINANCE_API, BINANCE_BACKUP]:

        try:

            response = requests.get(
                f"{base_url}{endpoint}",
                params=params,
                timeout=timeout
            )

            if response.status_code == 200:
                return response.json()

        except Exception:
            continue

    return None


# ============================================================
# AVAILABLE COINS
# ============================================================

@st.cache_data(ttl=3600)
def fetch_available_coins():

    data = binance_get(
        "/exchangeInfo",
        timeout=5
    )

    if isinstance(data, dict):

        symbols = []

        for item in data.get("symbols", []):

            if (
                item.get("quoteAsset") == "USDT"
                and item.get("status") == "TRADING"
            ):

                symbols.append(
                    item["symbol"]
                )

        if symbols:

            return sorted([
                f"{x[:-4]}/USDT"
                for x in symbols
            ])

    return sorted([
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "DOGE/USDT",
        "SUI/USDT",
        "PEPE/USDT",
        "ACE/USDT",
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
        "APT/USDT"
    ])


# ============================================================
# WATCHLIST TICKERS
# ============================================================

@st.cache_data(ttl=5)
def fetch_watchlist_tickers(symbols):

    data = binance_get(
        "/ticker/24hr",
        timeout=5
    )

    if not isinstance(data, list):
        return []

    lookup = {
        x["symbol"]: x
        for x in data
    }

    output = []

    for symbol in symbols:

        raw = clean_symbol(symbol)

        if raw in lookup:

            item = lookup[raw]

            output.append({

                "Symbol": symbol,

                "Price":
                    safe_float(
                        item.get("lastPrice")
                    ),

                "Change":
                    safe_float(
                        item.get("priceChangePercent")
                    ),

                "Volume":
                    safe_float(
                        item.get("quoteVolume")
                    )
            })

    return output


# ============================================================
# OHLCV DATA
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
            "limit": limit
        },
        timeout=7
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

        for column in [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df = df.dropna()

        return df.reset_index(drop=True)

    except Exception:

        return pd.DataFrame()


# ============================================================
# ORDER BOOK
# ============================================================

@st.cache_data(ttl=2)
def fetch_order_book_metrics(symbol):

    data = binance_get(
        "/depth",
        params={
            "symbol": clean_symbol(symbol),
            "limit": 100
        },
        timeout=5
    )

    if not isinstance(data, dict):

        return 50.0, 50.0, 0.0

    bids = sum(
        safe_float(x[1])
        for x in data.get("bids", [])
    )

    asks = sum(
        safe_float(x[1])
        for x in data.get("asks", [])
    )

    total = bids + asks

    if total <= 0:

        return 50.0, 50.0, 0.0

    bid_pressure = (
        bids / total * 100
    )

    ask_pressure = (
        asks / total * 100
    )

    imbalance = (
        (bids - asks)
        / total
        * 100
    )

    return (
        bid_pressure,
        ask_pressure,
        imbalance
    )


# ============================================================
# WHALE TRADES
# ============================================================

@st.cache_data(ttl=3)
def fetch_whale_transactions(
    symbol,
    threshold_usd=5000
):

    data = binance_get(
        "/trades",
        params={
            "symbol": clean_symbol(symbol),
            "limit": 1000
        },
        timeout=7
    )

    if not isinstance(data, list):

        return pd.DataFrame()

    trades = []

    for trade in data:

        price = safe_float(
            trade.get("price")
        )

        quantity = safe_float(
            trade.get("qty")
        )

        total_usd = (
            price * quantity
        )

        if total_usd >= threshold_usd:

            side = (
                "SELL 🔴"
                if trade.get("isBuyerMaker")
                else "BUY 🟢"
            )

            trades.append({

                "Time":
                    pd.to_datetime(
                        trade.get("time"),
                        unit="ms"
                    ).strftime("%H:%M:%S"),

                "Side":
                    side,

                "Price":
                    price,

                "Amount":
                    quantity,

                "Total ($)":
                    total_usd
            })

    return pd.DataFrame(trades)


# ============================================================
# INDICATORS
# ============================================================

def add_indicators(df):

    df = df.copy()

    # EMA 20
    df["EMA_20"] = (
        df["close"]
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    # EMA 50
    df["EMA_50"] = (
        df["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    # EMA 200
    df["EMA_200"] = (
        df["close"]
        .ewm(
            span=200,
            adjust=False
        )
        .mean()
    )

    # ---------------- RSI ----------------

    delta = df["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = (
        avg_gain
        / avg_loss.replace(
            0,
            np.nan
        )
    )

    df["RSI"] = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    df["RSI"] = df["RSI"].fillna(50)

    # ---------------- ATR ----------------

    previous_close = (
        df["close"].shift(1)
    )

    true_range = pd.concat(
        [
            df["high"] - df["low"],

            (
                df["high"]
                - previous_close
            ).abs(),

            (
                df["low"]
                - previous_close
            ).abs()
        ],
        axis=1
    ).max(axis=1)

    df["ATR"] = (
        true_range
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    # ---------------- VOLUME ----------------

    df["Volume_SMA20"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    df["Volume_Ratio"] = (
        df["volume"]
        / df["Volume_SMA20"].replace(
            0,
            np.nan
        )
    )

    df["Volume_Ratio"] = (
        df["Volume_Ratio"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(1)
    )

    return df


# ============================================================
# CANDLE PATTERN
# ============================================================

def detect_candle_pattern(df):

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
                current["close"],
                current["open"]
            )
        )

        lower_shadow = (
            min(
                current["close"],
                current["open"]
            )
            - current["low"]
        )

        if (
            lower_shadow
            > max(body, candle_range * 0.05) * 2
            and
            upper_shadow
            < max(body, candle_range * 0.05)
        ):

            return "Hammer 🟢"

        if (
            upper_shadow
            > max(body, candle_range * 0.05) * 2
            and
            lower_shadow
            < max(body, candle_range * 0.05)
        ):

            return "Shooting Star 🔴"

    return "Neutral"


# ============================================================
# MARKET STRUCTURE
# ============================================================

def detect_market_structure(
    df,
   
