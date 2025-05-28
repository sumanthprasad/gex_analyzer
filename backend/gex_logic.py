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
        out_df[col] = (
            out_df[col].astype(str)
                        .str.replace(',', '', regex=True)
                        .str.strip()
        )
        out_df[col] = pd.to_numeric(out_df[col], errors="coerce").fillna(0)

    out_df.sort_values("Strike Price", inplace=True)
    out_df.reset_index(drop=True, inplace=True)
    return out_df

def filter_strikes_around_spot(df, spot_price, n=12):
    below = df[df["Strike Price"] < spot_price].tail(n)
    above = df[df["Strike Price"] > spot_price].head(n)
    selected = pd.concat([below, above])
    if selected.empty:
        raise ValueError("No strikes found around the specified spot.")
    return selected

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

def process_all(df, spot, strikes, contract_size, vol, expiry, column_mode):
    df.columns = df.columns.str.strip()
    df = df.replace({',': ''}, regex=True)
    auto_rename_put_columns(df)

    if column_mode == "keyword":
        df_left, df_right, strike_series, call_idx, put_idx = detect_columns_keyword_based(df)
        df_cp = build_call_put_dataframe(df_left, df_right, strike_series, call_idx, put_idx)
    else:
        raise NotImplementedError("Only 'keyword' column detection supported.")

    df_sel = filter_strikes_around_spot(df_cp, spot, n=strikes)
    df_calc = compute_metrics(df_sel, spot, contract_size, vol, expiry)
    calls_df, puts_df = separate_calls_puts(df_calc)
    merged, zero_gamma_level = calculate_zero_gamma_level(calls_df, puts_df)
    c_sum, p_sum = summarize(calls_df, puts_df)
    total_net_gamma = merged["Net GEX 1pct"].sum()

    avg_vtr_calls = calls_df["VegaTheta_Ratio"].mean()
    avg_vtr_puts = puts_df["VegaTheta_Ratio"].mean()
    diff = avg_vtr_calls - avg_vtr_puts
    tol, high = 0.15, 0.3
    sentiment = (
        "Sideways" if abs(diff) < tol else
        "Bullish" if diff >= high else
        "Mildly Bullish" if diff >= tol else
        "Bearish" if diff <= -high else
        "Mildly Bearish" if diff <= -tol else "Neutral"
    )

    return {
        "net_gex_1pct": merged[["Strike Price", "Net GEX 1pct"]].rename(columns={"Strike Price": "strike", "Net GEX 1pct": "value"}).to_dict(orient="records"),
        "dealer_delta": df_calc[["Strike Price", "Dealer Delta Exposure"]].rename(columns={"Dealer Delta Exposure": "value"}).to_dict(orient="records"),
        "dealer_vanna": df_calc[["Strike Price", "Dealer Vanna Exposure"]].rename(columns={"Dealer Vanna Exposure": "value"}).to_dict(orient="records"),
        "gex": df_calc[["Strike Price", "GEX"]].rename(columns={"GEX": "value"}).to_dict(orient="records"),
        "cumulative_gex": df_calc[["Strike Price", "Cumulative GEX"]].rename(columns={"Cumulative GEX": "value"}).to_dict(orient="records"),
        "vega_theta_ratio": df_calc[["Strike Price", "VegaTheta_Ratio"]].rename(columns={"VegaTheta_Ratio": "value"}).to_dict(orient="records"),
        "summary_text": (
            f"Calls GEX: {c_sum['GEX']:.2e}\n"
            f"Puts GEX: {p_sum['GEX']:.2e}\n"
            f"Zero Gamma Level: {f'{zero_gamma_level:.2f}' if zero_gamma_level is not None else 'N/A'}\n"
            f"Net GEX (scaled 1e11): {total_net_gamma / 1e11:.2f}\n"
            f"Sentiment: {sentiment}"
        ),

        "sentiment": sentiment
    }
