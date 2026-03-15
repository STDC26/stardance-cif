"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://10.0.0.75:8000";

interface QDSPublicData {
  asset_id: string;
  asset_name: string;
  slug: string;
  version_id: string;
  flow: {
    id: string;
    name: string;
    steps: any[];
    outcomes: any[];
    transitions: any[];
  };
}

interface SessionState {
  session_key: string;
  current_step: any;
  answers: any[];
  cumulative_score: number;
  status: string;
  outcome?: any;
}

export default function PublicQDSPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [data, setData] = useState<QDSPublicData | null>(null);
  const [session, setSession] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/q/${slug}`)
      .then((r) => {
        if (!r.ok) throw new Error(`QDS not found (${r.status})`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  async function startSession() {
    if (!data) return;
    setSubmitting(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/qds/${data.asset_id}/sessions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_key: `pub-${Date.now()}` }),
        }
      );
      if (!res.ok) throw new Error("Failed to start session");
      const s = await res.json();
      setSession(s);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function submitAnswer(value: string) {
    if (!data || !session) return;
    setSubmitting(true);
    setSelectedAnswer(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/qds/${data.asset_id}/sessions/${session.session_key}/answer`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            step_id: session.current_step?.id,
            answer_value: value,
          }),
        }
      );
      if (!res.ok) throw new Error("Failed to submit answer");
      const updated = await res.json();
      setSession(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main style={{ padding: "64px 48px", maxWidth: "640px", margin: "0 auto", textAlign: "center" }}>
        <p style={{ color: "#888" }}>Loading QDS…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main style={{ padding: "64px 48px", maxWidth: "640px", margin: "0 auto", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#842029" }}>Error</h1>
        <p style={{ color: "#666" }}>{error}</p>
      </main>
    );
  }

  if (!data) return null;

  // Pre-session: show intro
  if (!session) {
    return (
      <main style={{ padding: "64px 48px", maxWidth: "640px", margin: "0 auto", textAlign: "center" }}>
        <h1 style={{ fontSize: "2rem", fontWeight: 800, marginBottom: "12px", color: "#1F3A6E" }}>
          {data.asset_name}
        </h1>
        <p style={{ color: "#666", marginBottom: "32px" }}>
          This diagnostic will help determine your qualification. Answer each question to proceed.
        </p>
        <button
          onClick={startSession}
          disabled={submitting}
          style={{
            padding: "14px 36px", background: "#1F3A6E", color: "#fff",
            border: "none", borderRadius: "8px", fontWeight: 700,
            fontSize: "1rem", cursor: "pointer", opacity: submitting ? 0.6 : 1,
          }}
        >
          {submitting ? "Starting…" : "Begin Diagnostic"}
        </button>
      </main>
    );
  }

  // Session complete: show outcome
  if (session.status === "completed" || session.outcome) {
    return (
      <main style={{ padding: "64px 48px", maxWidth: "640px", margin: "0 auto", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 800, marginBottom: "16px", color: "#1F3A6E" }}>
          Diagnostic Complete
        </h1>
        <div style={{
          padding: "28px", border: "2px solid #19875430", borderRadius: "12px",
          background: "#f0fdf4", marginBottom: "24px",
        }}>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#198754", marginBottom: "8px" }}>
            {session.outcome?.label ?? "Result"}
          </div>
          {session.outcome?.description && (
            <p style={{ color: "#555", margin: "0 0 12px" }}>{session.outcome.description}</p>
          )}
          <div style={{ fontSize: "0.85rem", color: "#888" }}>
            Score: {session.cumulative_score} | Steps answered: {session.answers?.length ?? 0}
          </div>
          {session.outcome?.routing_target && (
            <a
              href={session.outcome.routing_target}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-block", marginTop: "16px",
                padding: "10px 24px", background: "#1F3A6E", color: "#fff",
                borderRadius: "6px", textDecoration: "none", fontWeight: 600,
              }}
            >
              Continue →
            </a>
          )}
        </div>
      </main>
    );
  }

  // Active session: show current step
  const step = session.current_step;
  return (
    <main style={{ padding: "64px 48px", maxWidth: "640px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "24px", color: "#1F3A6E" }}>
        {data.asset_name}
      </h1>

      <div style={{
        padding: "28px", border: "1px solid #dee2e6", borderRadius: "12px",
        background: "#fff", marginBottom: "24px",
      }}>
        <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "8px" }}>
          {step?.title ?? "Question"}
        </h2>
        {step?.body && <p style={{ color: "#555", marginBottom: "20px" }}>{step.body}</p>}

        {step?.config?.options && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {step.config.options.map((opt: any, i: number) => (
              <button
                key={i}
                onClick={() => setSelectedAnswer(opt.value ?? opt.label)}
                style={{
                  padding: "12px 18px", border: `2px solid ${selectedAnswer === (opt.value ?? opt.label) ? "#1F3A6E" : "#dee2e6"}`,
                  borderRadius: "8px", background: selectedAnswer === (opt.value ?? opt.label) ? "#f0f4ff" : "#fff",
                  textAlign: "left", cursor: "pointer", fontWeight: selectedAnswer === (opt.value ?? opt.label) ? 700 : 400,
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          onClick={() => selectedAnswer && submitAnswer(selectedAnswer)}
          disabled={!selectedAnswer || submitting}
          style={{
            padding: "12px 28px", background: selectedAnswer ? "#1F3A6E" : "#ccc",
            color: "#fff", border: "none", borderRadius: "8px",
            fontWeight: 600, cursor: selectedAnswer ? "pointer" : "not-allowed",
            opacity: submitting ? 0.6 : 1,
          }}
        >
          {submitting ? "Submitting…" : "Next →"}
        </button>
      </div>

      <div style={{ marginTop: "20px", fontSize: "0.8rem", color: "#aaa" }}>
        Answers: {session.answers?.length ?? 0} | Score: {session.cumulative_score}
      </div>
    </main>
  );
}
