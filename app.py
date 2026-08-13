import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# ============================================================
# ⚡ ULTIMATE INSTITUTIONAL TRADING TERMINAL V3
# ============================================================

st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide",
)

st_autorefresh(
    interval=5000,
    limit=None,
    key="terminal_refresh"
)

BINANCE_API = "https://api.binance.com/api/v3"
BINANCE_BACKUP = "https://data-api.binance.vision/api/v3"


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
    p = safe_float(price)

    if p >= 1000:
        return f"{p:,.2f}"
    elif p >= 1:
        return f"{p:,.4f}"
    elif p >= 0.01:
        return f"{p:,.5f}"
    else:
        return f"{p:,.8f}"


@st.cache_data(ttl=10)
def binance_get(endpoint, params=None):

    for base_url in [BINANCE_API, BINANCE_BACKUP]:

        try:

            response = requests.get(
                base_url + endpoint,
                params=params,
                timeout=6
            )

            if response.status_code == 200:
                return response.json()

        except Exception:
            continue

    return None


# ============================================================
# COIN LIST
# ============================================================

@st.cache_data(ttl=3600)
def fetch_available_coins():

    data = binance_get("/exchangeInfo")

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
                [
                    symbol[:-4] + "/USDT"
                    for symbol in symbols
                ]
            )

    return sorted([
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "SUI/USDT",
        "DOGE/USDT",
        "ADA/USDT",
        "AVAX/USDT",
        "LINK/USDT",
        "NEAR/USDT",
        "PEPE/USDT",
        "APT/USDT",
        "UNI/USDT",
        "DOT/USDT"
    ])


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
   
