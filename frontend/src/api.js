export const API_URL = (import.meta.env.VITE_API_URL || "https://career-stat-cards.onrender.com").replace(/\/$/, "");

const ANALYZE_TIMEOUT_MS = 90_000;

async function fetchWithTimeout(url, options = {}, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/** Ping the API so a sleeping free-tier server starts waking up early. */
export async function wakeServer() {
  try {
    const res = await fetchWithTimeout(`${API_URL}/health`, {}, 75_000);
    return res.ok;
  } catch {
    return false;
  }
}

export async function analyzeResume(file, jobDescription) {
  const form = new FormData();
  form.append("file", file);
  form.append("job_description", jobDescription);

  let res;
  try {
    res = await fetchWithTimeout(`${API_URL}/analyze`, { method: "POST", body: form }, ANALYZE_TIMEOUT_MS);
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("This is taking longer than usual. The server may still be waking up, so please try again.");
    }
    throw new Error("Couldn't reach the server. Check your connection and try again.");
  }

  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error page */
  }
  if (!res.ok) {
    throw new Error(body?.error || "Something went wrong while scoring your resume. Please try again.");
  }
  return body;
}
