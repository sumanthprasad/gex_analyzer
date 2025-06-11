import asyncio
import json
import websockets
import re
import shared_state

# ------------------------------------------------------------------------------------
# 1) Replace these placeholders with your real GFDL WebSocket endpoint & API key:
# ------------------------------------------------------------------------------------
GFDL_WS_ENDPOINT = "wss://test.lisuns.com:4576/"
GFDL_ACCESS_KEY   = "cacedda4-cc86-4858-982a-397ba5866dd9"

# ------------------------------------------------------------------------------------
# 2) This list will store all live Option‐Greek ticks. FastAPI’s /live_data will serve this.
# ------------------------------------------------------------------------------------
live_ticks_cache: list = []

# We'll suppress the flood of "Echo" logs by only printing them once every 10 seconds:
_last_echo_print = 0


async def _ws_consumer(
    symbol: str,
    expiry: str,
    fallback_spot: float,
    strike_range: int,
    contract_step: int
):
    """
    1) Authenticate to GFDL.
    2) Fetch the Futures price (“<symbol>-I”), round to nearest contract_step.
    3) SubscribeOptionChain + SubscribeOptionChainGreeks (both Depth=strike_range).
    4) One‐off GetLastQuoteOptionGreeksChain for a snapshot.
    5) Listen for incoming messages of types:
       • Echo
       • RealtimeOptionChainResult
       • RealtimeOptionChainGreeksResult
       • LastQuoteOptionGreeksChainResult
       • OptionGreeksChainWithQuoteResult
       • RequestError
    Any time a message contains a list of ticks, parse each tick
    and append to live_ticks_cache as {InstrumentIdentifier, OpenInterest, Delta, Gamma, Vega, Theta}.
    """
    global _last_echo_print
    strike_regex = re.compile(r"_(\d+)$")

    try:
        print(f"[WS] Connecting to {GFDL_WS_ENDPOINT} …")
        async with websockets.connect(GFDL_WS_ENDPOINT, max_size=1024 * 1024 * 512) as ws:
            # ────────────────────────────────────────────────────────────────────────
            # A) AUTHENTICATE
            # ────────────────────────────────────────────────────────────────────────
            auth_payload = {
                "MessageType": "Authenticate",
                "Password":    GFDL_ACCESS_KEY
            }
            await ws.send(json.dumps(auth_payload))
            print("[WS] Sent Authenticate payload")

            while True:
                greeting = await ws.recv()
                data = json.loads(greeting)

                if data.get("MessageType") == "AuthenticateResult" and data.get("Message") == "Welcome!":
                    print("[WS] Authentication succeeded")
                    break

                if data.get("MessageType") == "Echo":
                    now = asyncio.get_event_loop().time()
                    # print "Echo" every 10 seconds at most
                    if now - _last_echo_print > 10:
                        print("[WS] Received Echo (keepalive)")
                        _last_echo_print = now
                    await ws.send(json.dumps({"MessageType": "Echo"}))
                    continue

            # ────────────────────────────────────────────────────────────────────────
            # B) GET THE FUTURES QUOTE FOR "<symbol>-I"
            # ────────────────────────────────────────────────────────────────────────
            fut_inst = f"{symbol}-I"
            print(f"[WS] Requesting Futures quote for {fut_inst} (GetLastQuote)")

            chosen_spot = None
            try:
                get_fut_payload = {
                    "MessageType":          "GetLastQuote",
                    "Exchange":             "NFO",
                    "InstrumentIdentifier": fut_inst,
                    "isShortIdentifier":    "false"
                }
                await ws.send(json.dumps(get_fut_payload))

                # Wait until either LastQuoteResult or RequestError arrives
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("MessageType") == "Echo":
                        now = asyncio.get_event_loop().time()
                        if now - _last_echo_print > 10:
                            print("[WS] Received Echo (keepalive)")
                            _last_echo_print = now
                        await ws.send(json.dumps({"MessageType": "Echo"}))
                        continue

                    if data.get("MessageType") == "RequestError":
                        chosen_spot = None
                        break

                    if data.get("MessageType") == "LastQuoteResult":
                        chosen_spot = data.get("LastTradePrice")
                        print(f"[WS] Retrieved Futures spot = {chosen_spot}")
                        break

            except Exception:
                chosen_spot = None
            
            # If no valid quote, fall back to what FastAPI gave us
            if chosen_spot is None:
                chosen_spot = fallback_spot
                print(f"[WS] Using fallback spot = {chosen_spot}")

            # Round to nearest multiple of contract_step
            nearest_multiple = int(round(chosen_spot / contract_step) * contract_step)
            rounded_spot = nearest_multiple
            print(f"[WS] Rounded spot {chosen_spot} → {rounded_spot} (contract_step={contract_step})")

            # ────────────────────────────────────────────────────────────────────────
            # Store the official “center spot” so main.py’s /live_data use it
            shared_state.live_center_spot = rounded_spot
            # ────────────────────────────────────────────────────────────────────────

            # ────────────────────────────────────────────────────────────────────────
            # C) SUBSCRIBE to OPTION CHAIN + GREEKS + SNAPSHOT
            # ────────────────────────────────────────────────────────────────────────

            # 1) SubscribeOptionChain
            sub_chain_payload = {
                "MessageType":  "SubscribeOptionChain",
                "Exchange":     "NFO",
                "Product":      symbol,
                "Expiry":       expiry,
                "StrikePrice":  str(rounded_spot),
                "Depth":        str(strike_range),
                "Unsubscribe":  "false"
            }
            await ws.send(json.dumps(sub_chain_payload))
            print(f"[WS] Sent subscription (OptionChain) → {sub_chain_payload}")
            await asyncio.sleep(0.2)

            # 2) SubscribeOptionChainGreeks
            sub_chain_greeks_payload = {
                "MessageType":  "SubscribeOptionChainGreeks",
                "Exchange":     "NFO",
                "Product":      symbol,
                "Expiry":       expiry,
                "StrikePrice":  str(rounded_spot),
                "Depth":        str(strike_range),
                "Unsubscribe":  "false"
            }
            await ws.send(json.dumps(sub_chain_greeks_payload))
            print(f"[WS] Sent subscription (OptionChainGreeks) → {sub_chain_greeks_payload}")
            await asyncio.sleep(0.2)

            # 3) One‐off snapshot: GetLastQuoteOptionGreeksChain
            one_off_payload = {
                "MessageType": "GetLastQuoteOptionGreeksChain",
                "Exchange":    "NFO",
                "Product":     symbol
            }
            await ws.send(json.dumps(one_off_payload))
            print(f"[WS] Sent one-off GetLastQuoteOptionGreeksChain → {one_off_payload}")

            print(f"[WS] Listening for Option‐Chain / Greeks messages around strike {rounded_spot} …")

            # ────────────────────────────────────────────────────────────────────────
            # D) LISTEN FOREVER for:
            #     • Echo
            #     • RealtimeOptionChainResult
            #     • RealtimeOptionChainGreeksResult
            #     • LastQuoteOptionGreeksChainResult
            #     • OptionGreeksChainWithQuoteResult
            #     • RequestError
            # ────────────────────────────────────────────────────────────────────────
            while True:
                raw_msg = await ws.recv()
                data = json.loads(raw_msg)
                msg_type = data.get("MessageType")

                if msg_type == "Echo":
                    now = asyncio.get_event_loop().time()
                    if now - _last_echo_print > 10:
                        print("[WS] Received Echo (keepalive)")
                        _last_echo_print = now
                    await ws.send(json.dumps({"MessageType": "Echo"}))
                    continue

                if msg_type == "RealtimeOptionChainResult":
                    entries = _extract_first_list(data)
                    print(f"[WS] RealtimeOptionChainResult with {len(entries)} entries")
                    continue

                if msg_type == "RealtimeOptionChainGreeksResult":
                    entries = _extract_first_list(data)
                    print(f"[WS] Realtime Greeks tick with {len(entries)} entries")
                    for tick in entries:
                        _append_parsed_tick(tick, strike_regex)
                    # Prevent unbounded growth: keep only most recent 5000 ticks
                    if len(live_ticks_cache) > 5000:
                        live_ticks_cache[:] = live_ticks_cache[-5000:]
                    continue

                if msg_type in ("LastQuoteOptionGreeksChainResult", "OptionGreeksChainWithQuoteResult"):
                    entries = _extract_first_list(data)
                    print(f"[WS] Snapshot Greeks chain ({msg_type}) with {len(entries)} entries")
                    for tick in entries:
                        _append_parsed_tick(tick, strike_regex)
                    if len(live_ticks_cache) > 5000:
                        live_ticks_cache[:] = live_ticks_cache[-5000:]
                    continue

                if msg_type == "RequestError":
                    print(f"[WS] RequestError: {data.get('Message', '<no message>')} — ignoring")
                    continue

                # All other message types are ignored silently

    except Exception as e:
        print(f"[WS] Exception in WS consumer: {e}")


def _extract_first_list(payload: dict) -> list:
    """
    Returns the first encountered list value in payload (or [] if none).
    This way, we don’t need to know exactly which key holds ["data"] or
    ["OptionGreeksChain"], etc.
    """
    for value in payload.values():
        if isinstance(value, list):
            return value
    return []


def _append_parsed_tick(tick: dict, strike_regex: re.Pattern):
    """
    From a single tick dict (which may contain keys like "InstrumentIdentifier",
    "OpenInterest", "Delta", "Gamma", "Vega", "Theta", etc.), extract the strike
    number and append a simplified record into live_ticks_cache.
    """
    instr = tick.get("InstrumentIdentifier", "")
    m = strike_regex.search(instr)
    if not m:
        return

    parsed_tick = {
        "InstrumentIdentifier": instr,
        "OpenInterest":         tick.get("OpenInterest", 0),
        "Delta":                tick.get("Delta", 0) or 0.0,
        "Gamma":                tick.get("Gamma", 0) or 0.0,
        "Vega":                 tick.get("Vega", 0) or 0.0,
        "Theta":                tick.get("Theta", 0) or 0.0,
    }
    live_ticks_cache.append(parsed_tick)


def start_background_ws_loop(
    symbol: str,
    expiry: str,
    spot: float,
    strike_range: int,
    contract_step: int
):
    """
    Invoked by FastAPI’s /start_stream. Launches _ws_consumer(...) as an asyncio Task.
    """
    loop = asyncio.get_event_loop()
    loop.create_task(_ws_consumer(symbol, expiry, spot, strike_range, contract_step))
    print(f"[WS] Launched background WS task for {symbol} / {expiry}")


def clear_live_cache():
    """
    Called by FastAPI whenever “Start Live Stream” is clicked again.
    Clears the in‐memory cache.
    """
    global live_ticks_cache
    live_ticks_cache = []
