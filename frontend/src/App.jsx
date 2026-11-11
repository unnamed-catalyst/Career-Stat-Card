import { useEffect, useRef, useState } from "react";
import { analyzeResume, wakeServer } from "./api";
import UploadForm from "./components/UploadForm";
import LoadingCard from "./components/LoadingCard";
import PlayerCard from "./components/PlayerCard";
import ResultPanel from "./components/ResultPanel";
import CardActions from "./components/CardActions";
import sampleCard from "./sampleCard";
import "./App.css";

export default function App() {
  const [file, setFile] = useState(null);
  const [jobDesc, setJobDesc] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [server, setServer] = useState("waking"); // waking | ready | offline
  const cardRef = useRef(null);
  const resultRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    wakeServer().then((ok) => !cancelled && setServer(ok ? "ready" : "offline"));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (status === "done" || status === "loading") {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [status]);

  const handleSubmit = async () => {
    if (!file || status === "loading") return;
    setStatus("loading");
    setError("");
    try {
      const data = await analyzeResume(file, jobDesc.trim());
      setResult(data);
      setStatus("done");
      setServer("ready");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  };

  const showExample = () => {
    setResult(sampleCard);
    setError("");
    setStatus("done");
  };

  // ?example opens the example card directly (handy for sharing and screenshots).
  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("example")) showExample();
  }, []);

  const reset = () => {
    setResult(null);
    setStatus("idle");
    setFile(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <img src={`${import.meta.env.BASE_URL}icon.svg`} alt="" width="28" height="28" />
          <span>Career Stat Card</span>
        </div>
        <ServerPill state={server} />
      </header>

      <main>
        <section className="hero">
          <h1>
            What's your <span className="accent">rating</span>?
          </h1>
          <p className="lede">
            Upload your resume and the job you want. Get a FIFA-style player card with six career stats, the evidence
            behind each one, and what to work on next.
          </p>
        </section>

        <UploadForm
          file={file}
          onFile={setFile}
          jobDesc={jobDesc}
          onJobDesc={setJobDesc}
          onSubmit={handleSubmit}
          loading={status === "loading"}
          onExample={showExample}
        />

        {status === "error" && (
          <div className="alert" role="alert">
            <strong>Couldn't make your card.</strong> {error}
            <button className="btn btn-ghost" onClick={handleSubmit}>
              Try again
            </button>
          </div>
        )}

        <div ref={resultRef} className="result-anchor" />

        {status === "loading" && <LoadingCard serverWaking={server !== "ready"} />}

        {status === "done" && result && (
          <section className="result" aria-live="polite">
            {result === sampleCard && (
              <p className="example-banner">This is an example card for a fictional candidate. Upload your resume to get yours.</p>
            )}
            <div className="result-card">
              <PlayerCard ref={cardRef} card={result} />
              <CardActions card={result} cardRef={cardRef} onReset={reset} />
            </div>
            <ResultPanel card={result} />
          </section>
        )}
      </main>

      <footer className="footer">
        Built by Nawaf Nazeer ·{" "}
        <a href="https://github.com/unnamed-catalyst/Career-Stat-Card" target="_blank" rel="noreferrer">
          Source on GitHub
        </a>
      </footer>
    </div>
  );
}

function ServerPill({ state }) {
  const text = { waking: "Warming up the scout…", ready: "Scout ready", offline: "Server unreachable" }[state];
  const short = { waking: "Waking…", ready: "Ready", offline: "Offline" }[state];
  return (
    <span className={`pill pill-${state}`} title="The free server sleeps when idle and takes up to a minute to wake.">
      <span className="dot" aria-hidden="true" />
      <span className="pill-text-long">{text}</span>
      <span className="pill-text-short" aria-hidden="true">
        {short}
      </span>
    </span>
  );
}
