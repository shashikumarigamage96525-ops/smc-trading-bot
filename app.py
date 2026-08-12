import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. UI Setup
st.set_page_config(page_title="Institutional Trading Terminal", layout="wide")
st_autorefresh(interval=5000, limit=None, key="live")

# Styling - Clean Dark Mode
st.markdown("""
    <style>
    .main {background-color: #0e1117;}
    .stMetric {background-color: #1e1e1e; padding: 15px; border-radius: 10px;}
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Pro Trading & Pattern Analysis")

# 2. Data Fetching
@st.cache_data(ttl=60)
def fetch_data(symbol, interval='1h'):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol.replace('/', '')}&interval={interval}&limit=200"
    try:
        data = requests.get(url).json()
        df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ct', 'q', 'nt', 'tb', 'tq', 'i'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df[['o', 'h', 'l', 'c']] = df[['o', 'h', 'l', 'c']].astype(float)
        # Indicators
        df['EMA_50'] = df['c'].ewm(span=50).mean()
        df['EMA_200'] = df['c'].ewm(span=200).mean()
        return df
    except: return pd.DataFrame()

# 3. Pattern Recognition
def get_patterns(df):
    patterns = []
    # Simplified Logic for clarity
    if df['c'].iloc[-1] > df['EMA_200'].iloc[-1]: bias = 'Bullish'
    else: bias = 'Bearish'
    
    # Example detection
    if abs(df['c'].iloc[-1] - df['c'].iloc[-2]) < (df['c'].iloc[-1] * 0.001):
        patterns.append({'name': 'Consolidation Zone', 'bias': 'Neutral'})
    
    return bias, patterns

# 4. Sidebar Inputs
symbol = st.sidebar.selectbox("Asset", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
df = fetch_data(symbol)
bias, patterns = get_patterns(df)

# 5. Main Chart Area
if not df.empty:
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name='Market'))
    
    # EMAs
    fig.add_trace(go.Scatter(x=df['ts'], y=df['EMA_50'], name='EMA 50', line=dict(color='#2962ff', width=1)))
    fig.add_trace(go.Scatter(x=df['ts'], y=df['EMA_200'], name='EMA 200', line=dict(color='#ff6d00', width=1)))
    
    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# 6. Clean Metric Grid
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"${df['c'].iloc[-1]:,.2f}")
c2.metric("Trend Bias", bias)
c3.metric("Patterns Found", len(patterns))

# 7. Pattern Report
if patterns:
    st.subheader("📋 Analysis Report")
    for p in patterns:
        st.info(f"Detected: {p['name']} | Bias: {p['bias']}")
else:
    st.success("Market state is clear. No active reversal patterns.")
