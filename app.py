import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# ============================================================
# ⚡ ULTIMATE INSTITUTIONAL TRADING TERMINAL V3
# Stable / Analysis Only / Binance Public API
# ============================================================

st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal V3",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Optional auto refresh
try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(
        interval=5000,
        limit=None,
        key="terminal_refresh",
    )
except Exception:
    pass


# ============================================================
# SESSION STATE
# ============================================================

if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "signal_history" not in st.session_state:
    st.session_state.signal_history = []

if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = "BTC/USDT"


# ============================================================
# CONSTANTS
# ============================================================

FALLBACK_SYMBOLS = [
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
    "1000RATS/USDT",
]

TIMEFRAMES = [
    "5m",
    "15m",
    "1h",
    "4h",
]

STRATEGIES = {
    "OB + FVG":
        "Order Block and Fair Value Gap confluence",

    "Liquidity Sweep + MSS":
        "Liquidity sweep and market structure shift",

    "MTF Trend Confluence":
        "15m execution aligned with 4h direction",

    "Order Book Imbalance":
        "Bid/ask pressure confirmation",
}


# ============================================================
# SAFE HTTP REQUEST
# ============================================================

def safe_get_json(url, timeout=5):

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent":
                    "InstitutionalTradingTerminal/3.0"
            },
        )

        if response.status_code == 200:
            return response.json()

    except Exception:
        return None

    return
