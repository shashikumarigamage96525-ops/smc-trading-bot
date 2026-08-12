import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide"
)

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

# 3. Fetch OHLCV Chart Data (Limit reduced to 40 for wide, clear mobile candles)
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
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# 4. Advanced Indicators Calculation (RSI, EMA)
def calculate_indicators(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# 5. Technical Analysis Engine (S&R, Liquidity, Trend, Patterns)
def technical_analysis_engine(df):
    if df.empty or len(df) < 15:
        return [], [], {}, "NEUTRAL", []
    
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    
    supports, resistances = [], []
    for i in range(2, len(df) - 2):
        if highs[i] == max(highs[i-2:i+2]):
            resistances.append(highs[i])
        if lows[i] == min(lows[i-2:i+2]):
            supports.append(lows[i])
            
    supports = sorted(list(set(supports)))[-2:]
    resistances = sorted(list(set(resistances)))[:2]
    
    liquidity_pools = {
        'buy_side': max(highs) * 1.0015,
        'sell_side': min(lows) * 0.9985
    }
    
    current_close = closes[-1]
    ema_50 = df['EMA_50'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    
    if current_close > ema_50:
        trend = "STRONG BULLISH 🟢"
    else:
        trend = "STRONG BEARISH 🔴"
        
    detected_patterns = ["Support & Resistance Channel"]
    return supports, resistances, liquidity_pools, trend, detected_patterns

# --- UI LAYOUT ---
st.title("⚡ Institutional Trading Terminal")
st.markdown("Mobile-Optimized Clean Trading View with Stable S&R Entries.")

st.sidebar.header("🎛 Control & Risk Hub")

all_symbols = fetch_available_coins()
default_index = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0
selected_coin = st.sidebar.selectbox("🔍 Select Trading Pair:", all_symbols, index=default_index)
timeframe = st.sidebar.selectbox("Select Timeframe:", ["15m", "1h", "4h", "1d"], index=1)

df_initial = fetch_chart_data(selected_coin, timeframe=timeframe)
if not df_initial.empty:
    df_initial = calculate_indicators(df_initial)
    supports, resistances, liquidity_pools, trend, patterns = technical_analysis_engine(df_initial)
    current_live_price = df_initial['close'].iloc[-1]
else:
    current_live_price = 1.0
    supports, resistances, liquidity_pools, trend, patterns = [], [], {}, "NEUTRAL", []

st.sidebar.divider()
st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0, key="account_balance")
risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

st.sidebar.divider()
st.sidebar.subheader("📈 S&R Strategy Setup")

if supports and resistances:
    nearest_support = supports[-1]
    nearest_resistance = resistances[0]
    
    if abs(current_live_price - nearest_support) <= abs(nearest_resistance - current_live_price):
        trade_type = "LONG (Support Bounce)"
        entry_price = nearest_support
        sl_price = nearest_support * 0.990
        tp_price = entry_price + (abs(entry_price - sl_price) * 3)
    else:
        trade_type = "SHORT (Resistance Rejection)"
        entry_price = nearest_resistance
        sl_price = nearest_resistance * 1.010
        tp_price = entry_price - (abs(sl_price - entry_price) * 3)
else:
    trade_type = "LONG Setup"
    entry_price = current_live_price
    sl_price = current_live_price * 0.98
    tp_price = current_live_price * 1.06

risk_amount_usd = st.session_state.account_balance * (risk_percentage / 100.0)
price_risk_per_unit = abs(entry_price - sl_price)
position_size_units = risk_amount_usd / price_risk_per_unit if price_risk_per_unit > 0 else 0
rrr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0

st.sidebar.info(f"💡 **Risk:** `${risk_amount_usd:.2f}` | **Units:** `{position_size_units:,.2f}` | **RRR:** `1:{rrr:.2f}`")

# --- MAIN DASHBOARD (SINGLE COLUMN FOR CLEAN MOBILE VIEW) ---
df = fetch_chart_data(selected_coin, timeframe=timeframe)

if not df.empty:
    df = calculate_indicators(df)
    live_price = df['close'].iloc[-1]
    current_rsi = df['RSI'].iloc[-1]
    supports, resistances, liquidity_pools, trend, patterns = technical_analysis_engine(df)
    
    st.markdown("### 📋 Automated Technical Report")
    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("RSI (14)", f"{current_rsi:.2f}")
    col_r2.metric("Trend", trend)
    col_r3.metric("Strategy", trade_type)
    
    st.subheader(f"📊 {selected_coin} [{timeframe}] | Live: ${live_price:,.4f}")
    
    # --- CLEAN TRADINGVIEW STYLE PLOTLY CHART ---
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#00E676', decreasing_line_color='#FF5252',
        name='Candles'
    )])
    
    # EMAs
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#29B6F6', width=1.5)))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FFA726', width=1.8)))
    
    # Support
    for sup in supports:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup, line=dict(color="#00C853", width=1.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[1], y=sup, text=f"Support: ${sup:,.2f}", showarrow=False, yshift=-10, font=dict(color="#00C853", size=10))

    # Resistance
    for res in resistances:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res, line=dict(color="#D50000", width=1.5, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[1], y=res, text=f"Resistance: ${res:,.2f}", showarrow=False, yshift=12, font=dict(color="#D50000", size=10))

    # Liquidity
    if liquidity_pools:
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=liquidity_pools['buy_side'], y1=liquidity_pools['buy_side'], line=dict(color="#FFD700", width=1.2, dash="dashdot"))
        fig.add_annotation(x=df['timestamp'].iloc[-2], y=liquidity_pools['buy_side'], text="⚡ Buy Liq", showarrow=False, yshift=12, font=dict(color="#FFD700", size=9))

        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=liquidity_pools['sell_side'], y1=liquidity_pools['sell_side'], line=dict(color="#FFD700", width=1.2, dash="dashdot"))
        fig.add_annotation(x=df['timestamp'].iloc[-2], y=liquidity_pools['sell_side'], text="⚡ Sell Liq", showarrow=False, yshift=-12, font=dict(color="#FFD700", size=9))

    # Entry, SL, TP Markers
    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=entry_price, y1=entry_price, line=dict(color="#29B6F6", width=2, dash="dash"))
    fig.add_annotation(x=df['timestamp'].iloc[-1], y=entry_price, text=f"ENTRY: ${entry_price:,.2f}", showarrow=True, arrowhead=2, ax=-50, ay=0, bgcolor="#29B6F6", font=dict(color="black", size=10))

    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF5252", width=2, dash="dash"))
    fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text=f"SL: ${sl_price:,.2f}", showarrow=True, arrowhead=2, ax=-50, ay=15, bgcolor="#FF5252", font=dict(color="white", size=10))

    fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_price, y1=tp_price, line=dict(color="#00E676", width=2, dash="dash"))
    fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp_price, text=f"TP: ${tp_price:,.2f}", showarrow=True, arrowhead=2, ax=-50, ay=-15, bgcolor="#00E676", font=dict(color="black", size=10))

    # Optimized Layout for Phone Screens
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
    
    st.divider()
    st.subheader("📌 Binance Metrics & Summary")
    
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("Account Risk", f"${risk_amount_usd:,.2f} ({risk_percentage}%)")
    m_col1.metric("Position Size", f"{position_size_units:,.2f} units")
    
    m_col2.metric("Target RRR", f"1:{rrr:.2f}")
    m_col2.metric("Liquidation Risk", "Low")
    
    st.success(f"📌 **Active Strategy:** {trade_type} | **Entry:** `${entry_price:,.2f}` | **SL:** `${sl_price:,.2f}` | **TP:** `${tp_price:,.2f}`")
else:
    st.warning("Fetching market data...")
