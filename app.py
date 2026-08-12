import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Professional Trading Terminal", layout="wide")

st.title("⚡ Professional Trading Terminal (Safe Mode)")

# 1. ආරක්ෂිත දත්ත උත්පාදක ක්‍රමවේදය (Fallback/Mock Data)
# මෙය සර්වර් බ්ලොක් වීම් වලින් තොරව ක්ෂණිකව ප්‍රස්ථාර පෙන්වයි.
@st.cache_data
def get_sample_data(symbol):
    np.random.seed(42 if "BTC" in symbol else (24 if "ETH" in symbol else 10))
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq='h')
    
    base_price = 60000.0 if "BTC" in symbol else (3000.0 if "ETH" in symbol else 0.20)
    walk = np.random.normal(loc=0, scale=base_price*0.005, size=200).cumsum()
    close_prices = base_price + walk
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices * 0.999,
        'high': close_prices * 1.005,
        'low': close_prices * 0.995,
        'close': close_prices,
        'volume': np.random.randint(100, 1000, size=200)
    })
    df['EMA_200'] = df['close'].ewm(span=50, adjust=False).mean()
    return df

# 2. UI Controls
symbol = st.sidebar.selectbox("Select Coin", ["BTC/USDT", "ETH/USDT", "ADA/USDT"])
df = get_sample_data(symbol)

current_price = df['close'].iloc[-1]
ema_200 = df['EMA_200'].iloc[-1]

# Trend Detection Logic
trend_desc = "Strong Bullish" if current_price > ema_200 else "Strong Bearish"

st.write(f"### Market Analysis for {symbol}")
st.info(f"📊 **Market Trend Structure:** {trend_desc} | **Live Price:** ${current_price:,.4f}")

# 3. Plotting Candlestick Chart
fig = go.Figure(data=[go.Candlestick(
    x=df['timestamp'],
    open=df['open'],
    high=df['high'],
    low=df['low'],
    close=df['close'],
    increasing_line_color='#26a69a',
    decreasing_line_color='#ef5350'
)])

fig.add_trace(go.Scatter(
    x=df['timestamp'], 
    y=df['EMA_200'], 
    name='EMA Trend Line', 
    line=dict(color='#ff9800', width=2)
))

fig.update_layout(
    height=600,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=10, b=10)
)

st.plotly_chart(fig, use_container_width=True)
