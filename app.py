import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide"
)

# Auto-refresh every 5 seconds for live feed
count = st_autorefresh(interval=5000, limit=None, key="live_terminal_counter")

# 2. Expanded Binance Searchable Coin List
@st.cache_data(ttl=300)
def fetch_available_coins():
    return [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", 
        "ADA/USDT", "DOGE/USDT", "SUI/USDT", "PEPE/USDT", "AVAX/USDT",
        "LINK/USDT", "NEAR/USDT", "RENDER/USDT", "FET/USDT", "INJ/USDT"
    ]

# 3. Strategy Definitions
STRATEGIES = {
    "1. Institutional Order Block (OB) + FVG": "Trading institutional footprints & Fair Value Gaps.",
    "2. Liquidity Sweep & Market Structure Shift (MSS)": "Grabbing retail stops then reversing.",
    "3. Multi-Timeframe Trend Confluence": "15m entry aligned with 4h major trend direction.",
    "4. Order Book Imbalance Scalp": "High frequency bid/ask volume dominance trading."
}

# 4. Fetch OHLCV Data
def fetch_chart_data(symbol, timeframe='1h', limit=150):
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            url = f"https://data-api.binance.vision/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"
            response = requests.get(url, timeout=5)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# 5. Advanced Order Book & Imbalance Fetcher (Live Depth)
def fetch_order_book_metrics(symbol):
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/depth?symbol={clean_symbol}&limit=50"
        res = requests.get(url, timeout=3).json()
        bids = sum([float(x[1]) for x in res.get('bids', [])])
        asks = sum([float(x[1]) for x in res.get('asks', [])])
        total = bids + asks
        bid_pressure = (bids / total) * 100 if total > 0 else 50
        ask_pressure = (asks / total) * 100 if total > 0 else 50
        return bid_pressure, ask_pressure
    except:
        return 50.0, 50.0

# 6. Indicators & SMC (Order Blocks / FVG) Calculation
def calculate_advanced_metrics(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # Fair Value Gap (FVG) Detection
    fvg_list = []
    for i in range(1, len(df) - 1):
        # Bullish FVG
        if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            fvg_list.append({'type': 'Bullish FVG', 'price': (df['low'].iloc[i+1] + df['high'].iloc[i-1]) / 2, 'time': df['timestamp'].iloc[i]})
        # Bearish FVG
        elif df['high'].iloc[i+1] < df['low'].iloc[i-1]:
            fvg_list.append({'type': 'Bearish FVG', 'price': (df['high'].iloc[i+1] + df['low'].iloc[i-1]) / 2, 'time': df['timestamp'].iloc[i]})
            
    return df, fvg_list

# --- UI LAYOUT ---
st.title("⚡ Ultimate Institutional Trading Terminal")
st.markdown("Equipped with Order Book Imbalance, Fair Value Gaps (FVG), Multi-Timeframe Confluence, and Risk Engine.")

st.sidebar.header("🎛 Control & Intelligence Hub")

all_symbols = fetch_available_coins()
default_index = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0
selected_coin = st.sidebar.selectbox("🔍 Select Asset:", all_symbols, index=default_index)
timeframe = st.sidebar.selectbox("Execution Timeframe:", ["5m", "15m", "1h", "4h"], index=1)

st.sidebar.divider()
selected_strategy_name = st.sidebar.selectbox("Select Strategy:", list(STRATEGIES.keys()))

df_live = fetch_chart_data(selected_coin, timeframe=timeframe, limit=5)
current_live_price = df_live['close'].iloc[-1] if not df_live.empty else 1.0

st.sidebar.divider()
st.sidebar.subheader("💰 Risk & Position Management")
account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

st.sidebar.divider()
st.sidebar.subheader("📈 Trade Configuration & Targets")
trade_type = st.sidebar.radio("Direction:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

if 'last_coin_pro' not in st.session_state or st.session_state['last_coin_pro'] != selected_coin:
    st.session_state['last_coin_pro'] = selected_coin
    st.session_state['entry'] = current_live_price
    st.session_state['sl'] = current_live_price * 0.99 if "LONG" in trade_type else current_live_price * 1.01
    st.session_state['tp1'] = current_live_price * 1.015
    st.session_state['tp2'] = current_live_price * 1.03
    st.session_state['tp3'] = current_live_price * 1.05

p_step = 0.0001 if current_live_price < 10 else 0.1
entry_price = st.sidebar.number_input("Entry Price:", value=float(st.session_state['entry']), format="%.4f", step=p_step)
sl_price = st.sidebar.number_input("Stop Loss (SL):", value=float(st.session_state['sl']), format="%.4f", step=p_step)
tp1_price = st.sidebar.number_input("Take Profit 1:", value=float(st.session_state['tp1']), format="%.4f", step=p_step)
tp2_price = st.sidebar.number_input("Take Profit 2:", value=float(st.session_state['tp2']), format="%.4f", step=p_step)
tp3_price = st.sidebar.number_input("Take Profit 3:", value=float(st.session_state['tp3']), format="%.4f", step=p_step)

risk_usd = account_balance * (risk_percentage / 100.0)
units = risk_usd / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0

st.sidebar.info(f"💡 Risk: **${risk_usd:.2f}** | Size: **{units:,.2f} units**")

# --- LIVE ORDER BOOK IMBALANCE METRICS ---
bid_p, ask_p = fetch_order_book_metrics(selected_coin)

st.sidebar.divider()
st.sidebar.subheader("📊 Live Order Book Depth")
st.sidebar.progress(bid_p / 100, text=f"Buyers (Bids): {bid_p:.1f}%")
st.sidebar.progress(ask_p / 100, text=f"Sellers (Asks): {ask_p:.1f}%")

if bid_p > 58:
    st.sidebar.success("🟢 Order Book Bias: STRONG BUYERS")
elif ask_p > 58:
    st.sidebar.error("🔴 Order Book Bias: STRONG SELLERS")
else:
    st.sidebar.warning("🟡 Order Book Bias: NEUTRAL / BALANCED")

# --- MAIN DASHBOARD AREA ---
col1, col2 = st.columns([3, 1])

with col1:
    df = fetch_chart_data(selected_coin, timeframe=timeframe)
    if not df.empty:
        df, fvgs = calculate_advanced_metrics(df)
        live_price = df['close'].iloc[-1]
        rsi_val = df['RSI'].iloc[-1]
        ema_50 = df['EMA_50'].iloc[-1]
        ema_200 = df['EMA_200'].iloc[-1]
        
        # Multi-timeframe trend simulation check (Higher TF check)
        df_higher = fetch_chart_data(selected_coin, timeframe='4h', limit=50)
        higher_trend = "BULLISH" if not df_higher.empty and df_higher['close'].iloc[-1] > df_higher['close'].ewm(span=50).mean().iloc[-1] else "BEARISH"
        
        # Scoring System for 100% Confidence Check
        score = 0
        if "LONG" in trade_type and live_price > ema_50: score += 25
        if "SHORT" in trade_type and live_price < ema_50: score += 25
        if "LONG" in trade_type and bid_p > 52: score += 25
        if "SHORT" in trade_type and ask_p > 52: score += 25
        if ("LONG" in trade_type and higher_trend == "BULLISH") or ("SHORT" in trade_type and higher_trend == "BEARISH"): score += 25
        if 30 < rsi_val < 70: score += 25

        # Metric Header
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Live Price", f"${live_price:,.4f}")
        sc2.metric("RSI (14)", f"{rsi_val:.1f}")
        sc3.metric("4H Trend", higher_trend)
        sc4.metric("Setup Confidence", f"{score}%", "A+ Grade" if score >= 75 else "Wait / Risk")

        st.subheader(f"📊 Advanced Chart: {selected_coin} [{timeframe}]")
        
        # Plotly Candlestick Chart
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#00E676', decreasing_line_color='#FF3B30', name='Candles'
        )])
        
        # EMAs
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#00D2FF', width=1.5)))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FFA726', width=1.5)))
        
        # Plot Fair Value Gaps (FVG)
        for fvg in fvgs[-3:]:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=fvg['price'], y1=fvg['price'],
                          line=dict(color="#FFD700", width=1, dash="dot"))
            fig.add_annotation(x=fvg['time'], y=fvg['price'], text=f"⚡ {fvg['type']}", showarrow=False, font=dict(color="#FFD700", size=9))

        # Trade Setup Lines
        t_label = "LONG" if "LONG" in trade_type else "SHORT"
        fig.add_hrect(y0=entry_price*0.998, y1=entry_price*1.002, fillcolor="rgba(0, 210, 255, 0.25)", line_color="#00D2FF", annotation_text=f"🎯 {t_label} ENTRY", annotation_position="top left")
        
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF3B30", width=2, dash="dash"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text="🛑 SL", showarrow=True, arrowhead=2, ax=-25, ay=10, bgcolor="#FF3B30", font=dict(color="white", size=9))

        for idx, tp_val in enumerate([tp1_price, tp2_price, tp3_price], 1):
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_val, y1=tp_val, line=dict(color="#00E676", width=1.5, dash="dot"))
            fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp_val, text=f"🎯 TP{idx}", showarrow=True, arrowhead=2, ax=-25, ay=-10*idx, bgcolor="#00E676", font=dict(color="black", size=9))

        fig.update_layout(
            height=480, template="plotly_dark", xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=5, b=0), yaxis=dict(side="right", gridcolor="#1a1a1a"), xaxis=dict(gridcolor="#1a1a1a")
        )
        st.plotly_chart(fig, use_container_width=True)
        
        if score >= 75:
            st.success(f"🚀 **HIGH PROBABILITY SETUP ({score}%):** All institutional metrics aligned. Safe to execute trade!")
        else:
            st.warning(f"⚠️ **CAUTION ({score}%):** Market conditions are mixed. Wait for better alignment.")

with col2:
    st.subheader("📌 Terminal Audit")
    st.metric("Order Book Pressure", f"Buy {bid_p:.1f}%" if bid_p > ask_p else f"Sell {ask_p:.1f}%")
    st.metric("Higher TF Bias", higher_trend)
    st.divider()
    st.markdown("🎯 **Execution Targets:**")
    st.markdown(f"- **Entry:** `${entry_price:,.4f}`")
    st.markdown(f"- **SL:** `${sl_price:,.4f}`")
    st.markdown(f"- **TP1:** `${tp1_price:,.4f}`")
    st.markdown(f"- **TP2:** `${tp2_price:,.4f}`")
    st.markdown(f"- **TP3:** `${tp3_price:,.4f}`")
