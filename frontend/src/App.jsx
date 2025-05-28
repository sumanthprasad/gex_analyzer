import React, { useState } from "react";
import UploadForm from "./components/UploadForm";
import Charts from "./components/Charts";
import SummaryBox from "./components/SummaryBox";

function App() {
  const [chartData, setChartData] = useState(null);
  const [summary, setSummary] = useState("");
  const [symbol, setSymbol] = useState("NIFTY");

  const handleSymbolChange = (e) => {
    setSymbol(e.target.value);
  };

  return (
    <div style={{ textAlign: "center", padding: "20px" }}>
      <h1>Gamma Exposure Analysis</h1>

      <div style={{ marginBottom: "20px" }}>
        <label htmlFor="symbol-select">Select Stock/Index: </label>
        <select id="symbol-select" value={symbol} onChange={handleSymbolChange}>
          <option value="NIFTY">NIFTY</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
          <option value="RELIANCE">RELIANCE</option>
          <option value="SBIN">SBIN</option>
          <option value="HDFCBANK">HDFCBANK</option>
          <option value="TCS">TCS</option>
          <option value="INFY">INFY</option>
          {/* Add more as needed */}
        </select>
      </div>

      <UploadForm
        onData={(data) => {
          setChartData(data);
          setSummary(data.summary_text);
        }}
        chartData={chartData}
        symbol={symbol}
      />

      {chartData && <Charts data={chartData} />}
      {summary && <SummaryBox text={summary} />}
    </div>
  );
}

export default App;
