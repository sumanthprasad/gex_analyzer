import React, { useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

function Charts({ data, gammaWallStrike }) {
  console.log("📈 Charts got data prop:", data);
  const [visibleCharts, setVisibleCharts] = useState({
    netGex: true,
    delta: true,
    vanna: true,
    gex: true,
    cumulativeGex: true,
    vtr: true,
  });


  const toggleChart = (key) => {
    setVisibleCharts((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const commonXAxisProps = {
    dataKey: "strike",
    interval: 0,
    angle: -45,
    textAnchor: "end",
    height: 80,
    tickMargin: 12,
    minTickGap: 20,
    tickFormatter: (val) => (typeof val === "number" ? val : ""),
  };

  const chartMargin = { top: 20, right: 30, left: 70, bottom: 60 };

  // Only keep entries where both `strike` and `value` are actual numbers
  const safeData = (series) =>
    Array.isArray(series)
      ? series.filter((d) => typeof d.strike === "number" && typeof d.value === "number")
      : [];

  const inferredSpot = data?.spot;

  const renderSpotLine = () =>
  typeof inferredSpot === "number" ? (
    <ReferenceLine
      x={inferredSpot}
      stroke="#ff0000"
      strokeWidth={2}
      strokeDasharray="3 3"
      label={{
        position: "insideTopLeft",
        value: `Spot ${inferredSpot}`,
        fontSize: 12,
        fill: "#ff0000",
      }}
    />
  ) : null;

  const renderGammaWall = () =>
  typeof gammaWallStrike === "number" ? (
    <ReferenceLine
      x={gammaWallStrike}
      stroke="#ff7300"
      strokeWidth={2}
      strokeDasharray="4 2"
      label={{
        position: "insideTopRight",
        value: `γ-Wall @ ${gammaWallStrike}`,
        fontSize: 12,
        fill: "#ff7300",
      }}
    />
  ) : null;

  // ─── TEMPORARY: force a visible container height so you see a grey box ───
  const forcedWrapperStyle = {
    width: "100%",
    height: "400px",           // ← you should see a grey rectangle even if no bars/lines draw
    backgroundColor: "#f9f9f9",
    borderRadius: "12px",
    padding: "25px",
    boxShadow: "0 4px 8px rgba(0,0,0,0.05)",
    marginBottom: "50px",
  };

  const chartTitleStyle = {
    textAlign: "center",
    fontSize: "18px",
    marginBottom: "15px",
  };

  const rollingPlot = () => {
    const rollingData = [{ time: 0, value: data.rolling_gex_ma }];
    return (
      <div style={{ ...forcedWrapperStyle, height: "200px" }}>
        <h3 style={chartTitleStyle}>Rolling GEX MA</h3>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rollingData}>
            <XAxis dataKey="time" hide />
            <YAxis hide />
            <Tooltip formatter={(v) => Number(v).toExponential(2)} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#00cc99"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const barPlot = (title, series, color = "#8884d8") => (
    <div style={forcedWrapperStyle}>
      <h3 style={chartTitleStyle}>{title}</h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={safeData(series)} margin={chartMargin}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis {...commonXAxisProps} padding={{ left: 20, right: 20 }} />
          <YAxis
            dataKey="value"
            tickFormatter={(val) => Number(val).toExponential(2)}
            width={80}
          />
          <Tooltip />
          <Legend />
          {renderSpotLine()}
          {renderGammaWall()}
          <Bar dataKey="value" fill={color} barSize={14} barCategoryGap="50%" barGap={4} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const linePlot = (title, series, color = "#0088FE") => (
    <div style={forcedWrapperStyle}>
      <h3 style={chartTitleStyle}>{title}</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={safeData(series)} margin={chartMargin}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis {...commonXAxisProps} />
          <YAxis
            dataKey="value"
            tickFormatter={(val) => Number(val).toExponential(2)}
            width={80}
          />
          <Tooltip />
          <Legend />
          {renderSpotLine()}
          {renderGammaWall()}
          <Line type="monotone" dataKey="value" stroke={color} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div style={{ padding: "10px", maxWidth: "1000px", margin: "auto" }}>
      <div style={toggleContainerStyle}>
        <label>
          <input
            type="checkbox"
            checked={visibleCharts.netGex}
            onChange={() => toggleChart("netGex")}
          />
          &nbsp;Net GEX
        </label>
        <label>
          <input
            type="checkbox"
            checked={visibleCharts.delta}
            onChange={() => toggleChart("delta")}
          />
          &nbsp;Dealer Delta
        </label>
        <label>
          <input
            type="checkbox"
            checked={visibleCharts.vanna}
            onChange={() => toggleChart("vanna")}
          />
          &nbsp;Dealer Vanna
        </label>
        <label>
          <input
            type="checkbox"
            checked={visibleCharts.gex}
            onChange={() => toggleChart("gex")}
          />
          &nbsp;GEX
        </label>
        <label>
          <input
            type="checkbox"
            checked={visibleCharts.cumulativeGex}
            onChange={() => toggleChart("cumulativeGex")}
          />
          &nbsp;Cumulative GEX
        </label>
        <label>
          <input
            type="checkbox"
            checked={visibleCharts.vtr}
            onChange={() => toggleChart("vtr")}
          />
          &nbsp;Vega/Theta Ratio
        </label>
      </div>

      {visibleCharts.netGex && barPlot("Net GEX 1% Change (Calls – Puts)", data.net_gex_1pct)}
      {visibleCharts.delta && barPlot("Dealer Delta Exposure", data.dealer_delta, "#82ca9d")}
      {visibleCharts.vanna && barPlot("Dealer Vanna Exposure", data.dealer_vanna, "#ffc658")}
      {visibleCharts.gex && barPlot("GEX", data.gex, "#ff7300")}
      {visibleCharts.cumulativeGex && linePlot("Cumulative GEX", data.cumulative_gex, "#3366cc")}
      {visibleCharts.vtr && linePlot("Vega / Theta Ratio", data.vega_theta_ratio, "#a83279")}
      {rollingPlot()}
    </div>
  );
}

const toggleContainerStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "20px",
  justifyContent: "center",
  marginBottom: "30px",
};

export default Charts;
