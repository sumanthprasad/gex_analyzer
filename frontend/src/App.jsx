import React, { useState, useEffect } from "react";
import UploadForm from "./components/UploadForm";
import Charts from "./components/Charts";
import SummaryBox from "./components/SummaryBox";
import LiveStockSelector from "./components/LiveStockSelector";
import TrendingGexTable from "./components/TrendingGexTable";
import axios from "axios";

function App() {
  const [view, setView] = useState("main"); // "main" or "trending"
  const [summary, setSummary] = useState("");
  const [chartData, setChartData] = useState(null);
  const [refreshCountdown, setRefreshCountdown] = useState(60);
  const [trendingRows, setTrendingRows] = useState([]);

  const [liveInputs, setLiveInputs] = useState({
    symbol: null,
    expiry: null,
    contractSize: 75,
    vol: 0.15,
    strikeRange: 5,
  });

  // Live-data polling
  useEffect(() => {
    const { symbol, expiry } = liveInputs;
    if (!symbol || !expiry) return;

    const fetchData = async () => {
      try {
        const res = await axios.get("http://localhost:8000/live_data");
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

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setRefreshCountdown((prev) => (prev === 1 ? 60 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Trending-GEX polling
  useEffect(() => {
    const fetchTrending = async () => {
      try {
        const res = await axios.get("http://localhost:8000/trending_gex");
        setTrendingRows(res.data);
      } catch (err) {
        console.error("Trending GEX fetch failed:", err);
      }
    };

    fetchTrending();
    const id = setInterval(fetchTrending, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{ padding: "30px 5%", maxWidth: "1200px", margin: "auto", textAlign: "center" }}>
      <h1 style={{ fontSize: "2.2rem", marginBottom: "20px" }}>Gamma Exposure Analysis</h1>

      {/* View Toggle Buttons */}
      <div style={{ marginBottom: "20px" }}>
        <button
          type="button"
          onClick={() => setView("main")}
          style={{
            marginRight: "10px",
            padding: "8px 16px",
            fontWeight: view === "main" ? "bold" : "normal",
          }}
        >
          Live & Charts
        </button>
        <button
          type="button"
          onClick={() => setView("trending")}
          style={{
            padding: "8px 16px",
            fontWeight: view === "trending" ? "bold" : "normal",
          }}
        >
          Trending GEX
        </button>
      </div>

      {/* ─── Main Live & Charts Panel ───────────────────────────────────── */}
      <div style={{ display: view === "main" ? "block" : "none" }}>
        <LiveStockSelector
          onRawTicks={(parsedTicks) => {
            if (!parsedTicks || parsedTicks.length === 0) return;
            const m = parsedTicks[0]?.InstrumentIdentifier?.match(
              /([A-Z]+)_(\d{2}[A-Z]{3}\d{4})_/
            );
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

        {summary && (
          <SummaryBox
            text={summary}
            gammaWallStrike={chartData?.gamma_wall_strike}
            rollingGexMa={chartData?.rolling_gex_ma}
          />
        )}

        {chartData ? (
          <Charts data={chartData} gammaWallStrike={chartData.gamma_wall_strike} />
        ) : (
          <p style={{ marginTop: "50px" }}>
            No data yet—start live stream or upload a file.
          </p>
        )}
      </div>

      {/* ─── Trending GEX Panel ───────────────────────────────────────────── */}
      <div style={{ display: view === "trending" ? "block" : "none" }}>
        <TrendingGexTable rows={trendingRows} />
      </div>
    </div>
  );
}

export default App;
