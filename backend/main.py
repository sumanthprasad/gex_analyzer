from fastapi import FastAPI, UploadFile, Form, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import io, re, math
from typing import List, Dict, Any
from datetime import datetime
import __main__ as main
import shared_state


from gex_logic import (
    filter_strikes_around_spot,
    compute_metrics,
    separate_calls_puts,
    calculate_zero_gamma_level,
    summarize,
    format_output_series,
)

import globaldata_ws

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

live_expiry_str: str = ""
live_strike_range: int = 5
live_center_spot: int = 0

@app.get("/gfdl/expiry_list")
async def get_expiry_list():
    return ["12JUN2025", "19JUN2025", "26JUN2025"]

@app.get("/raw_ticks")
async def get_raw_ticks():
    return JSONResponse(content=globaldata_ws.live_ticks_cache)

def load_excel_with_strike_detection(content_bytes: bytes) -> pd.DataFrame:
    for skip in range(10):
        df = pd.read_excel(io.BytesIO(content_bytes), engine="openpyxl", skiprows=skip)
        if any("strike" in col.lower() for col in df.columns if isinstance(col, str)):
            return df
    raise ValueError("No 'Strike Price' column found in first 10 rows.")

@app.post("/compute")
async def compute(
    file: UploadFile = Form(...),
    spot: float = Form(...),
    strikes: int = Form(...),
    contractSize: int = Form(...),
    vol: float = Form(...),
    expiry: float = Form(...),
):
    content = await file.read()
    if file.filename.endswith((".xls", ".xlsx")):
        df = load_excel_with_strike_detection(content)
    else:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))

    from gex_logic import process_all
    result = process_all(df, spot, strikes, contractSize, vol, expiry)

    for key in (
        "net_gex_1pct",
        "dealer_delta",
        "dealer_vanna",
        "gex",
        "cumulative_gex",
        "vega_theta_ratio",
    ):
        for entry in result.get(key, []):
            val = entry.get("value", 0.0)
            if not math.isfinite(val):
                entry["value"] = 0.0

    return JSONResponse(content=result)

@app.post("/start_stream")
async def start_stream(req: Request):
    global live_expiry_str, live_strike_range, live_center_spot

    body = await req.json()
    symbol = body.get("symbol")
    expiry = body.get("expiry")
    spot = float(body.get("spot", 0))
    strike_range = int(body.get("strike_range", 5))
    contract_step = int(body.get("contract_step", 50))

    if not symbol or not expiry or expiry.upper() == "UNKNOWN":
        raise HTTPException(status_code=400, detail="Invalid or missing expiry.")

    live_expiry_str = expiry
    shared_state.live_strike_range = strike_range
    shared_state.live_contract_step = contract_step
    live_center_spot = 0  # will be recomputed later from live ticks

    globaldata_ws.clear_live_cache()
    globaldata_ws.start_background_ws_loop(
        symbol=symbol,
        expiry=expiry,
        spot=int(spot),
        strike_range=strike_range,
        contract_step=contract_step,
    )

    return {"status": "WebSocket started", "symbol": symbol, "expiry": expiry}

def parse_option_data(responses: List[dict]) -> pd.DataFrame:
    records: Dict[int, Dict[str, Any]] = {}

    for item in responses:
        instr = item.get("InstrumentIdentifier", "")
        m = re.match(r".*_(CE|PE)_(\d+)$", instr)
        if not m:
            continue
        opt_type, strike_str = m.groups()
        strike = int(strike_str)

        if strike not in records:
            records[strike] = {}

        prefix = "Call" if opt_type == "CE" else "Put"
        records[strike][f"{prefix} OI"] = item.get("OpenInterest", 0)
        records[strike][f"{prefix} Delta"] = item.get("Delta", 0)
        records[strike][f"{prefix} Gamma"] = item.get("Gamma", 0)
        records[strike][f"{prefix} Theta"] = item.get("Theta", 0)

        records[strike]["Strike Price"] = strike
        records[strike]["OptionType"] = opt_type
        records[strike]["OI"] = item.get("OpenInterest", 0)
        records[strike]["Delta"] = item.get("Delta", 0)
        records[strike]["Gamma"] = item.get("Gamma", 0)
        records[strike]["Theta"] = item.get("Theta", 0)
        records[strike]["Vega"] = item.get("Vega", 0)

    rows: List[Dict[str, Any]] = []
    for strike, data in records.items():
        row = {
            "Strike Price": data.get("Strike Price", strike),
            "OptionType": data.get("OptionType", ""),
            "OI": data.get("OI", 0),
            "Delta": data.get("Delta", 0),
            "Gamma": data.get("Gamma", 0),
            "Theta": data.get("Theta", 0),
            "Vega": data.get("Vega", 0),
            "Call OI": data.get("Call OI", 0),
            "Call Delta": data.get("Call Delta", 0),
            "Call Gamma": data.get("Call Gamma", 0),
            "Call Theta": data.get("Call Theta", 0),
            "Put OI": data.get("Put OI", 0),
            "Put Delta": data.get("Put Delta", 0),
            "Put Gamma": data.get("Put Gamma", 0),
            "Put Theta": data.get("Put Theta", 0),
        }
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()

@app.get("/live_data")
async def get_live_option_data():
    raw_list: List[Dict[str, Any]] = globaldata_ws.live_ticks_cache.copy()
    df_live = parse_option_data(raw_list)

    if df_live.empty:
        return JSONResponse(content={
            "net_gex_1pct": [],
            "dealer_delta": [],
            "dealer_vanna": [],
            "gex": [],
            "cumulative_gex": [],
            "vega_theta_ratio": [],
            "summary_text": "",
            "sentiment": "",
            "spot": 0,
        })

    center_spot = shared_state.live_center_spot

    long_rows: List[Dict[str, Any]] = []
    for _, row in df_live.iterrows():
        strike = row["Strike Price"]
        long_rows.extend([
            {"Strike Price": strike, "OptionType": "C", "OI": row.get("Call OI", 0), "Delta": row.get("Call Delta", 0),
             "Gamma": row.get("Call Gamma", 0), "Theta": row.get("Call Theta", 0), "Vega": row.get("Vega", 0)},
            {"Strike Price": strike, "OptionType": "P", "OI": row.get("Put OI", 0), "Delta": row.get("Put Delta", 0),
             "Gamma": row.get("Put Gamma", 0), "Theta": row.get("Put Theta", 0), "Vega": row.get("Vega", 0)}
        ])
    df_long = pd.DataFrame(long_rows)

    try:
        df_sel = filter_strikes_around_spot(
                    df_long,
                    center_spot,
                    n=shared_state.live_strike_range,
                    step=shared_state.live_contract_step
                )


    except ValueError:
        return JSONResponse(content={
            "net_gex_1pct": [],
            "dealer_delta": [],
            "dealer_vanna": [],
            "gex": [],
            "cumulative_gex": [],
            "vega_theta_ratio": [],
            "summary_text": "",
            "sentiment": "",
            "spot": center_spot,
        })

    try:
        expiry_dt = datetime.strptime(live_expiry_str, "%d%b%Y")
        days_to_expiry = (expiry_dt - datetime.now()).total_seconds() / 86400
        T = max(days_to_expiry / 365.0, 1e-6)
    except Exception:
        T = 1e-6

    df_metrics = compute_metrics(df_sel, center_spot, 75, 0.15, T)
    calls_df, puts_df = separate_calls_puts(df_metrics)
    merged, zero_gamma_level = calculate_zero_gamma_level(calls_df, puts_df)
    c_sum, p_sum = summarize(calls_df, puts_df)
    current_net_gex = merged["Net GEX"].sum()

    shared_state.live_gex_history.append(current_net_gex)

    rolling_gex_ma = sum(shared_state.live_gex_history) / len(shared_state.live_gex_history)

    result = format_output_series(df_metrics, merged, calls_df, puts_df, zero_gamma_level, center_spot)
    result["rolling_gex_ma"] = rolling_gex_ma
    return JSONResponse(content=result)


@app.get("/")
async def root():
    return {"message": "GEX Analyzer backend is up and running."}
