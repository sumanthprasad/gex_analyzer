import React, { useEffect, useState } from "react";
import axios from "axios";

function LiveStockSelector({ onRawTicks }) {
  const [symbol, setSymbol] = useState("NIFTY");
  const [isStreaming, setIsStreaming] = useState(false);
  const [manualExpiry, setManualExpiry] = useState("26JUN2025");
  const [expiryOptions, setExpiryOptions] = useState([]);
  const [statusMsg, setStatusMsg] = useState("");

  const contractMap = {
    NIFTY: { contractSize: 75, step: 50 },
    BANKNIFTY: { contractSize: 30, step: 100 },
  };

  useEffect(() => {
    axios
      .get("http://localhost:8000/gfdl/expiry_list")
      .then((res) => {
        setExpiryOptions(res.data);
        if (res.data.length > 0) {
          setManualExpiry(res.data[0]);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch expiry list:", err);
      });
  }, []);

  const startStream = async () => {
    const { step } = contractMap[symbol];

    console.log("LiveStockSelector: Starting stream with expiry:", manualExpiry);

    try {
      await axios.post("http://localhost:8000/start_stream", {
        symbol,
        expiry: manualExpiry,
        strike_range: 15,
        contract_step: step,
      });
      setIsStreaming(true);
      setStatusMsg("✅ Live stream started! Please wait for charts to load...");
      setTimeout(() => setStatusMsg(""), 8000);  // optional auto-dismiss
    } catch (err) {
      console.error("Error starting stream:", err);
    }
  };

  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(async () => {
      try {
        const res = await axios.get("http://localhost:8000/raw_ticks");
        onRawTicks(res.data);
      } catch (err) {
        console.error("Error polling raw ticks:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isStreaming, symbol, manualExpiry, onRawTicks]);

  return (
    <div style={{ textAlign: "center", marginTop: "30px", marginBottom: "25px" }}>
      <select
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        style={{
          padding: "10px 15px",
          fontSize: "16px",
          borderRadius: "6px",
          border: "1px solid #ccc",
          marginRight: "15px",
        }}
      >
        <option value="NIFTY">NIFTY</option>
        <option value="BANKNIFTY">BANKNIFTY</option>
      </select>

      {expiryOptions.length > 0 ? (
        <select
          value={manualExpiry}
          onChange={(e) => setManualExpiry(e.target.value)}
          style={{
            padding: "10px 15px",
            fontSize: "16px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            marginRight: "15px",
            width: "130px",
          }}
        >
          {expiryOptions.map((exp) => (
            <option key={exp} value={exp}>
              {exp}
            </option>
          ))}
        </select>
      ) : (
        <input
          type="text"
          value={manualExpiry}
          onChange={(e) => setManualExpiry(e.target.value.toUpperCase())}
          placeholder="DDMMMyyyy"
          style={{
            padding: "10px 15px",
            fontSize: "16px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            marginRight: "15px",
            width: "130px",
            textAlign: "center",
          }}
        />
      )}
      {statusMsg && (
        <div style={{ marginTop: "10px", color: "#007bff", fontWeight: "bold" }}>
          {statusMsg}
        </div>
      )}


      <button
        onClick={startStream}
        style={{
          padding: "10px 18px",
          backgroundColor: "#007bff",
          color: "#fff",
          border: "none",
          borderRadius: "6px",
          fontSize: "16px",
          cursor: "pointer",
        }}
      >
        Start Live Stream
      </button>
    </div>
  );
}

export default LiveStockSelector;
