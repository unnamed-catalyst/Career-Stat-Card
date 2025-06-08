import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [jobDesc, setJobDesc] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("job_description", jobDesc);

    try {
      setLoading(true);
      const res = await axios.post("https://career-stat-cards.onrender.com/analyze", formData);
      setResult(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <h1>🎯 Career Stat Card</h1>
      <form onSubmit={handleSubmit}>
        <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} required />
        <input
          type="text"
          placeholder="Job Title or Description"
          value={jobDesc}
          onChange={(e) => setJobDesc(e.target.value)}
        />
        <button type="submit">{loading ? "Analyzing..." : "Generate Card"}</button>
        <div className="message">{loading ? "The first run may take ~40-60 seconds due to API inactivity" : ""}</div>
      </form>

      {result && (
        <div>
          <div className="card">
            <h2>{result.name}</h2>
            <h3 title={result.experience}>{result.target_role}</h3>
            <div className="stats">
              {Object.entries(result.scores).map(([key, value]) => (
                <div className="stat" key={key} title={result.explanations[key]}>
                  <strong>{key}</strong>
                  <span>{value}</span>
                </div>
              ))}
            </div>
          </div>
          <p className="hover-hint">💡 Hover over each stat to see the reasoning</p>
        </div>
        
      )}
    </div>
  );
}

export default App;
