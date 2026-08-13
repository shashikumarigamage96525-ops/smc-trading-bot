import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# ============================================================
# ⚡ ULTIMATE INSTITUTIONAL TRADING TERMINAL V4
# ============================================================
# Binance live data
# Multi-timeframe analysis
# EMA 20 / 50 / 200
# RSI
# ATR
# Support / Resistance
# BOS / CHoCH / MSS
# Liquidity Sweep
# Fair Value Gap
# Order Block
# Volume Confirmation
# Order Book Imbalance
# Whale Trades
# ATR based SL / TP
# LONG / SHORT / WAIT
# Confluence Score
# Backtesting
# Telegram Alerts
# Trade Journal
#
# NOTE:
# This is a rule-based analysis/decision-support tool.
# No system can guarantee 100% accurate trades.
# ============================================================

st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal V4",
    page_icon="⚡",
    layout="wide"
)

# Refresh every 5 seconds
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

if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "last_alert_key" not in st.session_state:
    st.session_state.last_alert_key = ""

if "last_signal" not in st.session_state:
    st.session_state.last_signal = "WAIT"


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def clean_symbol(symbol):
    return str(symbol).replace("/", "")


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
# COIN FETCHER
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
                symbols.append(item["symbol"])

        if symbols:

            return sorted([
                f"{x[:-4]}/USDT"
                for x in symbols
            ])

   
