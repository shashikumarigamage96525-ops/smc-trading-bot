import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Professional Trading Terminal", layout="wide")

st.title("⚡ Professional Trading & Pattern Analysis Terminal")

# 1. Safe & Stable Data Generator (Fallback / Mock Mode)
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
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df

# 2. Pattern & Trend Engine
def detect_dominant_pattern(df):
    current_price = df['close'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    
    trend_desc = "Strong Bearish" if current_price < ema_200 else ("Strong Bullish" if current_price > ema_200 else "Neutral")
    
    highs = df['high'].values
    lows = df['low'].values
    dominant_pattern = None
    
    if current_price >= ema_200 * 0.95: 
        recent_lows = lows[-50:]
        min_l = min(recent_lows)
        troughs = [i for i, l in enumerate(recent_lows) if l < min_l * 1.01]
        if len(troughs) >= 2:
            dominant_pattern = {'name': 'Double Bottom Reversal', 'bias': 'Bullish', 'level': min_l}
            
    if current_price <= ema_200 * 1.05:
        recent_highs = highs[-50:]
        max_h = max(recent_highs)
        peaks = [i for i, h in enumerate(recent_highs) if h > max_h * 0.99]
        if len(peaks) >= 2:
            dominant_pattern = {'name': 'Double Top Reversal', 'bias': 'Bearish', 'level': max_h}
            
    return trend_desc, dominant_pattern

# 3. Sidebar Controls & Risk Management Hub
symbol = st.sidebar.selectbox("Select Coin", ["BTC/USDT", "ETH/USDT", "ADA/USDT"])
df = get_sample_data(symbol)

current_price = df['close'].iloc[-1]

st.sidebar.divider()
st.sidebar.subheader("💰 Account & Position Sizing")
account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

st.sidebar.divider()
st.sidebar.subheader("📈 Trade Setup Configuration")
trade_type = st.sidebar.radio("Direction Strategy:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

p_step = 0.0001 if current_price < 10 else 0.1
entry_price = st.sidebar.number_input("Entry Price:", value=float(current_price), format="%.4f", step=p_step)
sl_price = st.sidebar.number_input("Stop Loss (SL) Price:", value=float(current_price * 0.99), format="%.4f", step=p_step)
tp_price = st.sidebar.number_input("Take Profit (TP) Price:", value=float(current_price * 1.02), format="%.4f", step=p_step)

risk_amount_usd = account_balance * (risk_percentage / 100.0)
price_risk_per_unit = abs(entry_price - sl_price)
position_size_units = risk_amount_usd / price_risk_per_unit if price_risk_per_unit > 0 else 0
position_size_usd = position_size_units * entry_price

st.sidebar.info(f"💡 **Position Sizing:** Risk: **${risk_amount_usd:.2f}** | Size: **{position_size_units:,.2f} units**")

# 4. Main Dashboard Area
trend_desc, pattern = detect_dominant_pattern(df)

col1, col2 = st.columns([3, 1])

with col1:
    st.write(f"### Market Analysis for {symbol}")
    st.info(f"📊 **Trend Structure:** {trend_desc} | **Dominant Pattern:** {pattern['name'] if pattern else 'No Clear Pattern'}")
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], name='EMA 50', line=dict(color='#2196f3', width=1.5)))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], name='EMA 200', line=dict(color='#ff9800', width=1.5)))
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📌 Metrics & Risk")
    st.metric(label="Live Price", value=f"${current_price:,.4f}")
    st.metric(label="Account Risk", value=f"${risk_amount_usd:,.2f}")
    st.metric(label="Units to Buy", value=f"{position_size_units:,.2f}")
    st.divider()
    rrr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0
    st.success(f"📌 **RRR Ratio:** 1:{rrr:.2f}")
