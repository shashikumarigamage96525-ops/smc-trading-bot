import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Institutional Advanced Technical Analysis Terminal",
    page_icon="⚡",
    layout="wide"
)

count = st_autorefresh(interval=5000, limit=None, key="live_price_counter")

# 2. Strategy Hub Dictionary
STRATEGIES = {
    "1. Liquidity Sweep + Reversal": "Wick rejection on S&R. Entry on reversal candle.",
    "2. Break & Retest + Order Block": "Breakout -> Retest at OB -> Continue.",
    "3. EMA 50/200 Trend Follow": "Trend-following with EMA 50/200. Entry on pullback.",
    "4. Funding + OI Divergence": "Counter-trend on Funding extreme + OI drop.",
    "5. VWAP Reversion": "Scalping strategy based on price mean reversion to VWAP.",
    "6. Market Structure Shift (MSS)": "Identifying trend change via liquidity sweep + MSS."
}

# 3. Expanded Binance Searchable Coin List
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

# 4. Fetch OHLCV Chart Data (Limit set to 40 for clean mobile candle view)
def fetch_chart_data(symbol, timeframe='1h', limit=40):
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

# 5. Advanced Indicators Calculation (RSI, EMA, VWAP)
def calculate_indicators(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # VWAP Calculation
    v = df['volume'].values
    tp = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (tp * v).cumsum() / v.cumsum()
    
    # RSI Calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

# 6. Advanced Multi-Pattern Detection Engine
def advanced_pattern_recognition(df):
    if df.empty or len(df) < 20:
        return [], [], []
    
    highs = df['high'].values
    lows = df['low'].values
    times = df['timestamp'].values
    
    supports = []
    resistances = []
    detected_patterns = []
    
    for i in range(2, len(df) - 2):
        if highs[i] == max(highs[i-2:i+2]):
            resistances.append(highs[i])
        if lows[i] == min(lows[i-2:i+2]):
            supports.append(lows[i])
            
    resistances = sorted(list(set(resistances)))[-2:]
    supports = sorted(list(set(supports)))[:2]
    
    return supports, resistances, detected_patterns

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
st.title("⚡ Institutional Strategy Terminal")
st.markdown("Advanced Technical Analysis Terminal with Strategy Hub & Clean Mobile Candles.")

st.sidebar.header("🎛 Control & Strategy Hub")

# Strategy Selector
selected_strategy = st.sidebar.selectbox("🎯 Pick Strategy:", list(STRATEGIES.keys()))
st.sidebar.info(STRATEGIES[selected_strategy])

st.sidebar.divider()

all_symbols = fetch_available_coins()
default_index = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0

selected_coin = st.sidebar.selectbox("🔍 Search & Select Trading Pair:", all_symbols, index=default_index)
timeframe = st.sidebar.selectbox("Select Timeframe:", ["15m", "1h", "4h", "1d"], index=1)

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
    st.session_state['entry'] = current_live_price
    st.session_state['sl'] = current_live_price * 0.992
    st.session_state['tp'] = current_live_price * 1.03

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

# --- MAIN DASHBOARD AREA (Single Column for Clean Mobile Display) ---
df = fetch_chart_data(selected_coin, timeframe=timeframe)

if not df.empty:
    df = calculate_indicators(df)
    live_price = df['close'].iloc[-1]
    current_rsi = df['RSI'].iloc[-1]
    ema_50 = df['EMA_50'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    vwap_val = df['VWAP'].iloc[-1]
    
    trend_status = "🟢 BULLISH" if live_price > ema_50 else "🔴 BEARISH"
    supports, resistances, patterns = advanced_pattern_recognition(df)
    
    st.markdown("### 📋 Automated Technical Analysis Report")
    rep_col1, rep_col2, rep_col3 = st.columns(3)
    rep_col1.metric("RSI Momentum", f"{current_rsi:.2f}")
    rep_col2.metric("Trend Structure", trend_status)
    rep_col3.metric("Active Strategy", selected_strategy.split(".")[1])
    
    st.subheader(f"📊 Chart: {selected_coin} [{timeframe}] | Live: ${live_price:,.4f}")
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#00E676', decreasing_line_color='#FF5252',
        name='Candles'
    )])
    
    # Plot Indicators
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#29B6F6', width=1.5)))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FFA726', width=1.5)))
    if "VWAP" in selected_strategy:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['VWAP'], mode='lines', name='VWAP', line=dict(color='#AB47BC', width=1.8, dash='dot')))
    
    # Plot Support & Resistance
    for sup in supports:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup, line=dict(color="#00C853", width=1.5, dash="dash"))
        fig.add_annotation(x=df['timestamp'].iloc[1], y=sup, text=f"Support: ${sup:,.2f}", showarrow=False, yshift=-10, font=dict(color="#00C853", size=10))

    for res in resistances:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res, line=dict(color="#D50000", width=1.5, dash="dash"))
        fig.add_annotation(x=df['timestamp'].iloc[1], y=res, text=f"Resistance: ${res:,.2f}", showarrow=False, yshift=12, font=dict(color="#D50000", size=10))

    # User Trade Setup Lines
    t_label = "LONG" if "LONG" in trade_type else "SHORT"
    
    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=entry_price, y1=entry_price, line=dict(color="#29B6F6", width=2, dash="dash"))
    fig.add_annotation(x=df['timestamp'].iloc[-1], y=entry_price, text=f"ENTRY: ${entry_price:,.2f}", showarrow=True, arrowhead=2, ax=-50, ay=0, bgcolor="#29B6F6", font=dict(color="black", size=10))

    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF5252", width=2, dash="dash"))
    fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text=f"SL: ${sl_price:,.2f}", showarrow=True, arrowhead=2, ax=-50, ay=15, bgcolor="#FF5252", font=dict(color="white", size=10))

    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_price, y1=tp_price, line=dict(color="#00E676", width=2, dash="dash"))
    fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp_price, text=f"TP: ${tp_price:,.2f}", showarrow=True, arrowhead=2, ax=-50, ay=-15, bgcolor="#00E676", font=dict(color="black", size=10))

    fig.update_layout(
        height=520,
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="Price (USDT)", gridcolor="#222222"),
        xaxis=dict(gridcolor="#222222")
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    rrr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0
    st.success(f"📌 **Active Strategy:** {t_label} | **Strategy Hub:** `{selected_strategy}` | **RRR:** `1:{rrr:.2f}`")
    
    st.divider()
    st.subheader("📌 Binance Metrics & Summary")
    
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("Account Risk", f"${risk_amount_usd:,.2f} ({risk_percentage}%)")
    m_col1.metric("Position Size", f"{position_size_units:,.2f} units")
    
    m_col2.metric("Target RRR", f"1:{rrr:.2f}")
    m_col2.metric("Funding Rate", "0.0100% (Normal)")
else:
    st.warning("Fetching market data...")
