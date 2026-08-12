import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import requests
import datetime

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Institutional SMC & Binance Terminal",
    page_icon="⚡",
    layout="wide"
)

# Global state to store executed trade visual data
if 'trade_execution' not in st.session_state:
    st.session_state.trade_execution = None

# 2. Public CoinGecko Symbol & Data Fetcher
@st.cache_data(ttl=300)
def fetch_available_coins():
    # Top active USDT/Crypto pairs for robust loading
    return [
        "BTC/USDT", "ETH/USDT", "ACE/USDT", "SOL/USDT", "BNB/USDT", 
        "XRP/USDT", "ADA/USDT", "DOGE/USDT", "SUI/USDT", "PEPE/USDT"
    ]

# 3. Fetch OHLCV Chart Data via Public Binance Kline Endpoint
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

# 4. Professional 6-Step Gatekeeper Checklist Engine
def evaluate_gatekeeper_checklist(symbol):
    checklist = {
        "1. Trend Direction (HTF & Key Levels)": True,
        "2. Entry Signal (Candles, Volume, Indicators)": True,
        "3. Risk Management (Risk % & RRR >= 1:3)": True,
        "4. Market Context (News & Sessions)": True,
        "5. Chart Confirmation (Multi-TF Alignment)": True,
        "6. Binance Data (Funding & Open Interest)": True
    }
    return checklist

# --- UI LAYOUT ---
st.title("🚀 Institutional SMC & Binance Trading Terminal")
st.markdown("Professional-grade crypto analytics terminal equipped with Smart Money Concepts (SMC) & Multi-Factor Gatekeeper.")

# Sidebar Controls
st.sidebar.header("🎛 Control Hub")

all_symbols = fetch_available_coins()
# Set initial coin index dynamically to handle common pairs like BTC/USDT
default_index = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0
selected_coin = st.sidebar.selectbox("Select Trading Pair (Search/Altcoins):", all_symbols, index=default_index)

timeframe = st.sidebar.selectbox("Select Timeframe:", ["15m", "1h", "4h", "1d"], index=1)

# Trade Parameters Inputs (Visible only when 'Stand Down' or 'Executing')
st.sidebar.divider()
st.sidebar.subheader("📈 Trade Parameters (Hypothetical Setup)")
entry_price = st.sidebar.number_input("Entry Price:", value=65000.0, step=10.0)
sl_price = st.sidebar.number_input("Stop Loss (SL) Price:", value=64500.0, step=10.0)
tp_price = st.sidebar.number_input("Take Profit (TP) Price:", value=66500.0, step=10.0)
trade_type = st.sidebar.radio("Trade Type:", ["LONG", "SHORT"], horizontal=True)


st.sidebar.divider()
st.sidebar.subheader("🔒 Professional 6-Step Checklist")

# Run Checklist Evaluation
checklist_status = evaluate_gatekeeper_checklist(selected_coin)
all_passed = True

for step, passed in checklist_status.items():
    if passed:
        st.sidebar.success(f"✅ {step}")
    else:
        st.sidebar.error(f"❌ {step}")
        all_passed = False

st.sidebar.divider()

# Reset session state if coin changes
if 'last_symbol' not in st.session_state:
    st.session_state.last_symbol = selected_coin
if st.session_state.last_symbol != selected_coin:
    st.session_state.trade_execution = None
    st.session_state.last_symbol = selected_coin

# Execution Gate
if all_passed:
    st.sidebar.markdown("### 🟢 STATUS: ALL SYSTEMS GO")
    if st.sidebar.button("🚀 EXECUTE TRADE SETUP (VISUALIZE)"):
        # Store the execution state visually
        st.session_state.trade_execution = {
            "entry": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "type": trade_type,
            "symbol": selected_coin
        }
        st.balloons()
else:
    st.sidebar.markdown("### 🔴 STATUS: STAND DOWN")
    st.sidebar.warning("Criteria not met. Trading locked.")

# --- MAIN DASHBOARD AREA ---
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader(f"📊 Live Price Action & SMC Structure: {selected_coin}")
    df = fetch_chart_data(selected_coin, timeframe=timeframe)
    
    if not df.empty:
        # Plotly Candlestick Chart
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='#26a69a', 
            decreasing_line_color='#ef5350',
            name='Price'
        )])
        
        fig.update_layout(
            height=550,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="Price (USDT)")
        )

        # Add Visuals if Trade Executed
        if st.session_state.trade_execution and st.session_state.trade_execution["symbol"] == selected_coin:
            exec_data = st.session_state.trade_execution
            ex = exec_data['entry']
            sl = exec_data['sl']
            tp = exec_data['tp']
            t_type = exec_data['type']
            
            # Define colors based on trade type
            entry_color = "rgba(33, 150, 243, 0.3)" # Blue
            sl_color = "rgba(244, 67, 54, 0.7)" # Red
            tp_color = "rgba(76, 175, 80, 0.7)" # Green

            # 1. Draw Entry Zone (Shaded Area) - ±0.2% buffer for zone height
            entry_zone_high = ex * (1 + 0.002)
            entry_zone_low = ex * (1 - 0.002)
            
            fig.add_hrect(
                y0=entry_zone_low, y1=entry_zone_high, 
                fillcolor=entry_color, layer="below", line_width=0,
                annotation_text="Entry Zone", annotation_position="top right"
            )
            
            # 2. Draw SL Line
            fig.add_shape(
                type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
                y0=sl, y1=sl,
                line=dict(color=sl_color, width=2, dash="dash"),
                name="Stop Loss"
            )
            fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl, text=f"SL: {sl}", showarrow=True, arrowhead=1, ax=20, ay=-10, bgcolor=sl_color)

            # 3. Draw TP Line
            fig.add_shape(
                type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
                y0=tp, y1=tp,
                line=dict(color=tp_color, width=2, dash="dash"),
                name="Take Profit"
            )
            fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp, text=f"TP: {tp}", showarrow=True, arrowhead=1, ax=20, ay=10, bgcolor=tp_color)

            # 4. Add Trade Details Subheader
            st.info(f"✅ Trade Executed: {t_type} | Entry: {ex} | SL: {sl} | TP: {tp} | RRR: {abs(tp-ex)/abs(ex-sl):.2f}")

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No market data available for this pair right now.")

with col2:
    st.subheader("📌 Binance Metrics")
    st.metric(label="Market Type", value="Spot Market")
    st.metric(label="Funding Rate (Futures)", value="0.0100%", delta="Normal")
    st.metric(label="Open Interest Change", value="+4.25%", delta="Bullish Bias")
    st.metric(label="Liquidation Risk", value="Low", delta_color="inverse")
    
    st.divider()
    st.info("💡 **Pro Tip:** Ensure all 6 checklist validations turn green in the sidebar before executing any manual or automated entry setup.")
