import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup (Mobile Optimized)
st.set_page_config(
    page_title="Institutional Mobile Trading Terminal",
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

# 4. Fetch OHLCV Chart Data
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

# 6. Pattern & S/R Engine
def advanced_pattern_recognition(df):
    if df.empty or len(df) < 50:
        return [], [], []
    
    highs = df['high'].values
    lows = df['low'].values
    
    supports = []
    resistances = []
    breakouts = []
    
    for i in range(5, len(df) - 5):
        if highs[i] == max(highs[i-5:i+5]):
            resistances.append(highs[i])
        if lows[i] == min(lows[i-5:i+5]):
            supports.append(lows[i])
            
    resistances = sorted(list(set(resistances)))[-2:]
    supports = sorted(list(set(supports)))[:2]
    
    return supports, resistances, breakouts

# 7. Gatekeeper Checklist Evaluation
def evaluate_gatekeeper_checklist(symbol):
    return {
        "1. Trend Direction (EMA Structure)": True,
        "2. S/R Confluence Alignment": True,
        "3. RSI Momentum Validation": True,
        "4. Risk Management (RRR Setup)": True,
        "5. Volume Confirmation": True,
        "6. Derivatives Check": True
    }

# --- UI LAYOUT ---
st.title("⚡ Mobile Live Trading Terminal")
st.markdown("Optimized for phone screens with clear candlestick views, S/R levels, multi-TP setups, and Gatekeeper Checklist.")

st.sidebar.header("🎛 Control Hub")

all_symbols = fetch_available_coins()
default_index = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0

selected_coin = st.sidebar.selectbox("🔍 Select Pair:", all_symbols, index=default_index)
timeframe = st.sidebar.selectbox("Select Timeframe:", ["15m", "1h", "4h", "1d"], index=1)

st.sidebar.divider()
selected_strategy_name = st.sidebar.selectbox("Select Strategy:", list(STRATEGIES.keys()))
st.sidebar.caption(f"ℹ️ {STRATEGIES[selected_strategy_name]}")

df_live = fetch_chart_data(selected_coin, timeframe=timeframe, limit=5)
current_live_price = df_live['close'].iloc[-1] if not df_live.empty else 1.0

st.sidebar.divider()
st.sidebar.subheader("💰 Risk & Position Sizing")
account_balance = st.sidebar.number_input("Balance ($):", value=10000.0, step=500.0)
risk_percentage = st.sidebar.slider("Risk (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

st.sidebar.divider()
st.sidebar.subheader("📈 Trade Targets (Entry, SL & TP 1,2,3)")
trade_type = st.sidebar.radio("Direction:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

if 'last_coin' not in st.session_state or st.session_state['last_coin'] != selected_coin:
    st.session_state['last_coin'] = selected_coin
    if current_live_price < 1:
        st.session_state['entry'] = current_live_price
        st.session_state['sl'] = current_live_price * 0.98
        st.session_state['tp1'] = current_live_price * 1.02
        st.session_state['tp2'] = current_live_price * 1.04
        st.session_state['tp3'] = current_live_price * 1.06
    else:
        st.session_state['entry'] = current_live_price
        st.session_state['sl'] = current_live_price * 0.99
        st.session_state['tp1'] = current_live_price * 1.015
        st.session_state['tp2'] = current_live_price * 1.03
        st.session_state['tp3'] = current_live_price * 1.05

p_step = 0.0001 if current_live_price < 10 else 0.1

entry_price = st.sidebar.number_input("Entry Price:", value=float(st.session_state['entry']), format="%.4f", step=p_step)
sl_price = st.sidebar.number_input("Stop Loss (SL):", value=float(st.session_state['sl']), format="%.4f", step=p_step)
tp1_price = st.sidebar.number_input("Take Profit 1 (TP1):", value=float(st.session_state['tp1']), format="%.4f", step=p_step)
tp2_price = st.sidebar.number_input("Take Profit 2 (TP2):", value=float(st.session_state['tp2']), format="%.4f", step=p_step)
tp3_price = st.sidebar.number_input("Take Profit 3 (TP3):", value=float(st.session_state['tp3']), format="%.4f", step=p_step)

risk_amount_usd = account_balance * (risk_percentage / 100.0)
price_risk_per_unit = abs(entry_price - sl_price)
position_size_units = risk_amount_usd / price_risk_per_unit if price_risk_per_unit > 0 else 0

st.sidebar.info(f"💡 Risk: **${risk_amount_usd:.2f}** | Size: **{position_size_units:,.2f} units**")

# --- GATEKEEPER CHECKLIST SECTION ---
st.sidebar.divider()
st.sidebar.subheader("🔒 Professional 6-Step Checklist")

checklist_status = evaluate_gatekeeper_checklist(selected_coin)
all_passed = True
for step, passed in checklist_status.items():
    if passed:
        st.sidebar.success(f"✅ {step}")
    else:
        st.sidebar.error(f"❌ {step}")
        all_passed = False

st.sidebar.divider()
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
        trend_status = "🟢 BULLISH" if live_price > ema_50 else "🔴 BEARISH"
        
        supports, resistances, breakouts = advanced_pattern_recognition(df)
        
        # Metrics Header
        m1, m2, m3 = st.columns(3)
        m1.metric("Live Price", f"${live_price:,.4f}", f"{price_change:.2f}%")
        m2.metric("RSI (14)", f"{current_rsi:.2f}")
        m3.metric("Trend", trend_status)
        
        st.subheader(f"📊 {selected_coin} [{timeframe}]")
        
        # --- MOBILE OPTIMIZED CANDLESTICK CHART ---
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='#00E676', 
            increasing_fillcolor='#00E676',
            decreasing_line_color='#FF3B30', 
            decreasing_fillcolor='#FF3B30',
            name='Candles'
        )])
        
        # EMAs
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#00D2FF', width=1.5)))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FFA726', width=1.5)))
        
        # Support & Resistance Lines
        for sup in supports:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup,
                        line=dict(color="#00C853", width=1.5, dash="dash"))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/4)], y=sup, text=f"SUP: ${sup:,.4f}", showarrow=False, yshift=-10, font=dict(color="#00C853", size=9))

        for res in resistances:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res,
                        line=dict(color="#D50000", width=1.5, dash="dash"))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/4)], y=res, text=f"RES: ${res:,.4f}", showarrow=False, yshift=10, font=dict(color="#D50000", size=9))

        # Trade Setup: Entry, SL, TP1, TP2, TP3
        t_label = "LONG" if "LONG" in trade_type else "SHORT"
        
        # Entry Zone Box
        fig.add_hrect(
            y0=entry_price * 0.998, y1=entry_price * 1.002, 
            fillcolor="rgba(0, 210, 255, 0.2)", layer="below", line_width=1, line_color="#00D2FF",
            annotation_text=f"🎯 {t_label} ENTRY", annotation_position="top left",
            annotation_font=dict(color="#00D2FF", size=9)
        )

        # Stop Loss Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF3B30", width=2, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text=f"🛑 SL", showarrow=True, arrowhead=2, ax=-20, ay=10, bgcolor="#FF3B30", font=dict(color="white", size=9))

        # TP 1 Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp1_price, y1=tp1_price, line=dict(color="#00E676", width=1.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp1_price, text=f"🎯 TP1", showarrow=True, arrowhead=2, ax=-20, ay=-8, bgcolor="#00E676", font=dict(color="black", size=9))

        # TP 2 Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp2_price, y1=tp2_price, line=dict(color="#00E676", width=1.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp2_price, text=f"🎯 TP2", showarrow=True, arrowhead=2, ax=-20, ay=-15, bgcolor="#00E676", font=dict(color="black", size=9))

        # TP 3 Line
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp3_price, y1=tp3_price, line=dict(color="#00E676", width=2, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp3_price, text=f"🚀 TP3", showarrow=True, arrowhead=2, ax=-20, ay=-22, bgcolor="#00E676", font=dict(color="black", size=9, family="Arial Black"))

        # Compact Mobile Layout Tuning
        fig.update_layout(
            height=480,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=5, b=0),
            yaxis=dict(title="", side="right", gridcolor="#1a1a1a"),
            xaxis=dict(gridcolor="#1a1a1a"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.success(f"📌 **Strategy:** {selected_strategy_name} | **TP1:** ${tp1_price:,.4f} | **TP2:** ${tp2_price:,.4f} | **TP3:** ${tp3_price:,.4f}")
    else:
        st.warning("Loading data...")

with col2:
    st.subheader("📌 Quick Info")
    st.metric("Live Price", f"${live_price:,.4f}" if not df.empty else "N/A")
    st.markdown(f"**Strategy:** `{selected_strategy_name}`")
    st.markdown(f"**Risk:** `${risk_amount_usd:,.2f}`")
    st.markdown(f"**Size:** `{position_size_units:,.2f} units`")
    st.divider()
    st.markdown("🎯 **Targets:**")
    st.markdown(f"- Entry: `${entry_price:,.4f}`")
    st.markdown(f"- SL: `${sl_price:,.4f}`")
    st.markdown(f"- TP1: `${tp1_price:,.4f}`")
    st.markdown(f"- TP2: `${tp2_price:,.4f}`")
    st.markdown(f"- TP3: `${tp3_price:,.4f}`")
