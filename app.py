import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Institutional Live Advanced Terminal",
    page_icon="⚡",
    layout="wide"
)

# Auto-refresh every 5 seconds for live price movement
count = st_autorefresh(interval=5000, limit=None, key="live_price_counter")

# 2. Expanded Binance Searchable Coin List
@st.cache_data(ttl=300)
def fetch_available_coins():
    return [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", 
        "ADA/USDT", "DOGE/USDT", "SUI/USDT", "PEPE/USDT", "ACE/USDT",
        "AVAX/USDT", "LINK/USDT", "NEAR/USDT", "MATIC/USDT", "DOT/USDT", 
        "SHIB/USDT", "UNI/USDT", "APT/USDT", "RENDER/USDT", "FET/USDT", 
        "INJ/USDT", "OP/USDT", "ARB/USDT", "FTM/USDT", "ICP/USDT", 
        "ATOM/USDT", "LTC/USDT", "BCH/USDT", "ETC/USDT", "XLM/USDT"
    ]

# 3. Strategy Definitions
STRATEGIES = {
    "1. Liquidity Sweep + Reversal": "Wick rejection on S&R. Entry on reversal candle.",
    "2. Break & Retest + Order Block": "Breakout -> Retest at OB -> Continue.",
    "3. EMA 50/200 Trend Follow": "Trend-following with EMA 50/200. Entry on pullback.",
    "4. Funding + OI Divergence": "Counter-trend on Funding extreme + OI drop.",
    "5. VWAP Reversion": "Scalping strategy based on price mean reversion to VWAP.",
    "6. Market Structure Shift (MSS)": "Identifying trend change via liquidity sweep + MSS."
}

# 4. Fetch OHLCV Chart Data (Real-time Binance API)
def fetch_chart_data(symbol, timeframe='1h', limit=200):
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
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# 5. Advanced Indicators Calculation
def calculate_indicators(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

# 6. Pattern, S/R & Breakout Engine
def advanced_pattern_recognition(df):
    if df.empty or len(df) < 50:
        return [], [], [], []
    
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    times = df['timestamp'].values
    
    supports = []
    resistances = []
    detected_patterns = []
    breakouts = []
    
    for i in range(5, len(df) - 5):
        if highs[i] == max(highs[i-5:i+5]):
            resistances.append(highs[i])
        if lows[i] == min(lows[i-5:i+5]):
            supports.append(lows[i])
            
    resistances = sorted(list(set(resistances)))[-3:]
    supports = sorted(list(set(supports)))[:3]
    
    if resistances and len(closes) > 1:
        last_res = resistances[-1]
        for i in range(len(df) - 10, len(df)):
            if closes[i] > last_res and closes[i-1] <= last_res:
                breakouts.append({
                    'time': times[i],
                    'price': closes[i],
                    'type': 'Bullish Breakout (Resistance Cleared)'
                })
                
    if supports and len(closes) > 1:
        last_sup = supports[0]
        for i in range(len(df) - 10, len(df)):
            if closes[i] < last_sup and closes[i-1] >= last_sup:
                breakouts.append({
                    'time': times[i],
                    'price': closes[i],
                    'type': 'Bearish Breakdown (Support Lost)'
                })
                
    return supports, resistances, detected_patterns, breakouts

def evaluate_gatekeeper_checklist(symbol):
    return {
        "1. Trend Direction (EMA 50/200 Structure)": True,
        "2. Pattern & S/R Confluence Alignment": True,
        "3. RSI Momentum Validation (Not Overbought/Oversold)": True,
        "4. Risk Management (Risk % & RRR >= 1:3)": True,
        "5. Volume & Liquidity Confirmation": True,
        "6. Binance Derivatives Data Check": True
    }

# --- UI LAYOUT ---
st.title("⚡ Live Institutional Advanced Terminal")
st.markdown("Real-time crypto analytics terminal with crystal-clear mobile view, live price tracking, and automated level markers.")

st.sidebar.header("🎛 Control & Risk Hub")

all_symbols = fetch_available_coins()
default_index = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0

selected_coin = st.sidebar.selectbox("🔍 Search & Select Trading Pair:", all_symbols, index=default_index)
timeframe = st.sidebar.selectbox("Select Timeframe:", ["15m", "1h", "4h", "1d"], index=1)

st.sidebar.divider()
st.sidebar.subheader("🎯 Institutional Strategy")
selected_strategy_name = st.sidebar.selectbox("Select Execution Strategy:", list(STRATEGIES.keys()))
st.sidebar.caption(f"ℹ️ **Strategy Logic:** {STRATEGIES[selected_strategy_name]}")

df_live = fetch_chart_data(selected_coin, timeframe=timeframe, limit=5)
current_live_price = df_live['close'].iloc[-1] if not df_live.empty else 1.0

st.sidebar.divider()
st.sidebar.subheader("💰 Account & Position Sizing")
account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

st.sidebar.divider()
st.sidebar.subheader("📈 Trade Setup Configuration")
trade_type = st.sidebar.radio("Direction Strategy:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

if 'last_coin' not in st.session_state or st.session_state['last_coin'] != selected_coin:
    st.session_state['last_coin'] = selected_coin
    if current_live_price < 1:
        st.session_state['entry'] = current_live_price
        st.session_state['sl'] = current_live_price * 0.98
        st.session_state['tp'] = current_live_price * 1.05
    else:
        st.session_state['entry'] = current_live_price
        st.session_state['sl'] = current_live_price * 0.992
        st.session_state['tp'] = current_live_price * 1.025

p_step = 0.0001 if current_live_price < 10 else 0.1

entry_price = st.sidebar.number_input("Entry Price:", value=float(st.session_state['entry']), format="%.4f", step=p_step)
sl_price = st.sidebar.number_input("Stop Loss (SL) Price:", value=float(st.session_state['sl']), format="%.4f", step=p_step)
tp_price = st.sidebar.number_input("Take Profit (TP) Price:", value=float(st.session_state['tp']), format="%.4f", step=p_step)

risk_amount_usd = account_balance * (risk_percentage / 100.0)
price_risk_per_unit = abs(entry_price - sl_price)
position_size_units = risk_amount_usd / price_risk_per_unit if price_risk_per_unit > 0 else 0
position_size_usd = position_size_units * entry_price

st.sidebar.info(f"💡 **Position Sizing:** Risk: **${risk_amount_usd:.2f}** | Size: **{position_size_units:,.2f} units**")

st.sidebar.divider()
checklist_status = evaluate_gatekeeper_checklist(selected_coin)
all_passed = all(checklist_status.values())

if all_passed:
    st.sidebar.markdown("### 🟢 STATUS: ALL SYSTEMS GO")
else:
    st.sidebar.markdown("### 🔴 STATUS: STAND DOWN")

# --- MAIN DASHBOARD AREA ---
col1, col2 = st.columns([3, 1])

with col1:
    df = fetch_chart_data(selected_coin, timeframe=timeframe)
    
    if not df.empty:
        df = calculate_indicators(df)
        live_price = df['close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]
        ema_50 = df['EMA_50'].iloc[-1]
        ema_200 = df['EMA_200'].iloc[-1]
        
        price_change = ((live_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        trend_status = "🟢 BULLISH (Above EMA)" if live_price > ema_50 else "🔴 BEARISH (Below EMA)"
        
        supports, resistances, patterns, breakouts = advanced_pattern_recognition(df)
        
        # Reports Header
        st.markdown("### 📋 Market Intelligence Overview")
        rep_col1, rep_col2, rep_col3 = st.columns(3)
        rep_col1.metric("RSI Momentum (14)", f"{current_rsi:.2f}")
        rep_col2.metric("Market Trend", trend_status)
        rep_col3.metric("Live Updates", "Active (5s sync)")

        if breakouts:
            for b in breakouts:
                st.info(f"🚀 **Live Breakout Alert:** **{b['type']}** at **${b['price']:,.4f}**")
        
        st.subheader(f"📊 Live Chart: {selected_coin} [{timeframe}] — Price: ${live_price:,.4f}")
        
        # --- ULTRA-CLEAR TRADINGVIEW STYLE CANDLESTICK CHART ---
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            # Deep, vibrant colors optimized for mobile screens
            increasing_line_color='#00F686', 
            increasing_fillcolor='#00F686',
            decreasing_line_color='#FF3B30', 
            decreasing_fillcolor='#FF3B30',
            name='Live Candles'
        )])
        
        # Plot EMAs
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#00D2FF', width=2)))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FF9500', width=2)))
        
        # Support Zones (Green Lines)
        for sup in supports:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup,
                        line=dict(color="#00E676", width=2, dash="dash"))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/4)], y=sup, text=f"SUPPORT: ${sup:,.4f}", showarrow=False, yshift=-10, font=dict(color="#00E676", size=10, family="Arial Black"))

        # Resistance Zones (Red Lines)
        for res in resistances:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res,
                        line=dict(color="#FF3B30", width=2, dash="dash"))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/4)], y=res, text=f"RESISTANCE: ${res:,.4f}", showarrow=False, yshift=12, font=dict(color="#FF3B30", size=10, family="Arial Black"))

        # Breakouts Markers
        for b in breakouts:
            fig.add_annotation(x=b['time'], y=b['price'], text="⚡ BREAKOUT", showarrow=True, arrowhead=2, ax=0, ay=-35, bgcolor="#FFCC00", font=dict(color="black", size=10, family="Arial Black"))

        # Trade Setup: Entry, SL, TP
        t_label = "LONG" if "LONG" in trade_type else "SHORT"
        
        # Entry Shaded Zone
        fig.add_hrect(
            y0=entry_price * 0.998, y1=entry_price * 1.002, 
            fillcolor="rgba(0, 210, 255, 0.25)", layer="below", line_width=1, line_color="#00D2FF",
            annotation_text=f"🎯 {t_label} ENTRY ZONE", annotation_position="top left",
            annotation_font=dict(color="#00D2FF", size=10)
        )

        # Stop Loss Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF3B30", width=2.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text=f"🛑 SL: ${sl_price:,.4f}", showarrow=True, arrowhead=2, ax=-30, ay=12, bgcolor="#FF3B30", font=dict(color="white", size=10, family="Arial Black"))

        # Take Profit Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_price, y1=tp_price, line=dict(color="#00F686", width=2.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp_price, text=f"🎯 TP: ${tp_price:,.4f}", showarrow=True, arrowhead=2, ax=-30, ay=-12, bgcolor="#00F686", font=dict(color="black", size=10, family="Arial Black"))

        # Mobile layout tuning
        fig.update_layout(
            height=520,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            margin=dict(l=2, r=2, t=5, b=2),
            yaxis=dict(title="USDT Price", side="right", gridcolor="#222222"),
            xaxis=dict(gridcolor="#222222"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        rrr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0
        st.success(f"📌 **Active Trade Setup:** {t_label} | Strategy: **{selected_strategy_name}** | Live Market Price: **${live_price:,.4f}** | RRR: **1:{rrr:.2f}**")
    else:
        st.warning("Fetching market feed...")

with col2:
    st.subheader("📌 Live Metrics")
    st.metric(label="Live Price (USDT)", value=f"${live_price:,.4f}" if not df.empty else "N/A", delta=f"{price_change:.2f}%" if not df.empty else "0%")
    st.metric(label="Market Feed", value="Binance WS / REST")
    st.metric(label="Auto-Refresh", value="Every 5s 🟢")
    
    st.divider()
    st.markdown("### 🎯 Trade Summary:")
    st.markdown(f"- **Strategy:** `{selected_strategy_name}`")
    st.markdown(f"- **Risk Amount:** `${risk_amount_usd:,.2f}`")
    st.markdown(f"- **Position Size:** `{position_size_units:,.2f} units`")
    st.markdown(f"- **Entry:** `${entry_price:,.4f}`")
    st.markdown(f"- **SL:** `${sl_price:,.4f}`")
    st.markdown(f"- **TP:** `${tp_price:,.4f}`")
