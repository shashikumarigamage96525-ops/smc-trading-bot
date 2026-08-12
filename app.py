import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Config
st.set_page_config(page_title="Professional Trading Terminal", layout="wide")
st_autorefresh(interval=5000, limit=None)

# 2. Data Fetch
@st.cache_data(ttl=60)
def fetch_chart_data(symbol, timeframe='1h'):
    clean_symbol = symbol.replace("/", "")
    url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit=200"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'not', 'tb', 'tq', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close']: df[col] = df[col].astype(float)
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df

# 3. Corrected Pattern Engine
def detect_dominant_pattern(df):
    current_price = df['close'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    
    # Trend Detection
    trend_desc = "Strong Bearish" if current_price < ema_200 else ("Strong Bullish" if current_price > ema_200 else "Neutral")
    
    highs = df['high'].values
    lows = df['low'].values
    
    dominant_pattern = None
    
    # Logic: Double Bottom (Valid only if trend is NOT Bearish)
    if current_price >= ema_200 * 0.95: 
        recent_lows = lows[-50:]
        min_l = min(recent_lows)
        troughs = [i for i, l in enumerate(recent_lows) if l < min_l * 1.01]
        if len(troughs) >= 2 and (troughs[-1] - troughs[0]) > 15:
            dominant_pattern = {'name': 'Double Bottom', 'bias': 'Bullish', 'level': min_l}
            
    # Logic: Double Top (Valid only if trend is NOT Bullish)
    if current_price <= ema_200 * 1.05:
        recent_highs = highs[-50:]
        max_h = max(recent_highs)
        peaks = [i for i, h in enumerate(recent_highs) if h > max_h * 0.99]
        if len(peaks) >= 2 and (peaks[-1] - peaks[0]) > 15:
            dominant_pattern = {'name': 'Double Top', 'bias': 'Bearish', 'level': max_h}
            
    return trend_desc, dominant_pattern

# 4. Main UI
symbol = st.sidebar.selectbox("Select Coin", ["BTC/USDT", "ETH/USDT", "ADA/USDT", "SOL/USDT", "BCH/USDT"])
df = fetch_chart_data(symbol)
trend_desc, pattern = detect_dominant_pattern(df)

st.title(f"Analysis for {symbol}")
st.write(f"### Market Trend: {trend_desc}")

if pattern:
    if pattern['bias'] == 'Bullish' and trend_desc != "Strong Bearish":
        st.success(f"✅ Validated {pattern['name']} at ${pattern['level']:.4f}")
    elif pattern['bias'] == 'Bearish' and trend_desc != "Strong Bullish":
        st.error(f"⚠️ Validated {pattern['name']} at ${pattern['level']:.4f}")
    else:
        st.info("Market structure is uncertain for this pattern.")
else:
    st.info("No high-probability structural patterns detected.")

# Plot
fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], name='EMA 200', line=dict(color='orange')))
st.plotly_chart(fig, use_container_width=True)
