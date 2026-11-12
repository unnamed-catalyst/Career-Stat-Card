import { useRef, useState } from "react";

const MAX_MB = 5;
const QUICK_ROLES = ["Software Engineer", "Machine Learning Engineer", "Data Analyst", "Product Manager"];

export default function UploadForm({ file, onFile, jobDesc, onJobDesc, onSubmit, loading, onExample }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState("");

  const accept = (candidate) => {
    if (!candidate) return;
    const isPdf = candidate.type === "application/pdf" || candidate.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setFileError("Please choose a PDF file.");
      return;
    }
    if (candidate.size > MAX_MB * 1024 * 1024) {
      setFileError(`That file is over ${MAX_MB} MB. Please choose a smaller PDF.`);
      return;
    }
    setFileError("");
    onFile(candidate);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    accept(e.dataTransfer.files?.[0]);
  };

  return (
    <form
      className="panel form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="step">
        <span className="step-num">1</span>
        <label className="step-title" htmlFor="resume-input">
          Your resume
        </label>
      </div>
      <div
        className={`dropzone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), inputRef.current?.click())}
        aria-describedby="resume-hint"
      >
        <input
          id="resume-input"
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          hidden
          onChange={(e) => accept(e.target.files?.[0])}
        />
        {file ? (
          <>
            <FileIcon />
            <div className="dz-text">
              <strong className="file-name">{file.name}</strong>
              <span className="muted">{(file.size / 1024).toFixed(0)} KB · click to change</span>
            </div>
          </>
        ) : (
          <>
            <UploadIcon />
            <div className="dz-text">
              <strong>Drop your PDF here or click to browse</strong>
              <span className="muted" id="resume-hint">
                Text-based PDF, up to {MAX_MB} MB
              </span>
            </div>
          </>
        )}
      </div>
      {fileError && <p className="field-error">{fileError}</p>}

      <div className="step">
        <span className="step-num">2</span>
        <label className="step-title" htmlFor="job-input">
          The job you want <span className="optional">optional</span>
        </label>
      </div>
      <textarea
        id="job-input"
        rows={4}
        placeholder="Paste a job posting for the sharpest comparison, or just type a title like “Backend Engineer”."
        value={jobDesc}
        onChange={(e) => onJobDesc(e.target.value)}
        maxLength={6000}
      />
      <div className="chips" aria-label="Quick picks">
        {QUICK_ROLES.map((role) => (
          <button type="button" key={role} className={`chip ${jobDesc === role ? "active" : ""}`} onClick={() => onJobDesc(role)}>
            {role}
          </button>
        ))}
      </div>
      <p className="hint">Leave it blank and the scout will pick the role your resume fits best.</p>

      <button type="submit" className="btn btn-primary btn-lg" disabled={!file || loading}>
        {loading ? "Scouting your resume…" : "Generate my card"}
      </button>
      <button type="button" className="btn btn-link center" onClick={onExample}>
        No resume handy? See an example card
      </button>
      <p className="privacy">
        <LockIcon /> Your resume is sent to Google's Gemini API to be scored and is not stored by this site.
      </p>
    </form>
  );
}

const UploadIcon = () => (
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
    <path d="M12 16V4m0 0-4 4m4-4 4 4" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" strokeLinecap="round" />
  </svg>
);

const FileIcon = () => (
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" strokeLinejoin="round" />
    <path d="M14 3v5h5M9 14l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const LockIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <rect x="5" y="11" width="14" height="10" rx="2" />
    <path d="M8 11V7a4 4 0 0 1 8 0v4" />
  </svg>
);
