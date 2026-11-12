// A fictional example card, so visitors can see the result before uploading.
const stat = (key, label, code, raw_rating, score, reason, evidence) => ({
  key,
  label,
  code,
  raw_rating,
  score,
  reason,
  evidence,
  evidence_verified: Boolean(evidence),
});

const sampleCard = {
  name: "Jordan Rivera",
  target_role: "Machine Learning Engineer",
  position: "MLE",
  years_of_experience: 6,
  experience_band: "5-10 years",
  experience_multiplier: 0.92,
  overall: 81,
  tier: "gold",
  stats: [
    stat("technical_proficiency", "Technical Proficiency", "TEC", 92, 85, "Deep, production-grade ML stack with PyTorch, Spark and Kubernetes.", "Built a real-time fraud model serving 30M scores/day on Kubernetes"),
    stat("problem_solving", "Problem Solving", "PRB", 89, 82, "Cut inference latency by redesigning the feature pipeline, not just tuning.", "reduced p95 latency from 310ms to 70ms by moving features to a streaming store"),
    stat("communication", "Communication", "COM", 80, 74, "Presents to stakeholders and writes design docs, with limited evidence of wider influence.", "Wrote design docs and presented results to the risk leadership team"),
    stat("domain_fit", "Domain Fit", "FIT", 88, 81, "Core ML engineering skills transfer directly, even though the domain is new.", null),
    stat("initiative_impact", "Initiative & Impact", "IMP", 90, 83, "Owned a model end to end with a clear dollar impact.", "saving an estimated $2.1M per year in chargebacks"),
    stat("adaptability", "Adaptability", "ADP", 78, 72, "Has moved between batch and real-time systems, but always in one industry.", null),
  ],
  summary: "A proven production ML engineer with strong systems instincts. Ready for this role; the main gap is LLM and computer-vision experience.",
  strengths: ["Ships models to production at scale", "Strong latency and data-pipeline engineering", "Measurable business impact"],
  gaps: ["No computer-vision or LLM work shown", "Little evidence of mentoring or leading a team"],
  bullet_rewrites: [
    {
      original: "Worked on the model monitoring dashboard.",
      improved: "Built the model monitoring dashboard that the team used to track drift across production models.",
    },
  ],
  meta: { model: "example", latency_ms: 0, attempts: 1, job_description_provided: true },
};

export default sampleCard;
