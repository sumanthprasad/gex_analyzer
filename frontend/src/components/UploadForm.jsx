import React, { useState } from "react";
import axios from "axios";

function UploadForm({ onData, chartData, symbol }) {
  const [file, setFile] = useState(null);
  const [spot, setSpot] = useState("");
  const [vol, setVol] = useState(0.15);
  const [strikePriceRange, setStrikePriceRange] = useState("12");
  const [expiry, setExpiry] = useState("");
  const [contractSize, setContractSize] = useState("75");
  const [columnMode, setColumnMode] = useState("keyword");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const form = new FormData();
    form.append("file", file);
    form.append("spot", spot);
    form.append("vol", vol);
    form.append("strikes", strikePriceRange);
    form.append("expiry", expiry);
    form.append("contractSize", contractSize);
    form.append("columnMode", columnMode);

    const res = await axios.post("http://localhost:8000/compute", form);
    onData(res.data);
  };

  const handleSaveChart = () => {
    const svg = document.querySelector("svg");
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();
    const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);

    img.onload = function () {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);
      const pngImg = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.download = "gex_chart.png";
      a.href = pngImg;
      a.click();
    };
    img.src = url;
  };

  const formRowStyle = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    margin: "10px 0",
    maxWidth: "400px"
  };

  const labelStyle = { minWidth: "160px", textAlign: "right", marginRight: "10px" };

  return (
    <form onSubmit={handleSubmit} style={{ marginBottom: "20px", margin: "auto", maxWidth: "500px" }}>
      <div style={formRowStyle}>
        <label style={labelStyle}>Select file to Uplpad:</label>
        <input type="file" accept=".csv, .xlsx, .xls" onChange={(e) => setFile(e.target.files[0])} />
      </div>

      <div style={formRowStyle}>
        <label style={labelStyle}>Spot Price:</label>
        <input type="number" value={spot} onChange={(e) => setSpot(e.target.value)} />
      </div>

      <div style={formRowStyle}>
        <label style={labelStyle}>Volatility (e.g. 0.15):</label>
        <input type="number" value={vol} onChange={(e) => setVol(e.target.value)} />
      </div>

      <div style={formRowStyle}>
        <label style={labelStyle}>Strike Price ± (default 12):</label>
        <input type="number" value={strikePriceRange} onChange={(e) => setStrikePriceRange(e.target.value)} />
      </div>

      <div style={formRowStyle}>
        <label style={labelStyle}>Time to Expiry (Years):</label>
        <input type="number" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
      </div>

      <div style={formRowStyle}>
        <label style={labelStyle}>Contract Size (default 75):</label>
        <input type="number" value={contractSize} onChange={(e) => setContractSize(e.target.value)} />
      </div>

      <div style={formRowStyle}>
        <label style={labelStyle}>Column Detection Mode:</label>
        <select value={columnMode} onChange={(e) => setColumnMode(e.target.value)}>
          <option value="keyword">Keyword Detection</option>
          <option value="exact" disabled>Exact Match (Coming Soon)</option>
          <option value="regex" disabled>Regex Match (Coming Soon)</option>
        </select>
      </div>

      <div style={{ marginTop: "20px", textAlign: "center" }}>
        <button type="submit">Compute</button>
        {chartData && <button type="button" onClick={handleSaveChart} style={{ marginLeft: "10px" }}>Save Chart</button>}
      </div>
    </form>
  );
}

export default UploadForm;
