import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# Page Config
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st_autorefresh(interval=5000, limit=None, key="live_counter")

st.title("⚡ Professional Trading & Pattern Analysis Terminal")

# 1. Robust Data Fetcher
@st.cache_data(ttl=10)
def fetch_live_data(symbol):
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval=1h&limit=200"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'a', 'b', 'c', 'd', 'e', 'f'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
        else: raise Exception
    except:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq='h')
        base = 60000.0 if "BTC" in symbol else (3000.0 if "ETH" in symbol else 0.50)
        df = pd.DataFrame({'timestamp': dates, 'open': base, 'high': base*1.01, 'low': base*0.99, 'close': base, 'volume': 500})
        
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df

# 2. Strict Pattern Engine
def detect_dominant_pattern(df):
    if df.empty or len(df) < 100: return "Consolidation", None
    
    current_price = df['close'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    trend_desc = "Strong Bullish" if current_price > ema_200 else ("Strong Bearish" if current_price < ema_200 else "Consolidation")
    
    dominant_pattern = None
    highs, lows = df['high'].values, df['low'].values
    
    # Double Bottom
    recent_lows = lows[-60:]
    min_l = min(recent_lows)
    troughs = [i for i, l in enumerate(recent_lows) if abs(l - min_l) / min_l < 0.005]
    if len(troughs) >= 2 and (troughs[-1] - troughs[0]) >= 10:
        dominant_pattern = {'name': 'Double Bottom', 'level': min_l, 'bias': 'Bullish'}
        
    # Double Top
    recent_highs = highs[-60:]
    max_h = max(recent_highs)
    peaks = [i for i, h in enumerate(recent_highs) if abs(h - max_h) / max_h < 0.005]
    if len(peaks) >= 2 and (peaks[-1] - peaks[0]) >= 10:
        dominant_pattern = {'name': 'Double Top', 'level': max_h, 'bias': 'Bearish'}
                
    return trend_desc, dominant_pattern

# 3. Sidebar UI
symbol = st.sidebar.selectbox("Select Trading Pair", ["BTC/USDT", "ETH/USDT", "ADA/USDT"], index=0)
df = fetch_live_data(symbol)
current_price = df['close'].iloc[-1]

st.sidebar.subheader("💰 Risk Management")
acc_bal = st.sidebar.number_input("Balance ($):", value=10000.0)
risk_pct = st.sidebar.slider("Risk (%):", 0.5, 5.0, 1.0)
trade_type = st.sidebar.radio("Strategy:", ["LONG", "SHORT"], horizontal=True)

entry = st.sidebar.number_input("Entry:", value=float(current_price), format="%.4f")
sl = st.sidebar.number_input("SL:", value=float(current_price*0.99 if trade_type=="LONG" else current_price*1.01), format="%.4f")
tp = st.sidebar.number_input("TP:", value=float(current_price*1.02 if trade_type=="LONG" else current_price*0.98), format="%.4f")

size = (acc_bal * (risk_pct/100)) / abs(entry - sl) if abs(entry - sl) > 0 else 0

# 4. Main Layout
trend, pattern = detect_dominant_pattern(df)
col1, col2 = st.columns([3, 1])

with col1:
    st.info(f"📊 **Trend:** {trend} | **Pattern:** {pattern['name'] if pattern else 'None'}")
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    
    # Add Markers
    for price, color, text in [(entry, "#2196f3", "ENTRY"), (sl, "#f44336", "SL"), (tp, "#4caf50", "TP")]:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=price, y1=price, line=dict(color=color, width=2, dash="dash"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=price, text=f"{text}: {price}", bgcolor=color, font=dict(color="white"))
    
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Metrics")
    st.metric("Price", f"${current_price:,.2f}")
    st.metric("Size (Units)", f"{size:,.2f}")
    if pattern:
        if pattern['bias'] == 'Bullish': st.success(f"✅ {pattern['name']} detected")
        else: st.error(f"⚠️ {pattern['name']} detected")
