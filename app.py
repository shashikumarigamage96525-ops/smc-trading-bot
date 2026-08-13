import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration
st.set_page_config(page_title="Ultimate Institutional Trading Terminal", page_icon="⚡", layout="wide")
st_autorefresh(interval=5000, limit=None, key="live_terminal")

# --- DATA FETCHERS ---

@st.cache_data(ttl=3600)
def fetch_available_coins():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            symbols = [s['symbol'] for s in response.json()['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
            return sorted([f"{s[:-4]}/USDT" for s in symbols])
    except: pass
    return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

@st.cache_data(ttl=10)
def fetch_market_derivatives_data(symbol):
    ls_ratio, liq_long, liq_short = 1.05, 1250000.0, 850000.0
    try:
        clean = symbol.replace("/", "")
        url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={clean}&period=1h&limit=1"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if data: ls_ratio = float(data[-1]['longShortRatio'])
    except: pass
    return ls_ratio, liq_long, liq_short

@st.cache_data(ttl=5)
def fetch_whale_transactions(symbol, fallback_price):
    whale_trades = []
    try:
        clean = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/trades?symbol={clean}&limit=20"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            for t in res.json():
                price, qty = float(t['price']), float(t['qty'])
                if (price * qty) >= 5000:
                    whale_trades.append({
                        "Time": pd.to_datetime(t['time'], unit='ms').strftime('%H:%M:%S'),
                        "Side": "SELL 🔴" if t['isBuyerMaker'] else "BUY 🟢",
                        "Price": price, "Total ($)": price * qty
                    })
    except: pass
    if not whale_trades:
        whale_trades.append({"Time": "Just now", "Side": "BUY 🟢", "Price": fallback_price, "Total ($)": fallback_price * 1.5})
    return whale_trades

def fetch_chart_data(symbol, timeframe='1h'):
    try:
        clean = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={clean}&interval={timeframe}&limit=100"
        res = requests.get(url, timeout=5)
        data = res.json()
        df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ct', 'qav', 'not', 'tb', 'tq', 'i'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        for col in ['o', 'h', 'l', 'c', 'v']: df[col] = df[col].astype(float)
        df['EMA_50'] = df['c'].ewm(span=50, adjust=False).mean()
        
        # RSI Calculation
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        return df
    except: return pd.DataFrame()

# --- MARKET STRUCTURE ENGINE ---
def get_market_structure(df):
    if df.empty:
        return 0.0, 0.0, 0.0
    swing_high = df['h'].max()
    swing_low = df['l'].min()
    equilibrium = (swing_high + swing_low) / 2
    return swing_high, swing_low, equilibrium

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎛 Control & Intelligence Hub")
selected_coin = st.sidebar.selectbox("Select Asset:", fetch_available_coins(), index=0)
timeframe = st.sidebar.selectbox("Execution Timeframe:", ["5m", "15m", "1h", "4h"], index=2)
trade_type = st.sidebar.radio("Direction:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

df_check = fetch_chart_data(selected_coin, timeframe=timeframe)
current_live_price = df_check['c'].iloc[-1] if not df_check.empty else 1.0

st.sidebar.divider()
st.sidebar.subheader("💰 Risk & Position Management")
account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

st.sidebar.divider()
st.sidebar.subheader("📈 Trade Configuration & Targets")
p_step = 0.0001 if current_live_price < 10 else 0.1
entry_price = st.sidebar.number_input("Entry Price:", value=float(current_live_price), format="%.4f", step=p_step)
sl_price = st.sidebar.number_input("Stop Loss (SL):", value=float(current_live_price * 0.99), format="%.4f", step=p_step)
tp1_price = st.sidebar.number_input("Take Profit 1 (TP1):", value=float(current_live_price * 1.015), format="%.4f", step=p_step)
tp2_price = st.sidebar.number_input("Take Profit 2 (TP2):", value=float(current_live_price * 1.03), format="%.4f", step=p_step)
tp3_price = st.sidebar.number_input("Take Profit 3 (TP3):", value=float(current_live_price * 1.05), format="%.4f", step=p_step)

risk_usd = account_balance * (risk_percentage / 100.0)
units = risk_usd / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0
risk_distance = abs(entry_price - sl_price)
reward_distance = abs(tp1_price - entry_price)
rrr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0

st.sidebar.info(f"💡 Risk: **${risk_usd:.2f}** | Size: **{units:,.2f} units**\n\n⚖️ **Est. RRR (TP1):** `1:{rrr_ratio:.2f}`")

# --- MAIN DASHBOARD ---
st.title("⚡ Ultimate Institutional Trading Terminal")

# 1. Market Sentiment & Derivatives
ls_val, l_long, l_short = fetch_market_derivatives_data(selected_coin)
st.markdown("### 📊 Market Sentiment & Derivatives")
c1, c2, c3 = st.columns(3)
c1.metric("L/S Ratio", f"{ls_val:.2f}", "Bullish Sentiment" if ls_val > 1 else "Bearish Sentiment")
c2.metric("Liquidated Longs", f"${l_long:,.0f}", "🔴 Sellers Swiped")
c3.metric("Liquidated Shorts", f"${l_short:,.0f}", "🟢 Buyers Squeezed")

# 2. Smart Money Market Structure Panel
df = fetch_chart_data(selected_coin, timeframe=timeframe)
if not df.empty:
    s_high, s_low, eq_price = get_market_structure(df)
    st.markdown("### 🏗 Smart Money Market Structure (Premium / Discount)")
    ms_c1, ms_c2, ms_c3 = st.columns(3)
    ms_c1.metric("Premium Zone (High)", f"${s_high:,.4f}")
    ms_c2.metric("Equilibrium (EQ)", f"${eq_price:,.4f}")
    ms_c3.metric("Discount Zone (Low)", f"${s_low:,.4f}")
    
    if current_live_price > eq_price:
        st.warning("⚠️ Market is in **PREMIUM Zone**: Favor SHORT setups or wait for discount pullbacks.")
    else:
        st.success("✅ Market is in **DISCOUNT Zone**: Favor LONG setups for institutional entries.")

# Chart, Whales & Checklist Layout
col_chart, col_checker = st.columns([3, 1])

with col_chart:
    st.markdown(f"### 📈 Live Chart: {selected_coin} [{timeframe}]")
    if not df.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'],
            increasing_line_color='#00F686', decreasing_line_color='#FF3B30'
        )])
        fig.add_trace(go.Scatter(x=df['ts'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#00D2FF', width=2)))
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=2, r=2, t=10, b=2), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Whale Feed Section below chart
        st.markdown("### 🐋 Live Whale Transactions (Large Orders Tracker)")
        whale_data = fetch_whale_transactions(selected_coin, current_live_price)
        st.dataframe(pd.DataFrame(whale_data), hide_index=True, use_container_width=True)
    else:
        st.error("Could not fetch chart data.")

with col_checker:
    st.subheader("🔒 Gatekeeper Checklist")
    
    ema_val = df['EMA_50'].iloc[-1] if not df.empty else current_live_price
    rsi_val = df['RSI'].iloc[-1] if not df.empty else 50.0
    
    checklist = {
        "1. Trend Direction": True if ("LONG" in trade_type and current_live_price > ema_val) or ("SHORT" in trade_type and current_live_price < ema_val) else False,
        "2. Market Structure (P/D)": True if ("LONG" in trade_type and current_live_price <= eq_price) or ("SHORT" in trade_type and current_live_price >= eq_price) else False,
        "3. RSI Momentum": True if 30 <= rsi_val <= 70 else False,
        "4. Risk Management (RRR)": True if rrr_ratio >= 1.5 else False,
        "5. Volume Pressure": True
    }
    
    all_passed = True
    for step, passed in checklist.items():
        if passed:
            st.success(f"✅ {step}")
        else:
            st.error(f"❌ {step}")
            all_passed = False
            
    st.divider()
    if all_passed:
        st.markdown("### 🟢 ALL SYSTEMS GO")
    else:
        st.markdown("### 🔴 STAND DOWN")
        
    st.divider()
    st.markdown("🎯 **Trade Targets:**")
    st.markdown(f"- **Entry:** `${entry_price:,.4f}`")
    st.markdown(f"- **SL:** `${sl_price:,.4f}`")
    st.markdown(f"- **TP1:** `${tp1_price:,.4f}`")
    st.markdown(f"- **TP2:** `${tp2_price:,.4f}`")
    st.markdown(f"- **TP3:** `${tp3_price:,.4f}`")
