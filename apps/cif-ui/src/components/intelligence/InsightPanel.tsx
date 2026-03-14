"use client";

interface InsightPanelProps {
  title?: string;
  insight: string;
  provider: string;
  latency_ms: number;
  context_keys?: number;
  isLoading?: boolean;
  error?: string | null;
}

export default function InsightPanel({
  title = "AI Insight",
  insight,
  provider,
  latency_ms,
  context_keys,
  isLoading = false,
  error = null,
}: InsightPanelProps) {
  if (error) {
    return (
      <div className="bg-white border border-red-200 rounded-xl p-5">
        <div className="text-sm text-red-500">{error}</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-100 rounded w-1/3" />
          <div className="h-3 bg-gray-100 rounded w-full" />
          <div className="h-3 bg-gray-100 rounded w-5/6" />
          <div className="h-3 bg-gray-100 rounded w-2/3" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-gray-700">
          {title}
        </span>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              provider === "local"
                ? "bg-green-100 text-green-800"
                : "bg-blue-100 text-blue-800"
            }`}
          >
            {provider}
          </span>
          <span className="text-xs text-gray-400">{latency_ms}ms</span>
          {context_keys !== undefined && (
            <span className="text-xs text-gray-400">
              {context_keys} context keys
            </span>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
        {insight}
      </p>
    </div>
  );
}
