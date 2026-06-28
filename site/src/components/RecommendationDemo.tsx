"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "./Section";

interface RecommendationItem {
  widget_id: number;
  widget_type: string;
  score: number;
}

interface RecommendationResponse {
  user_id: number;
  method_used: string;
  is_cold_start: boolean;
  why: string;
  recommendations: RecommendationItem[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function RecommendationDemo() {
  const [userId, setUserId] = useState("7493");
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchRecommendation() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/recommend?user_id=${encodeURIComponent(userId)}&n=5`
      );
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `Request failed (${res.status})`);
      }
      const data: RecommendationResponse = await res.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <p className="text-sm font-medium text-foreground">
        Try it live — get a real recommendation
      </p>
      <p className="mt-1 text-sm text-muted">
        Calls the deployed FastAPI hybrid recommender directly. User IDs
        1–10,000 exist; the model gracefully falls back to content-based
        cold-start for any user with little or no interaction history.
      </p>

      <div className="mt-4 flex gap-2">
        <input
          type="number"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="user_id"
          className="w-full rounded-lg border border-hairline bg-elevated px-3 py-2 text-sm text-foreground outline-none focus:border-[var(--color-accent)]"
        />
        <button
          onClick={fetchRecommendation}
          disabled={loading || !userId}
          className="cursor-pointer rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          style={{ backgroundColor: "var(--color-accent)" }}
        >
          {loading ? "Loading…" : "Recommend"}
        </button>
      </div>

      <AnimatePresence mode="wait">
        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-3 text-sm text-[#f47174]"
          >
            {error} — the API may be cold-starting (free-tier Render spins
            down when idle); try again in ~30s.
          </motion.p>
        )}

        {result && !error && (
          <motion.div
            key={result.user_id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="mt-4 rounded-lg border border-hairline bg-elevated/40 p-4"
          >
            <p className="text-xs uppercase tracking-wide text-accent">
              method: {result.method_used}{" "}
              {result.is_cold_start && "(cold-start fallback)"}
            </p>
            <p className="mt-1 text-sm text-muted">{result.why}</p>
            <ul className="mt-3 space-y-1.5">
              {result.recommendations.map((r) => (
                <li
                  key={r.widget_id}
                  className="num flex items-center justify-between text-sm text-foreground"
                >
                  <span>
                    widget #{r.widget_id} · {r.widget_type}
                  </span>
                  <span className="text-faint">{r.score.toFixed(3)}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
