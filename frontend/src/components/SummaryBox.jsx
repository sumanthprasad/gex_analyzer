import React from "react";

function SummaryBox({ text, gammaWallStrike, rollingGexMa }) {
  const sentimentLine = text.split("\n").find(line => line.toLowerCase().includes("sentiment"));
  const sentiment = sentimentLine?.split(":")[1]?.trim() || "Unknown";

  const badgeColor = {
    Bullish: "#28a745",
    "Mildly Bullish": "#70c96f",
    Bearish: "#dc3545",
    "Mildly Bearish": "#ff7777",
    Sideways: "#ffc107",
    Neutral: "#6c757d",
    Unknown: "#adb5bd"
  }[sentiment] || "#007bff";

  return (
    <div style={boxStyle}>
      <h2 style={titleStyle}>📊 Summary</h2>
  
      {typeof gammaWallStrike === "number" && (
        <div style={{ marginBottom: "12px", fontSize: "16px" }}>
          <strong>Gamma Wall:</strong> {gammaWallStrike}
        </div>
      )}
  
      {typeof rollingGexMa === "number" && (
        <div style={{ marginBottom: "12px", fontSize: "16px" }}>
          <strong>Rolling GEX MA:</strong> {rollingGexMa.toExponential(2)}
        </div>
      )}
  
      <pre style={summaryStyle}>{text}</pre>
      <div style={{ marginTop: "15px" }}>
        <span style={{ ...badgeStyle, backgroundColor: badgeColor }}>
          Sentiment: {sentiment}
        </span>
      </div>
    </div>
  );
  
}

// Styles
const boxStyle = {
  background: "#ffffff",
  padding: "25px",
  margin: "40px auto 20px",
  borderRadius: "12px",
  maxWidth: "850px",
  boxShadow: "0 6px 18px rgba(0, 0, 0, 0.04)",
  textAlign: "center",
};

const titleStyle = {
  marginBottom: "16px",
  fontWeight: "600",
  fontSize: "24px",
  color: "#222"
};

const summaryStyle = {
  background: "#f5f7fa",
  padding: "18px",
  borderRadius: "8px",
  fontFamily: "monospace",
  fontSize: "14px",
  lineHeight: "1.65",
  whiteSpace: "pre-wrap",
  wordWrap: "break-word",
  display: "inline-block",
  textAlign: "left",
  maxWidth: "100%",
  boxShadow: "inset 0 0 5px rgba(0,0,0,0.05)"
};

const badgeStyle = {
  display: "inline-block",
  padding: "8px 16px",
  borderRadius: "20px",
  color: "#fff",
  fontWeight: 500,
  fontSize: "14px",
  boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
};

export default SummaryBox;
