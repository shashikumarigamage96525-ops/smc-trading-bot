import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal V4",
    page_icon="⚡",
    layout="wide"
)

st_autorefresh(
    interval=5000,
    limit=None,
    key="terminal_refresh"
)

API = "https://api.binance.com/api/v3"
BACKUP = "https://data-api.binance.vision/api/v3"


# ============================================================
# HELPERS
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
        return f"{price:,.6f}"

    return f"{price:,.8f}"


# ============================================================
# BINANCE API
# ============================================================

@st.cache_data(ttl=10)
def api_get(endpoint, params=None):

    for base_url in [API, BACKUP]:

        try:
            response = requests.get(
                base_url + endpoint,
                params=params,
                timeout=6
            )

            if response.status_code == 200:
                return response.json()

        except Exception:
            pass

    return None


# ============================================================
# COINS
# ============================================================

@st.cache_data(ttl=3600)
def fetch_coins():

    data = api_get("/exchangeInfo")

    if isinstance(data, dict):

        result = []

        for item in data.get("symbols", []):

            if (
                item.get("quoteAsset") == "USDT"
                and item.get("status") == "TRADING"
            ):

                result.append(
                    item["symbol"][:-4] + "/USDT"
                )

        if result:
            return sorted(result)

    return sorted([
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "SUI/USDT",
        "DOGE/USDT",
        "PEPE/USDT",
        "ACE/USDT",
        "AVAX/USDT",
        "LINK/USDT",
        "NEAR/USDT",
        "INJ/USDT",
        "UNI/USDT",
        "APT/USDT"
    ])


# ============================================================
# OHLCV
# ============================================================

@st.cache_data(ttl=5)
def fetch_klines(
    symbol,
    interval="15m",
    limit=250
):

    data = api_get(
        "/klines",
        params={
            "symbol": clean_symbol(symbol),
            "interval": interval,
            "limit": limit
        }
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
        "taker_base",
        "taker_quote",
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
# INDICATORS
# ============================================================

def calculate_indicators(df):

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

    # RSI
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

    # ATR
    previous_close = df["close"].shift(1)

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

    # Volume
    df["Volume_SMA"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    df["Volume_Ratio"] = (
        df["volume"]
        /
        df["Volume_SMA"].replace(
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
# SUPPORT / RESISTANCE
# ============================================================

def find_structure(df):

    supports = []
    resistances = []

    highs = df["high"].values
    lows = df["low"].values

    window = 5

    for i in range(
        window,
        len(df) - window
    ):

        local_high = max(
            highs[
                i - window:
                i + window + 1
            ]
        )

        local_low = min(
            lows[
                i - window:
                i + window + 1
            ]
        )

        if highs[i] >= local_high:
            resistances.append(
                float(highs[i])
            )

        if lows[i] <= local_low:
            supports.append(
                float(lows[i])
            )

    supports = sorted(
        list(set(supports))
    )

    resistances = sorted(
        list(set(resistances))
    )

    return (
        supports[-3:],
        resistances[-3:]
    )


# ============================================================
# FAIR VALUE GAP
# ============================================================

def detect_fvg(df):

    bullish = []
    bearish = []

    for i in range(
        1,
        len(df) - 1
    ):

        previous_high = df[
            "high"
        ].iloc[i - 1]

        previous_low = df[
            "low"
        ].iloc[i - 1]

        next_high = df[
            "high"
        ].iloc[i + 1]

        next_low = df[
            "low"
        ].iloc[i + 1]

        if next_low > previous_high:

            bullish.append({
                "low": float(
                    previous_high
                ),
                "high": float(
                    next_low
                ),
                "type": "Bullish FVG"
            })

        if next_high < previous_low:

            bearish.append({
                "low": float(
                    next_high
                ),
                "high": float(
                    previous_low
                ),
                "type": "Bearish FVG"
            })

    return (
        bullish[-3:],
        bearish[-3:]
    )


# ============================================================
# CANDLE PATTERN
# ============================================================

def candle_pattern(df):

    if len(df) < 2:
        return "Neutral"

    previous = df.iloc[-2]
    current = df.iloc[-1]

    if (
        current["close"]
        > current["open"]
        and
        previous["close"]
        < previous["open"]
        and
        current["close"]
        >= previous["open"]
        and
        current["open"]
        <= previous["close"]
    ):

        return "Bullish Engulfing 🟢"

    if (
        current["close"]
        < current["open"]
        and
        previous["close"]
        > previous["open"]
        and
        current["close"]
        <= previous["open"]
        and
        current["open"]
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
            and
            upper_shadow < body
        ):

            return "Bullish Pin Bar 🟢"

        if (
            upper_shadow > body * 2
            and
            lower_shadow < body
        ):

            return "Bearish Pin Bar 🔴"

    return "Neutral"


# ============================================================
# ORDER BOOK
# ============================================================

@st.cache_data(ttl=2)
def order_book(symbol):

    data = api_get(
        "/depth",
        params={
            "symbol": clean_symbol(symbol),
            "limit": 100
        }
    )

    if not isinstance(
        data,
        dict
    ):

        return (
            50.0,
            50.0,
            0.0
        )

    bids = sum(
        safe_float(x[1])
        for x in data.get(
            "bids",
            []
        )
    )

    asks = sum(
        safe_float(x[1])
        for x in data.get(
            "asks",
            []
        )
    )

    total = bids + asks

    if total <= 0:

        return (
            50.0,
            50.0,
            0.0
        )

    bid_pressure = (
        bids
        / total
        * 100
    )

    ask_pressure = (
        asks
        / total
        * 100
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
# WATCHLIST
# ============================================================

@st.cache_data(ttl=5)
def fetch_tickers(symbols):

    data = api_get(
        "/ticker/24hr"
    )

    if not isinstance(
        data,
        list
    ):

        return []

    lookup = {
        item["symbol"]: item
        for item in data
    }

    result = []

    for symbol in symbols:

        raw = clean_symbol(
            symbol
        )

        if raw in lookup:

            item = lookup[raw]

            result.append({
                "Symbol": symbol,
                "Price": safe_float(
                    item["lastPrice"]
                ),
                "Change": safe_float(
                    item["priceChangePercent"]
                )
            })

    return result


# ============================================================
# WHALE TRADES
# ============================================================

@st.cache_data(ttl=3)
def whale_trades(
    symbol,
    threshold=5000
):

    data = api_get(
        "/trades",
        params={
            "symbol": clean_symbol(symbol),
            "limit": 1000
        }
    )

    rows = []

    if isinstance(
        data,
        list
    ):

        for trade in data:

            price = safe_float(
                trade.get("price")
            )

            quantity = safe_float(
                trade.get("qty")
            )

            total = (
                price
                * quantity
            )

            if total >= threshold:

                side = (
                    "SELL 🔴"
                    if trade.get(
                        "isBuyerMaker"
                    )
                    else
                    "BUY 🟢"
                )

                rows.append({
                    "Time":
                        pd.to_datetime(
                            trade.get(
                                "time"
                            ),
                            unit="ms"
                        ).strftime(
                            "%H:%M:%S"
                        ),

                    "Side": side,

                    "Price": price,

                    "Amount": quantity,

                    "Total ($)": total
                })

    return pd.DataFrame(rows)


# ============================================================
# SIGNAL ENGINE
# ============================================================

def calculate_signal(
    df,
    df4,
    direction,
    bid_pressure,
    ask_pressure,
    entry,
    sl,
    tp1
):

    current = df.iloc[-1]

    price = float(
        current["close"]
    )

    ema20 = float(
        current["EMA_20"]
    )

    ema50 = float(
        current["EMA_50"]
    )

    rsi = float(
        current["RSI"]
    )

    volume_ratio = float(
        current["Volume_Ratio"]
    )

    macro_bullish = (
        df4.iloc[-1]["close"]
        >
        df4.iloc[-1]["EMA_50"]
    )

    bullish_structure = (
        price
        > ema20
        > ema50
    )

    bearish_structure = (
        price
        < ema20
        < ema50
    )

    volume_ok = (
        volume_ratio >= 1.15
    )

    if direction == "LONG":

        checks = [
            bullish_structure,
            macro_bullish,
            45 <= rsi <= 68,
            bid_pressure >= 52,
            volume_ok
        ]

    else:

        checks = [
            bearish_structure,
            not macro_bullish,
            32 <= rsi <= 55,
            ask_pressure >= 52,
            volume_ok
        ]

    risk_distance = abs(
        entry - sl
    )

    reward_distance = abs(
        tp1 - entry
    )

    if risk_distance > 0:

        rr = (
            reward_distance
            / risk_distance
        )

    else:

        rr = 0.0

    checks.append(
        rr >= 1.5
    )

    score = int(
        sum(checks)
        / len(checks)
        * 100
    )

    if score >= 80:

        signal = direction

    elif score >= 60:

        signal = "WATCH"

    else:

        signal = "WAIT"

    return (
        signal,
        score,
        rr,
        checks
    )


# ============================================================
# SIDEBAR
# ============================================================

st.title(
    "⚡ Ultimate Institutional Trading Terminal V4"
)

st.caption(
    "Binance Live Data • MTF • EMA • RSI • ATR • "
    "S/R • FVG • Order Book • Whale Trades • Risk Engine"
)

all_symbols = fetch_coins()

default_index = (
    all_symbols.index("BTC/USDT")
    if "BTC/USDT" in all_symbols
    else 0
)

with st.sidebar:

    st.header(
        "🎛 Control Center"
    )

    selected_coin = st.selectbox(
        "🔍 Select Asset",
        all_symbols,
        index=default_index
    )

    timeframe = st.selectbox(
        "Execution Timeframe",
        [
            "5m",
            "15m",
            "1h",
            "4h"
        ],
        index=1
    )

    direction = st.radio(
        "Trade Direction",
        [
            "LONG",
            "SHORT"
        ],
        horizontal=True
    )

    st.divider()

    account_balance = st.number_input(
        "Account Balance ($)",
        min_value=10.0,
        value=10000.0,
        step=100.0
    )

    risk_percentage = st.slider(
        "Risk Per Trade (%)",
        0.5,
        5.0,
        1.0,
        0.5
    )


# ============================================================
# MAIN DATA
# ============================================================

df = fetch_klines(
    selected_coin,
    timeframe,
    250
)

df4 = fetch_klines(
    selected_coin,
    "4h",
    250
)

if df.empty:

    st.error(
        "❌ Binance data load failed. "
        "Please refresh the page."
    )

    st.stop()

df = calculate_indicators(
    df
)

if df4.empty:

    df4 = df.copy()

else:

    df4 = calculate_indicators(
        df4
    )


# ============================================================
# CURRENT VALUES
# ============================================================

current_price = float(
    df.iloc[-1]["close"]
)

atr = float(
    df.iloc[-1]["ATR"]
)

if atr <= 0:

    atr = current_price * 0.001


# ============================================================
# DEFAULT TRADE LEVELS
# ============================================================

if direction == "LONG":

    entry_price = current_price

    sl_price = (
        current_price
        - atr * 1.5
    )

    tp1_price = (
        current_price
        + atr * 1.5
    )

    tp2_price = (
        current_price
        + atr * 3.0
    )

    tp3_price = (
        current_price
        + atr * 4.5
    )

else:

    entry_price = current_price

    sl_price = (
        current_price
        + atr * 1.5
    )

    tp1_price = (
        current_price
        - atr * 1.5
    )

    tp2_price = (
        current_price
        - atr * 3.0
    )

    tp3_price = (
        current_price
        - atr * 4.5
    )


# ============================================================
# MANUAL LEVELS
# ============================================================

with st.sidebar:

    st.divider()

    entry_price = st.number_input(
        "Entry Price",
        value=float(entry_price),
        format="%.8f"
    )

    sl_price = st.number_input(
        "Stop Loss",
        value=float(sl_price),
        format="%.8f"
    )

    tp1_price = st.number_input(
        "Take Profit 1",
        value=float(tp1_price),
        format="%.8f"
    )

    tp2_price = st.number_input(
        "Take Profit 2",
        value=float(tp2_price),
        format="%.8f"
    )

    tp3_price = st.number_input(
        "Take Profit 3",
        value=float(tp3_price),
        format="%.8f"
    )


# ============================================================
# ORDER BOOK
# ============================================================

bid_pressure, ask_pressure, imbalance = (
    order_book(
        selected_coin
    )
)


# ============================================================
# SIGNAL
# ============================================================

signal, confidence, rr_ratio, checklist = (
    calculate_signal(
        df,
        df4,
        direction,
        bid_pressure,
        ask_pressure,
        entry_price,
        sl_price,
        tp1_price
    )
)


# ============================================================
# POSITION SIZE
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

if risk_distance > 0:

    position_size = (
        risk_usd
        / risk_distance
    )

else:

    position_size = 0


# ============================================================
# WATCHLIST
# ============================================================

st.markdown(
    "### ⚡ Multi-Coin Watchlist"
)

watchlist = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    selected_coin
]

watchlist = list(
    dict.fromkeys(
        watchlist
    )
)

ticker_data = fetch_tickers(
    watchlist
)

watch_cols = st.columns(
    min(
        3,
        max(
            1,
            len(ticker_data)
        )
    )
)

for i, item in enumerate(
    ticker_data
):

    with watch_cols[
        i % len(watch_cols)
    ]:

        st.metric(
            item["Symbol"],
            "$" + format_price(
                item["Price"]
            ),
            f'{item["Change"]:+.2f}%'
        )


# ============================================================
# TOP METRICS
# ============================================================

st.divider()

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric(
    "Live Price",
    "$" + format_price(
        current_price
    )
)

m2.metric(
    "RSI",
    f'{df.iloc[-1]["RSI"]:.1f}'
)

m3.metric(
    "ATR",
    format_price(atr)
)

m4.metric(
    "Order Book",
    f"{bid_pressure:.1f}% / "
    f"{ask_pressure:.1f}%"
)

m5.metric(
    "Signal",
    f"{signal} {confidence}%"
)


# ============================================================
# MULTI TIMEFRAME
# ============================================================

st.markdown(
    "### 🌐 Multi-Timeframe Trend Confluence"
)

tf1 = fetch_klines(
    selected_coin,
    "15m",
    100
)

tf2 = fetch_klines(
    selected_coin,
    "1h",
    100
)

tf3 = fetch_klines(
    selected_coin,
    "4h",
    100
)


def get_trend(data):

    if data.empty:

        return "N/A"

    data = calculate_indicators(
        data
    )

    if (
        data.iloc[-1]["close"]
        >
        data.iloc[-1]["EMA_50"]
    ):

        return "BULLISH 🟢"

    return "BEARISH 🔴"


trend_15m = get_trend(tf1)
trend_1h = get_trend(tf2)
trend_4h = get_trend(tf3)

t1, t2, t3 = st.columns(3)

t1.metric(
    "15m Execution",
    trend_15m
)

t2.metric(
    "1h Structure",
    trend_1h
)

t3.metric(
    "4h Macro",
    trend_4h
)


# ============================================================
# SIGNAL STATUS
# ============================================================

st.markdown(
    "### 🎯 Institutional Signal Engine"
)

s1, s2, s3, s4 = st.columns(4)

s1.metric(
    "Signal",
    signal
)

s2.metric(
    "Confidence",
    f"{confidence}%"
)

s3.metric(
    "Risk : Reward",
    f"1:{rr_ratio:.2f}"
)

s4.metric(
    "Position Size",
    f"{position_size:.2f}"
)


if signal == "LONG":

    st.success(
        "🟢 HIGH-CONFLUENCE LONG SETUP"
    )

elif signal == "SHORT":

    st.error(
        "🔴 HIGH-CONFLUENCE SHORT SETUP"
    )

elif signal == "WATCH":

    st.warning(
        "🟡 WATCH — setup developing"
    )

else:

    st.info(
        "⚪ WAIT — insufficient confluence"
    )


# ============================================================
# GATEKEEPER
# ============================================================

st.markdown(
    "### 🔒 Gatekeeper Checklist"
)

check_names = [
    "EMA Structure",
    "4H Trend",
    "RSI Momentum",
    "Order Book
