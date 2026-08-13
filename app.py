# Gather all Fvgs separately
    bullish_fvgs = []
    bearish_fvgs = []
    
    for i in range(1, len(df) - 1):
        if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            bullish_fvgs.append({
                'type': 'Bullish FVG', 
                'low': df['high'].iloc[i-1], 
                'high': df['low'].iloc[i+1], 
                'time': df['timestamp'].iloc[i]
            })
        elif df['high'].iloc[i+1] < df['low'].iloc[i-1]:
            bearish_fvgs.append({
                'type': 'Bearish FVG', 
                'low': df['high'].iloc[i+1], 
                'high': df['low'].iloc[i-1], 
                'time': df['timestamp'].iloc[i]
            })
            
    # Determine Trend based on EMA 50 & Price
    current_price = closes[-1]
    current_ema50 = df['EMA_50'].iloc[-1]
    
    # Strict filtering: Show ONLY Bullish FVG if in uptrend, ONLY Bearish FVG if in downtrend
    selected_fvg = []
    if current_price >= current_ema50 and bullish_fvgs:
        selected_fvg = [bullish_fvgs[-1]] # Only the latest Bullish FVG
    elif current_price < current_ema50 and bearish_fvgs:
        selected_fvg = [bearish_fvgs[-1]] # Only the latest Bearish FVG
    else:
        # Fallback to the absolute latest single one if conditions overlap
        all_fvgs = bullish_fvgs + bearish_fvgs
        if all_fvgs:
            selected_fvg = [all_fvgs[-1]]
