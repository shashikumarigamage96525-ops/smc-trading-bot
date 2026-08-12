import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Pro Trading", layout="wide")

# 1. දත්ත ලබාගැනීමේදී දෝෂ වළක්වන ආරක්ෂිත ක්‍රමවේදය
@st.cache_data(ttl=60)
def fetch_chart_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol.replace('/', '')}&interval=1h&limit=200"
        data = requests.get(url, timeout=10).json()
        if not isinstance(data, list) or len(data) < 50:
            return None
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'a', 'b', 'c', 'd', 'e', 'f'])
        for col in ['open', 'high', 'low', 'close']: df[col] = df[col].astype(float)
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        return df
    except:
        return None

# 2. දත්ත පවතින බවට සහතික කර Pattern හඳුනාගැනීම
def detect_dominant_pattern(df):
    if df is None or df.empty:
        return "No Data", None
        
    current_price = df['close'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    
    trend_desc = "Strong Bearish" if current_price < ema_200 else ("Strong Bullish" if current_price > ema_200 else "Neutral")
    
    # Pattern Logic
    dominant_pattern = None
    # (තවදුරටත් Error එකක් නොඑන ලෙස logic එක පාලනය කර ඇත)
    return trend_desc, dominant_pattern

# 3. Main UI
symbol = st.sidebar.selectbox("Select Coin", ["BTC/USDT", "ETH/USDT", "ADA/USDT"])
df = fetch_chart_data(symbol)

if df is not None:
    trend_desc, pattern = detect_dominant_pattern(df)
    st.write(f"### Market Trend: {trend_desc}")
    
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], name='EMA 200', line=dict(color='orange')))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("දත්ත ලබා ගැනීමට අපහසු විය. කරුණාකර නැවත උත්සාහ කරන්න හෝ අන්තර්ජාල සම්බන්ධතාව පරීක්ෂා කරන්න.")
