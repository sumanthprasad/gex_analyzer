import React from "react";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

function Charts({ data }) {
  const commonXAxisProps = {
    dataKey: "strike",
    interval: 0, // show all ticks
    angle: -45, // optional: tilt labels for better readability
    textAnchor: "end",
    label: {
      value: "Strike Price",
      position: "insideBottom",
      offset: -5
    }
  };

  const barPlot = (title, series, color = "#8884d8") => (
    <div style={{ margin: "40px 0" }}>
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={series}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis {...commonXAxisProps} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="value" fill={color} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const linePlot = (title, series, color = "#0088FE") => (
    <div style={{ margin: "40px 0" }}>
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={series}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis {...commonXAxisProps} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="value" stroke={color} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div>
      {barPlot("Net GEX 1% Change (Calls - Puts)", data.net_gex_1pct)}
      {barPlot("Dealer Delta Exposure", data.dealer_delta, "#82ca9d")}
      {barPlot("Dealer Vanna Exposure", data.dealer_vanna, "#ffc658")}
      {barPlot("GEX", data.gex, "#ff7300")}
      {linePlot("Cumulative GEX", data.cumulative_gex, "#3366cc")}
      {linePlot("Vega / Theta Ratio", data.vega_theta_ratio, "#a83279")}
    </div>
  );
}

export default Charts;
