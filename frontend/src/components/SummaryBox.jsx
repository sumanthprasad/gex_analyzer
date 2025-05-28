function SummaryBox({ text }) {
    return (
      <div style={{ whiteSpace: "pre-wrap", marginTop: "20px", fontFamily: "monospace" }}>
        <h3>Summary</h3>
        <p>{text}</p>
      </div>
    );
  }
  
  export default SummaryBox;
  