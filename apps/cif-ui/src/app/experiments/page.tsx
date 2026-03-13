"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchAllExperiments,
  startExperiment,
  pauseExperiment,
  completeExperiment,
} from "@/lib/deployment-api";

type Experiment = {
  id: string;
  experiment_id: string;
  asset_id: string;
  asset_type: string;
  experiment_name: string;
  goal_metric: string | null;
  status: string;
};

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    live: "bg-green-100 text-green-800",
    draft: "bg-gray-100 text-gray-600",
    paused: "bg-yellow-100 text-yellow-800",
    complete: "bg-blue-100 text-blue-800",
    archived: "bg-gray-100 text-gray-400",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await fetchAllExperiments();
      setExperiments(Array.isArray(data) ? data : []);
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(
    experimentId: string,
    action: "start" | "pause" | "complete"
  ) {
    setActing(experimentId);
    try {
      if (action === "start") await startExperiment(experimentId);
      else if (action === "pause") await pauseExperiment(experimentId);
      else await completeExperiment(experimentId);
      await load();
    } finally {
      setActing(null);
    }
  }

  useEffect(() => { load(); }, []);

  const getActions = (exp: Experiment) => {
    const actions: { label: string; action: "start" | "pause" | "complete" }[] = [];
    if (exp.status === "draft") actions.push({ label: "Go Live", action: "start" });
    if (exp.status === "live") {
      actions.push({ label: "Pause", action: "pause" });
      actions.push({ label: "Complete", action: "complete" });
    }
    if (exp.status === "paused") {
      actions.push({ label: "Resume", action: "start" });
      actions.push({ label: "Complete", action: "complete" });
    }
    return actions;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-widest mb-1">
              <Link href="/analytics" className="hover:text-gray-600">Analytics</Link>
              {" / "}Experiments
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Experiment Manager</h1>
            <p className="text-sm text-gray-500 mt-1">
              Create and manage A/B tests across assets
            </p>
          </div>
        </div>

        {loading ? (
          <div className="text-sm text-gray-400">Loading…</div>
        ) : experiments.length === 0 ? (
          <div className="text-sm text-gray-400">No experiments found.</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Goal</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {experiments.map(exp => (
                  <tr key={exp.experiment_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {exp.experiment_name}
                    </td>
                    <td className="px-4 py-3 text-gray-500 capitalize">
                      {exp.asset_type}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={exp.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {exp.goal_metric ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        {getActions(exp).map(({ label, action }) => (
                          <button
                            key={action}
                            onClick={() => handleAction(exp.experiment_id, action)}
                            disabled={acting === exp.experiment_id}
                            className="text-xs px-3 py-1 border border-gray-200 rounded
                              hover:bg-gray-50 disabled:opacity-50"
                          >
                            {acting === exp.experiment_id ? "…" : label}
                          </button>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/experiments/${exp.experiment_id}`}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Results →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
