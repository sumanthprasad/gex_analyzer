import React, { useRef, useEffect } from "react";

export default function TrendingGexTable({ rows }) {
  const bottomRef = useRef();

  // auto-scroll on new data
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [rows]);

  return (
    <div style={{ maxHeight: "400px", overflowY: "auto", marginTop: "20px" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {["Time", "Current Net GEX (scaled 1e11)", "New Net GEX (scaled 1e11)", "Change in Net Gex (scaled 1e11)", "Direction"].map((h) => (
              <th
                key={h}
                style={{ padding: "8px", borderBottom: "1px solid #ddd", textAlign: "left" }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const net = r.netGex.toFixed(2);
            const newNet = r.newNetGex.toFixed(2);
            const delta = r.deltaGex.toFixed(2);
            return (
              <tr key={i}>
                <td style={{ padding: "6px" }}>{r.time}</td>
                <td style={{ padding: "6px" }}>{net}</td>
                <td style={{ padding: "6px" }}>{newNet}</td>
                <td style={{ padding: "6px" }}>{delta}</td>
                <td
                  style={{
                    padding: "6px",
                    color:
                      r.direction === "↑"
                        ? "green"
                        : r.direction === "↓"
                        ? "red"
                        : "grey",
                  }}
                >
                  {r.direction}
                </td>
              </tr>
            );
          })}
          <tr ref={bottomRef} />
        </tbody>
      </table>
    </div>
  );
}
