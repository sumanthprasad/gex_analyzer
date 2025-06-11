import React, { useState, useEffect } from "react";
import UploadForm from "./components/UploadForm";
import Charts from "./components/Charts";
import SummaryBox from "./components/SummaryBox";
import LiveStockSelector from "./components/LiveStockSelector";
import axios from "axios";

function App() {
  const [summary, setSummary] = useState("");
  const [chartData, setChartData] = useState(null);
  const [refreshCountdown, setRefreshCountdown] = useState(60);

  const [liveInputs, setLiveInputs] = useState({
    symbol: null,
    expiry: null,
    contractSize: 75,
    vol: 0.15,
    strikeRange: 5,
  });

  useEffect(() => {
    const { symbol, expiry } = liveInputs;
    if (!symbol || !expiry) return;

    const fetchData = async () => {
      try {
        const res = await axios.get("http://localhost:8000/live_data");
        console.log("⚙️ fetchData returned:", res.data);
        setChartData(res.data);
        setSummary(res.data.summary_text || "");
      } catch (err) {
        console.error("Live auto-fetch failed:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [liveInputs.symbol, liveInputs.expiry]);

  useEffect(() => {
    const timer = setInterval(() => {
      setRefreshCountdown((prev) => (prev === 1 ? 60 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ padding: "30px 5%", maxWidth: "1200px", margin: "auto", textAlign: "center" }}>
      <h1 style={{ fontSize: "2.2rem", marginBottom: "20px" }}>Gamma Exposure Analysis</h1>

      <LiveStockSelector
        onRawTicks={(parsedTicks) => {
          if (!parsedTicks || parsedTicks.length === 0) return;
          const m = parsedTicks[0]?.InstrumentIdentifier?.match(/([A-Z]+)_(\d{2}[A-Z]{3}\d{4})_/);
          if (!m) return;
          const symbol = m[1];
          const expiry = m[2];

          setLiveInputs((prev) => ({
            ...prev,
            symbol,
            expiry,
          }));
        }}
      />

      <div style={{ fontSize: "14px", color: "#555", marginBottom: "15px" }}>
        🔄 Auto‐refresh in: <strong>{refreshCountdown}s</strong>
      </div>

      <UploadForm
        onData={(data) => {
          setChartData(data);
          setSummary(data.summary_text || "");
        }}
        chartData={chartData}
        symbol={liveInputs.symbol || "NIFTY"}
      />

      {summary && <SummaryBox text={summary} gammaWallStrike={chartData.gamma_wall_strike} rollingGexMa={chartData.rolling_gex_ma}/>}
      {chartData ? (
        <Charts data={chartData} gammaWallStrike={chartData.gamma_wall_strike} />
      ) : (
        <p style={{ textAlign: "center", marginTop: "50px" }}>
          No data yet—start live stream or upload a file.
        </p>
      )}
    </div>
  );
}

export default App;
