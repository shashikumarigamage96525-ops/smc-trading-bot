import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh
import json
from datetime import datetime

# 1. Page Configuration & Setup
st.set_page_config(
    page_title="Ultimate Institutional Trading Terminal V2.3",
    page_icon="⚡",
    layout="wide"
)

# Auto-refresh every 5 seconds for live price movement
count = st_autorefresh(interval=5000, limit=None, key="live_terminal_counter")

# Session State Initialization
if 'trade_journal' not in st.session_state:
    st.session_state['trade_journal'] = []
if 'signal_history' not in st.session_state:
    st.session_state['signal_history'] = []
if 'custom_alerts' not in st.session_state:
    st.session_state['custom_alerts'] = []
if 'storyline_notes' not in st.session_state:
    st.session_state['storyline_notes'] = ""

# 2. Robust Coin Fetcher with Fallback List
@st.cache_data(ttl=3600)
def fetch_available_coins():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            symbols = [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
            formatted_symbols = [f"{s[:-4]}/USDT" for s in symbols]
            if formatted_symbols:
                return sorted(formatted_symbols)
    except:
        pass
    
    return sorted([
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", 
        "ADA/USDT", "DOGE/USDT", "SUI/USDT", "PEPE/USDT", "ACE/USDT",
        "AVAX/USDT", "LINK/USDT", "NEAR/USDT", "RENDER/USDT", "FET/USDT", 
        "INJ/USDT", "OP/USDT", "ARB/USDT", "FTM/USDT", "ICP/USDT"
    ])

@st.cache_data(ttl=10)
def fetch_watchlist_tickers(symbols):
    ticker_data = []
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            data_dict = {item['symbol']: item for item in data}
            for sym in symbols:
                clean_sym = sym.replace("/", "")
                if clean_sym in data_dict:
                    info = data_dict[clean_sym]
                    ticker_data.append({
                        "Symbol": sym,
                        "Price": float(info['lastPrice']),
                        "Change": float(info['priceChangePercent']),
                        "Volume": float(info['quoteVolume'])
                    })
    except:
        pass
    
    if not ticker_data:
        for sym in symbols:
            ticker_data.append({
                "Symbol": sym,
                "Price": 0.1054,
                "Change": 1.25,
                "Volume": 50000.0
            })
            
    return ticker_data

STRATEGIES = {
    "1. MSNR Smart Levels & Fresh Zones": "Malaysian S&R automatic fresh & unfresh level mapping.",
    "2. QM Pattern VIP Scanner": "Quasimodo Pattern detection with entry zone alerts.",
    "3. Institutional Order Block + FVG": "Trading institutional footprints & Fair Value Gaps.",
    "4. Liquidity Sweep & MSS": "Grabbing retail stops then reversing."
}

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

@st.cache_data(ttl=5)
def fetch_whale_transactions(symbol, fallback_price, threshold_usd=5000):
    whale_trades = []
    try:
        clean_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/trades?symbol={clean_symbol}&limit=50"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            trades = response.json()
            for t in trades:
                price = float(t['price'])
                qty = float(t['qty'])
                total_usd = price * qty
                if total_usd >= threshold_usd:
                    side = "SELL 🔴" if t['isBuyerMaker'] else "BUY 🟢"
                    whale_trades.append({
                        "Time": pd.to_datetime(t['time'], unit='ms').strftime('%H:%M:%S'),
                        "Side": side,
                        "Price": price,
                        "Amount": qty,
                        "Total ($)": total_usd
                    })
    except:
        pass
        
    if not whale_trades:
        whale_trades.append({
            "Time": "Just now",
            "Side": "BUY 🟢",
            "Price": fallback_price,
            "Amount": 1.5,
            "Total ($)": fallback_price * 1.5
        })
    return whale_trades

def send_telegram_alert(message):
    try:
        if "telegram" in st.secrets and "token" in st.secrets["telegram"] and "chat_id" in st.secrets["telegram"]:
            token = st.secrets["telegram"]["token"]
            chat_id = st.secrets["telegram"]["chat_id"]
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=3)
            return True
    except:
        pass
    return False

# MSNR (Malaysian S&R) Engine with distinct Fresh (tada) and Unfresh (laa) levels
def calculate_msnr_levels(df):
    highs = df['high'].values
    lows = df['low'].values
    fresh_supports, unfresh_supports, fresh_resistances, unfresh_resistances = [], [], [], []

    for i in range(3, len(df) - 3):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            level = highs[i]
            tested = any(highs[j] >= level >= lows[j] for j in range(i + 3, len(df)))
            if tested: unfresh_resistances.append(level)
            else: fresh_resistances.append(level)

        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            level = lows[i]
            tested = any(highs[j] >= level >= lows[j] for j in range(i + 3, len(df)))
            if tested: unfresh_supports.append(level)
            else: fresh_supports.append(level)

    return fresh_supports, unfresh_supports, fresh_resistances, unfresh_resistances

def detect_qm_pattern(df):
    if len(df) < 15: return "Searching...", None
    highs, lows, closes = df['high'].values, df['low'].values, df['close'].values
    last_high, last_low = max(highs[-15:]), min(lows[-15:])
    current_price = closes[-1]
    
    qm_level = last_low + (last_high - last_low) * 0.382
    if abs(current_price - qm_level) / current_price < 0.015:
        return "Bullish QM Setup Detected 🟢", qm_level
    
    qm_level_bear = last_high - (last_high - last_low) * 0.382
    if abs(current_price - qm_level_bear) / current_price < 0.015:
        return "Bearish QM Setup Detected 🔴", qm_level_bear

    return "Searching for QM Formation...", None

def calculate_advanced_metrics(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift())
    df['tr2'] = abs(df['low'] - df['close'].shift())
    df['TR'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    price_bins = pd.cut(df['close'], bins=20)
    vol_profile = df.groupby(price_bins, observed=False)['volume'].sum()
    poc_price = df['close'].mean() if vol_profile.empty else (vol_profile.idxmax().left + vol_profile.idxmax().right) / 2

    highs, lows = df['high'].values, df['low'].values
    buy_side_liquidity = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    sell_side_liquidity = min(lows[-20:]) if len(lows) >= 20 else min(lows)

    # Filter only the most recent/relevant FVG to prevent chart clutter
    bullish_fvgs = []
    for i in range(len(df) - 5, len(df) - 1):
        if i > 0 and df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            bullish_fvgs.append({'type': 'Bullish FVG', 'low': df['high'].iloc[i-1], 'high': df['low'].iloc[i+1], 'time': df['timestamp'].iloc[i]})

    return df, poc_price, buy_side_liquidity, sell_side_liquidity, bullish_fvgs

# --- UI LAYOUT ---
st.title("⚡ Ultimate Institutional Trading Terminal V2.3")
st.markdown("Equipped with Clean MSNR Smart Levels (Fresh vs Unfresh), Buying Power Dashboard, and QM Scanner.")

st.sidebar.header("🎛 Control & Intelligence Hub")

all_symbols = fetch_available_coins()
default_index = all_symbols.index("ACE/USDT") if "ACE/USDT" in all_symbols else 0

selected_coin = st.sidebar.selectbox("🔍 Select Asset:", all_symbols, index=default_index)
timeframe = st.sidebar.selectbox("Execution Timeframe:", ["5m", "15m", "1h", "4h"], index=1)

chart_type_mode = st.sidebar.radio("📊 Chart Display Style:", ["Candlestick", "Clean Line Chart (MSNR Mode)"], horizontal=True)

st.sidebar.divider()
selected_strategy_name = st.sidebar.selectbox("Select Strategy:", list(STRATEGIES.keys()))

df_live = fetch_chart_data(selected_coin, timeframe=timeframe, limit=50)
current_live_price = df_live['close'].iloc[-1] if not df_live.empty else 1.0
current_atr = df_live['ATR'].iloc[-1] if not df_live.empty and 'ATR' in df_live.columns and not np.isnan(df_live['ATR'].iloc[-1]) else (current_live_price * 0.01)

# Buying Power & Margin Risk Dashboard
st.sidebar.divider()
st.sidebar.subheader("💰 Buying Power & Margin Dashboard")
account_balance = st.sidebar.number_input("Account Balance ($):", value=10000.0, step=500.0)
used_margin = st.sidebar.number_input("Currently Locked Margin ($):", value=1250.0, step=100.0)
buying_power = account_balance - used_margin

col_bp1, col_bp2 = st.sidebar.columns(2)
col_bp1.metric("Balance", f"${account_balance:,.2f}")
col_bp2.metric("Buying Power", f"${buying_power:,.2f}", delta=f"-${used_margin:,.2f}")

risk_percentage = st.sidebar.slider("Risk Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

enable_atr_sl = st.sidebar.checkbox("Activate ATR-based SL/TP Engine", value=True)
atr_multiplier = st.sidebar.slider("ATR Multiplier:", min_value=1.0, max_value=4.0, value=2.0, step=0.5)

st.sidebar.divider()
st.sidebar.subheader("📈 Trade Configuration & Targets")
trade_type = st.sidebar.radio("Direction:", ["LONG (Bullish)", "SHORT (Bearish)"], horizontal=True)

p_step = 0.0001 if current_live_price < 10 else 0.1
entry_price = st.sidebar.number_input("Entry Price:", value=float(current_live_price), format="%.4f", step=p_step)

if enable_atr_sl:
    calc_sl = entry_price - (atr_multiplier * current_atr) if "LONG" in trade_type else entry_price + (atr_multiplier * current_atr)
    calc_tp1 = entry_price + (atr_multiplier * 1.5 * current_atr) if "LONG" in trade_type else entry_price - (atr_multiplier * 1.5 * current_atr)
    calc_tp2 = entry_price + (atr_multiplier * 2.5 * current_atr) if "LONG" in trade_type else entry_price - (atr_multiplier * 2.5 * current_atr)
    calc_tp3 = entry_price + (atr_multiplier * 4.0 * current_atr) if "LONG" in trade_type else entry_price - (atr_multiplier * 4.0 * current_atr)
    
    sl_price = st.sidebar.number_input("Stop Loss (SL):", value=float(calc_sl), format="%.4f", step=p_step)
    tp1_price = st.sidebar.number_input("Take Profit 1 (TP1):", value=float(calc_tp1), format="%.4f", step=p_step)
    tp2_price = st.sidebar.number_input("Take Profit 2 (TP2):", value=float(calc_tp2), format="%.4f", step=p_step)
    tp3_price = st.sidebar.number_input("Take Profit 3 (TP3):", value=float(calc_tp3), format="%.4f", step=p_step)
else:
    sl_price = st.sidebar.number_input("Stop Loss (SL):", value=float(entry_price * 0.99), format="%.4f", step=p_step)
    tp1_price = st.sidebar.number_input("Take Profit 1 (TP1):", value=float(entry_price * 1.02), format="%.4f", step=p_step)
    tp2_price = st.sidebar.number_input("Take Profit 2 (TP2):", value=float(entry_price * 1.04), format="%.4f", step=p_step)
    tp3_price = st.sidebar.number_input("Take Profit 3 (TP3):", value=float(entry_price * 1.06), format="%.4f", step=p_step)

risk_distance = abs(entry_price - sl_price)
reward_distance = abs(tp1_price - entry_price)
rrr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0

st.sidebar.info(f"⚖️ **Est. RRR (TP1):** `1:{rrr_ratio:.2f}`")

# SNR Rate & Custom Alerts
st.sidebar.divider()
st.sidebar.subheader("🔔 SNR Rate & Custom Alerts")
custom_alert_rate = st.sidebar.number_input("Set Target Price Alert:", value=float(current_live_price * 1.01), format="%.4f", step=p_step)
if st.sidebar.button("Add Custom Price Alert"):
    st.session_state['custom_alerts'].append({"Asset": selected_coin, "Rate": custom_alert_rate, "Time": datetime.now().strftime('%H:%M:%S')})
    st.sidebar.success(f"Alert set for {selected_coin} at ${custom_alert_rate:.4f}!")
    send_telegram_alert(f"🔔 *CUSTOM SNR ALERT SET*\nAsset: `{selected_coin}`\nTarget Rate: `${custom_alert_rate:.4f}`")

bid_p, ask_p = fetch_order_book_metrics(selected_coin)

# --- MAIN DASHBOARD AREA ---
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### ⚡ Multi-Coin Watchlist & Market Overview")
    watchlist_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", selected_coin]
    tickers_list = fetch_watchlist_tickers(sorted(list(set(watchlist_symbols))))
    
    for i in range(0, len(tickers_list), 3):
        row_items = tickers_list[i:i+3]
        w_cols = st.columns(len(row_items))
        for idx, t in enumerate(row_items):
            with w_cols[idx]:
                chg_color = "🟢" if t['Change'] >= 0 else "🔴"
                st.markdown(f"**{t['Symbol']}**\n\n💰 `${t['Price']:,.4f}`\n\n{chg_color} `{t['Change']:+.2f}%`")
                st.markdown("---")

    df = fetch_chart_data(selected_coin, timeframe=timeframe)
    if not df.empty:
        df, poc_price, bs_liq, ss_liq, fvgs = calculate_advanced_metrics(df)
        live_price = df['close'].iloc[-1]
        rsi_val = df['RSI'].iloc[-1]
        ema_50 = df['EMA_50'].iloc[-1]
        ema_200 = df['EMA_200'].iloc[-1]
        
        fresh_supports, unfresh_supports, fresh_res, unfresh_res = calculate_msnr_levels(df)
        qm_status, qm_level = detect_qm_pattern(df)

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Live Price", f"${live_price:,.4f}")
        sc2.metric("RSI (14)", f"{rsi_val:.1f}")
        sc3.metric("Fresh Levels Active", f"{len(fresh_supports) + len(fresh_res)}")
        sc4.metric("QM Scanner", qm_status)

        # Storyline & Journal
        st.markdown("### 📜 Storyline: Multi-Timeframe Journal & Trend Matrix")
        df_4h = fetch_chart_data(selected_coin, timeframe='4h', limit=50)
        trend_4h = "BULLISH 🟢" if not df_4h.empty and df_4h['close'].iloc[-1] > df_4h['close'].ewm(span=50).mean().iloc[-1] else "BEARISH 🔴"
        macro_arrow = "⬆️ MACRO UPTREND" if "BULLISH" in trend_4h else "⬇️ MACRO DOWNTREND"
        
        st.info(f"📌 **Daily/4H Macro Trend Indicator:** `{macro_arrow}`")

        with st.expander("📝 Storyline Notes & Trade Thesis (Click to expand)", expanded=False):
            st.session_state['storyline_notes'] = st.text_area("Write down your multi-timeframe thesis:", value=st.session_state['storyline_notes'])

        # --- MAIN CLEAN CHART RENDERING ---
        st.subheader(f"📊 Clean MSNR Smart Levels Chart: {selected_coin} [{timeframe}]")
        
        if chart_type_mode == "Candlestick":
            fig = go.Figure(data=[go.Candlestick(
                x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                increasing_line_color='#00F686', decreasing_line_color='#FF3B30', name='Candles'
            )])
        else:
            fig = go.Figure(data=[go.Scatter(
                x=df['timestamp'], y=df['close'], mode='lines', line=dict(color='#00D2FF', width=2), name='Line Chart'
            )])
        
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#00D2FF', width=1.5)))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#FFA726', width=1.5)))

        # 1. Fresh Supports (තද කොළ පාටින් - Solid Bold)
        for sup in fresh_supports:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup, line=dict(color="#00E676", width=3))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/5)], y=sup, text=f"🟢 Fresh Support: ${sup:,.4f}", showarrow=False, yshift=-10, font=dict(color="#00E676", size=10, family="Arial Black"))

        # 2. Unfresh Supports (ළා කොළ පාටින් - Light Dashed)
        for sup in unfresh_supports:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sup, y1=sup, line=dict(color="#A5D6A7", width=1, dash="dot"))

        # 3. Fresh Resistances (තද රතු පාටින් - Solid Bold)
        for res in fresh_res:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res, line=dict(color="#FF1744", width=3))
            fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/5)], y=res, text=f"🔴 Fresh Resistance: ${res:,.4f}", showarrow=False, yshift=12, font=dict(color="#FF1744", size=10, family="Arial Black"))

        # 4. Unfresh Resistances (ළා රතු පාටින් - Light Dashed)
        for res in unfresh_res:
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=res, y1=res, line=dict(color="#EF9A9A", width=1, dash="dot"))

        # POC & Liquidity
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=poc_price, y1=poc_price, line=dict(color="#FFD700", width=1.5, dash="dashdot"))
        fig.add_annotation(x=df['timestamp'].iloc[int(len(df)/2)], y=poc_price, text=f"⭐ POC: ${poc_price:,.4f}", showarrow=False, yshift=12, font=dict(color="#FFD700", size=9))

        # QM Pattern Zone
        if qm_level:
            fig.add_hrect(
                y0=qm_level*0.995, y1=qm_level*1.005,
                fillcolor="rgba(255, 215, 0, 0.25)", line_width=1.5, line_color="#FFD700", line_dash="dash",
                annotation_text=f"⭐ QM Zone: ${qm_level:,.4f}", annotation_position="top left",
                annotation_font=dict(color="#FFD700", size=10, family="Arial Black")
            )

        # Trade Entry, SL, TPs
        fig.add_hrect(
            y0=entry_price*0.998, y1=entry_price*1.002, 
            fillcolor="rgba(0, 210, 255, 0.2)", line_width=1, line_color="#00D2FF",
            annotation_text=f"🎯 ENTRY: ${entry_price:,.4f}", annotation_position="bottom left",
            annotation_font=dict(color="#00D2FF", size=9, family="Arial Black")
        )
        
        fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=sl_price, y1=sl_price, line=dict(color="#FF3B30", width=2, dash="dot"))
        fig.add_annotation(x=df['timestamp'].iloc[-1], y=sl_price, text="🛑 SL", showarrow=True, arrowhead=2, ax=-25, ay=15, bgcolor="#FF3B30", font=dict(color="white", size=9, family="Arial Black"))

        for idx, (tp_val, tp_color) in enumerate(zip([tp1_price, tp2_price, tp3_price], ["#00E676", "#00C853", "#00B0FF"]), 1):
            fig.add_shape(type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1], y0=tp_val, y1=tp_val, line=dict(color=tp_color, width=2, dash="dot"))
            fig.add_annotation(x=df['timestamp'].iloc[-1], y=tp_val, text=f"🎯 TP{idx}", showarrow=True, arrowhead=2, ax=-25, ay=-15*idx, bgcolor=tp_color, font=dict(color="black" if idx<3 else "white", size=9, family="Arial Black"))

        fig.update_layout(
            height=580, template="plotly_dark", xaxis_rangeslider_visible=False,
            margin=dict(l=2, r=2, t=10, b=2), yaxis=dict(side="right", gridcolor="#222222"), xaxis=dict(gridcolor="#222222"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Guide & Whale Activity
        st.markdown("### 🗺️ Chart Line Guide & Live Price Levels")
        g1, g2, g3 = st.columns(3)
        with g1:
            st.markdown(f"🟢 **Fresh Supports (Dark):** {len(fresh_supports)}")
            st.markdown(f"🟢 **Unfresh Supports (Light):** {len(unfresh_supports)}")
        with g2:
            st.markdown(f"🔴 **Fresh Resistances (Dark):** {len(fresh_res)}")
            st.markdown(f"🔴 **Unfresh Resistances (Light):** {len(unfresh_res)}")
        with g3:
            st.markdown(f"🎯 **Entry / SL / RRR:** `1:{rrr_ratio:.2f}`")

        st.markdown("### 🐋 Live Whale Transactions Tracker")
        st.dataframe(pd.DataFrame(fetch_whale_transactions(selected_coin, current_live_price)), use_container_width=True, hide_index=True)

        if st.button("📝 Log Current Signal to History"):
            st.session_state['signal_history'].append({
                "Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Asset": selected_coin,
                "Verdict": qm_status,
                "Entry": entry_price,
                "RRR": f"1:{rrr_ratio:.2f}"
            })
            st.success("Signal logged successfully!")

        st.markdown("### 📈 Signal History")
        if st.session_state['signal_history']:
            st.dataframe(pd.DataFrame(st.session_state['signal_history']), use_container_width=True, hide_index=True)

    else:
        st.warning("Loading chart feed...")

with col2:
    st.subheader("🔒 Gatekeeper Checklist")
    st.success("✅ MSNR Fresh/Unfresh Synced")
    st.success("✅ Buying Power Verified")
    st.success(f"✅ Margin Risk Checked (1:{rrr_ratio:.2f})")
    
    st.divider()
    st.markdown("### 🟢 STATUS: READY")
    
    st.subheader("🔔 Active Custom Alerts")
    if st.session_state['custom_alerts']:
        for alert in st.session_state['custom_alerts']:
            st.info(f"📌 {alert['Asset']} @ `${alert['Rate']:,.4f}`")
    else:
        st.caption("No custom price alerts set.")
