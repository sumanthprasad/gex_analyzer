import pandas as pd
import numpy as np

def auto_rename_put_columns(df, strike_col="Strike Price"):
    if strike_col not in df.columns:
        raise ValueError(f"Column '{strike_col}' not found in the DataFrame.")
    strike_idx = df.columns.get_loc(strike_col)
    right_cols = list(df.columns[strike_idx + 1:])
    new_names = []
    for old_col in right_cols:
        col_lower = old_col.lower().strip()
        if "oi" in col_lower:
            new_names.append("Put OI")
        elif "delta" in col_lower:
            new_names.append("Put Delta")
        elif "gamma" in col_lower:
            new_names.append("Put Gamma")
        elif "theta" in col_lower:
            new_names.append("Put Theta")
        else:
            new_names.append("Put " + old_col)
    rename_map = dict(zip(right_cols, new_names))
    df.rename(columns=rename_map, inplace=True)
    return df

def detect_columns_keyword_based(df, strike_col="Strike Price"):
    if strike_col not in df.columns:
        raise ValueError(f"Column '{strike_col}' not found in the DataFrame.")
    strike_idx = df.columns.get_loc(strike_col)
    df_left = df.iloc[:, :strike_idx]
    df_right = df.iloc[:, strike_idx + 1:]
    strike_series = df[strike_col]

    def find_col(col_list, keywords):
        for i, col in enumerate(col_list):
            if any(k.lower() in str(col).lower() for k in keywords):
                return i
        return -1

    call_idx = {
        "oi": find_col(df_left.columns, ["oi", "open int", "ce oi", "call oi"]),
        "delta": find_col(df_left.columns, ["delta", "ce delta", "call delta"]),
        "gamma": find_col(df_left.columns, ["gamma", "ce gamma", "call gamma"]),
        "theta": find_col(df_left.columns, ["theta", "ce theta", "call theta"]),
    }
    put_idx = {
        "oi": find_col(df_right.columns, ["oi", "put oi", "pe oi"]),
        "delta": find_col(df_right.columns, ["delta", "put delta", "pe delta"]),
        "gamma": find_col(df_right.columns, ["gamma", "put gamma", "pe gamma"]),
        "theta": find_col(df_right.columns, ["theta", "pe theta", "put theta"]),
    }

    if min(call_idx.values()) < 0 or min(put_idx.values()) < 0:
        raise ValueError("Required columns not found via keyword detection.")

    return df_left, df_right, strike_series, call_idx, put_idx

def build_call_put_dataframe(df_left, df_right, strike_series, call_idx, put_idx):
    rows_out = []
    for i in range(len(strike_series)):
        strike_val = strike_series.iloc[i]
        c_oi = df_left.iloc[i, call_idx["oi"]]
        c_delta = df_left.iloc[i, call_idx["delta"]]
        c_gamma = df_left.iloc[i, call_idx["gamma"]]
        c_theta = df_left.iloc[i, call_idx["theta"]]

        p_oi = df_right.iloc[i, put_idx["oi"]]
        p_delta = df_right.iloc[i, put_idx["delta"]]
        p_gamma = df_right.iloc[i, put_idx["gamma"]]
        p_theta = df_right.iloc[i, put_idx["theta"]]

        rows_out.append({
            "Strike Price": strike_val,
            "OI": c_oi, "Delta": c_delta, "Gamma": c_gamma, "Theta": c_theta,
            "OptionType": "C"
        })
        rows_out.append({
            "Strike Price": strike_val,
            "OI": p_oi, "Delta": p_delta, "Gamma": p_gamma, "Theta": p_theta,
            "OptionType": "P"
        })

    out_df = pd.DataFrame(rows_out)
    for col in ["Strike Price", "OI", "Delta", "Gamma", "Theta"]:
        out_df[col] = pd.to_numeric(out_df[col], errors="coerce").fillna(0)

    out_df.sort_values("Strike Price", inplace=True)
    out_df.reset_index(drop=True, inplace=True)
    return out_df

def filter_strikes_around_spot(df, spot_price, n=15, step=50):
    """
    Only include strikes from spot - n*step up to spot + n*step (inclusive),
    stepping by the contract step.
    """
    # Build the exact valid strikes
    valid_strikes = set(range(
        int(spot_price - n * step),
        int(spot_price + (n + 1) * step),
        step
    ))
    # Filter and sort
    filtered = df[df["Strike Price"].isin(valid_strikes)]
    if filtered.empty:
        raise ValueError("No strikes found around the specified spot.")
    return filtered.sort_values("Strike Price").reset_index(drop=True)



def compute_metrics(df, spot_price, contract_size=75, vol=0.2, T=0.25):
    df["d1"] = np.log(spot_price / df["Strike Price"]) + 0.5 * vol ** 2 * T
    df["d1"] = df["d1"] / (vol * np.sqrt(T))
    df["Vega"] = spot_price * np.sqrt(T) * (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * df["d1"] ** 2)
    df["Vanna"] = - df["d1"] * df["Vega"] / (spot_price * vol)

    df["Dealer OI"] = df["OI"] * contract_size
    df["Dealer Delta Exposure"] = df["Dealer OI"] * df["Delta"]
    df["Dealer Vanna Exposure"] = df["Dealer OI"] * df["Vanna"]
    df["GEX"] = df["OI"] * contract_size * df["Gamma"] * (spot_price ** 2)
    df["GEX_1pct"] = df["GEX"] * 0.0201
    df["Cumulative GEX"] = df.groupby("OptionType")["GEX"].cumsum()
    df["Cumulative Dealer Delta"] = df.groupby("OptionType")["Dealer Delta Exposure"].cumsum()
    df["VegaTheta_Ratio"] = np.where(df["Theta"] != 0, df["Vega"] / np.abs(df["Theta"]), np.nan)

    return df

def separate_calls_puts(df):
    return df[df["OptionType"] == "C"], df[df["OptionType"] == "P"]

def calculate_zero_gamma_level(calls_df, puts_df):
    merged = pd.merge(
        calls_df[['Strike Price', 'GEX']],
        puts_df[['Strike Price', 'GEX']],
        on="Strike Price", how="outer", suffixes=('_calls', '_puts')
    ).fillna(0).sort_values("Strike Price")
    merged["Net GEX"] = merged["GEX_calls"] - merged["GEX_puts"]
    merged["Net GEX 1pct"] = merged["Net GEX"] * 0.0201

    zero_gamma_level = None
    for i in range(1, len(merged)):
        if merged["Net GEX"].iloc[i - 1] * merged["Net GEX"].iloc[i] < 0:
            x1, x2 = merged["Strike Price"].iloc[i - 1], merged["Strike Price"].iloc[i]
            y1, y2 = merged["Net GEX"].iloc[i - 1], merged["Net GEX"].iloc[i]
            zero_gamma_level = x1 - y1 * (x2 - x1) / (y2 - y1)
            break
    return merged, zero_gamma_level

def summarize(calls_df, puts_df):
    def agg(df):
        return {
            "GEX": df["GEX"].sum(),
            "Vanna": df["Vanna"].sum(),
            "Dealer Vanna": df["Dealer Vanna Exposure"].sum(),
            "Dealer Delta": df["Dealer Delta Exposure"].sum(),
            "Dealer OI": df["Dealer OI"].sum()
        }
    return agg(calls_df), agg(puts_df)

def compress(df, col):
    return df.groupby("Strike Price")[col].sum().reset_index()

def format_output_series(df_calc, merged, calls_df, puts_df, zero_gamma_level, spot):
    def safe_float(x): return float(x) if pd.notna(x) else 0.0
    def safe_int(x): return int(float(x)) if pd.notna(x) else 0

    def make_series(df, col):
        return [
            {"strike": safe_int(r["Strike Price"]), "value": safe_float(r[col])}
            for _, r in compress(df, col).iterrows()
        ]

    net_gex_1pct = [
        {"strike": safe_int(r["Strike Price"]), "value": safe_float(r["Net GEX 1pct"])}
        for _, r in merged.iterrows()
    ]
    total_net_gamma = sum([d["value"] for d in net_gex_1pct])
    avg_vtr_calls = calls_df["VegaTheta_Ratio"].mean() or 0.0
    avg_vtr_puts = puts_df["VegaTheta_Ratio"].mean() or 0.0
    diff = avg_vtr_calls - avg_vtr_puts
    tol, high = 0.15, 0.3

    sentiment = (
        "Sideways" if abs(diff) < tol else
        "Bullish" if diff >= high else
        "Mildly Bullish" if diff >= tol else
        "Bearish" if diff <= -high else
        "Mildly Bearish" if diff <= -tol else "Neutral"
    )

    summary = (
        f"Calls GEX: {calls_df['GEX'].sum():.2e}\n"
        f"Puts GEX: {puts_df['GEX'].sum():.2e}\n"
        f"Zero Gamma Level: {zero_gamma_level:.2f}\n"
        f"Net GEX (scaled 1e11): {total_net_gamma / 1e11:.2f}\n"
        f"Sentiment: {sentiment}"
    )

    gamma_exposures = (
        df_calc
        .assign(gammaExposure=lambda d: d["Gamma"] * d["OI"])
        .groupby("Strike Price")["gammaExposure"]
        .sum()
        .reset_index()
    )
    # pick strike with max |exposure|
    gamma_wall_strike = int(
        gamma_exposures.iloc[gamma_exposures["gammaExposure"].abs().idxmax()]["Strike Price"]
    )
    return {
        "net_gex_1pct": net_gex_1pct,
        "dealer_delta": make_series(df_calc, "Dealer Delta Exposure"),
        "dealer_vanna": make_series(df_calc, "Dealer Vanna Exposure"),
        "gex": make_series(df_calc, "GEX"),
        "cumulative_gex": make_series(df_calc, "Cumulative GEX"),
        "vega_theta_ratio": make_series(df_calc, "VegaTheta_Ratio"),
        "summary_text": summary,
        "sentiment": sentiment,
        "spot": spot,
        "gamma_wall_strike": gamma_wall_strike,
    }
