from collections import deque

live_center_spot = 0  # this will hold the rounded spot price
live_strike_range = 15      
live_contract_step = 50
live_gex_history = deque(maxlen=15)
trending_history = deque(maxlen=100)  # keep up to last 100 intervals