import React, { useState, useEffect } from "react";
import axios from "axios";

function UploadForm({ onData, chartData, symbol }) {
  const [file, setFile] = useState(null);
  const [spot, setSpot] = useState("");
  const [vol, setVol] = useState(0.15);
  const [strikePriceRange, setStrikePriceRange] = useState("5");
  const [expiry, setExpiry] = useState("");
  const [contractSize, setContractSize] = useState("75");

  // Auto-fill fields from live_data if no file is uploaded
  useEffect(() => {
    if (file) return;

    const fetchLiveDefaults = async () => {
      try {
        const res = await axios.get("http://localhost:8000/live_data");
        const data = res.data;

        if (data.length > 0) {
          const instrument = data[0].InstrumentIdentifier;
          const expiryMatch = instrument.match(/_(\d{2}[A-Z]{3}\d{4})_/);

          if (expiryMatch) {
            const expiryStr = expiryMatch[1];
            const expiryDate = parseExpiry(expiryStr);
            const today = new Date();
            const diffInYears = (expiryDate - today) / (1000 * 60 * 60 * 24 * 365);
            setExpiry(diffInYears.toFixed(4));
          }

          const strikes = data.map(d => {
            const parts = d.InstrumentIdentifier.split("_");
            return parseInt(parts[parts.length - 1]);
          }).filter(s => !isNaN(s));

          const avgStrike = Math.round(strikes.reduce((a, b) => a + b, 0) / strikes.length);
          setSpot(avgStrike.toString());

          if (symbol === "BANKNIFTY") setContractSize("30");
          else if (symbol === "NIFTY") setContractSize("75");
        }
      } catch (err) {
        console.error("Failed to fetch live defaults:", err);
      }
    };

    fetchLiveDefaults();
  }, [file, symbol]);

  const parseExpiry = (str) => {
    const months = {
      JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5,
      JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11
    };
    const day = parseInt(str.slice(0, 2));
    const mon = months[str.slice(2, 5).toUpperCase()];
    const year = parseInt(str.slice(5));
    return new Date(year, mon, day);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      alert("Please upload a file.");
      return;
    }

    const form = new FormData();
    form.append("file", file);
    form.append("spot", spot);
    form.append("vol", vol);
    form.append("strikes", strikePriceRange);
    form.append("expiry", expiry);
    form.append("contractSize", contractSize);

    try {
      const res = await axios.post("http://localhost:8000/compute", form);
      onData(res.data);
    } catch (err) {
      console.error("Manual file upload failed:", err);
    }
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
      a.download = `${symbol}_gex_chart.png`;
      a.href = pngImg;
      a.click();
    };
    img.src = url;
  };

  return (
    <form onSubmit={handleSubmit} style={formStyle}>
      <div style={rowStyle}>
        {/* File Upload */}
        <div style={{ ...itemStyle, minWidth: "220px" }}>
          <label style={labelStyle}>Upload CSV/XLSX:</label>
          <input
            type="file"
            accept=".csv, .xlsx, .xls"
            onChange={(e) => setFile(e.target.files[0])}
            style={inputStyle}
          />
          {file && (
            <span style={{ fontSize: "12px", marginTop: "4px", color: "#555", wordBreak: "break-all" }}>
              📄 {file.name}
            </span>
          )}
        </div>

        {/* Other Fields */}
        <FormItem label="Spot Price:" type="number" value={spot} onChange={(e) => setSpot(e.target.value)} />
        <FormItem label="Volatility:" type="number" value={vol} onChange={(e) => setVol(e.target.value)} step="0.01" />
        <FormItem label="± Strikes:" type="number" value={strikePriceRange} onChange={(e) => setStrikePriceRange(e.target.value)} />
        <FormItem label="Expiry (Yrs):" type="number" value={expiry} onChange={(e) => setExpiry(e.target.value)} step="0.01" />
        <FormItem label="Contract Size:" type="number" value={contractSize} onChange={(e) => setContractSize(e.target.value)} />
      </div>

      <div style={{ textAlign: "center", marginTop: "20px" }}>
        <button type="submit" style={btnStyle}>Compute</button>
        {chartData && (
          <button type="button" style={{ ...btnStyle, marginLeft: "15px" }} onClick={handleSaveChart}>
            Save Chart
          </button>
        )}
      </div>
    </form>
  );
}

const FormItem = ({ label, type, value, onChange, step }) => (
  <div style={itemStyle}>
    <label style={labelStyle}>{label}</label>
    <input
      type={type}
      value={value}
      onChange={onChange}
      step={step}
      style={inputStyle}
    />
  </div>
);

// Styles
const formStyle = {
  backgroundColor: "#f4f4f4",
  padding: "20px",
  borderRadius: "10px",
  maxWidth: "95%",
  margin: "auto",
  marginBottom: "30px",
  boxShadow: "0 4px 8px rgba(0,0,0,0.05)"
};

const rowStyle = {
  display: "flex",
  flexWrap: "wrap",
  justifyContent: "space-between",
  gap: "15px"
};

const itemStyle = {
  display: "flex",
  flexDirection: "column",
  flex: "1 1 150px",
  minWidth: "150px"
};

const labelStyle = {
  fontSize: "13px",
  fontWeight: "bold",
  marginBottom: "4px"
};

const inputStyle = {
  padding: "6px 8px",
  borderRadius: "4px",
  border: "1px solid #ccc",
  fontSize: "13px",
  width: "100%"
};

const btnStyle = {
  padding: "10px 20px",
  backgroundColor: "#007bff",
  color: "#fff",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
  fontWeight: "bold"
};

export default UploadForm;
